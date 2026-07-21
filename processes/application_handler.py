"""Module for handling application startup, and close"""

import logging
import subprocess as sp
from subprocess import CalledProcessError

from mbu_dev_shared_components.solteqtand.application import SolteqTandApp
from mbu_dev_shared_components.solteqtand.application.exceptions import (
    NotMatchingError,
    PatientNotFoundError,
)
from mbu_rpa_core.exceptions import BusinessError

from helpers import config
from helpers.credential_constants import get_rpa_credentials

logger = logging.getLogger(__name__)

APP: SolteqTandApp | None = None


def get_app():
    """Function to get the application instance"""
    # noqa: PLW0602, PLW0603
    global APP
    return APP


def open_patient(cpr: str) -> SolteqTandApp:
    """Open a patient in Solteq Tand, guarding against a missing patient.

    Fetches the running application instance and opens the patient with the
    given CPR. Conditions that stem from the input data rather than an
    automation failure are translated into a ``BusinessError`` so they are
    handled as business failures upstream:

    - ``PatientNotFoundError``: no patient exists with the given CPR.
    - ``NotMatchingError``: a patient was opened, but its CPR did not match
      the requested one.

    Returns the application instance so callers can keep using it.
    """
    solteq_app = get_app()
    if solteq_app is None:
        raise ValueError("Could not get application instance.")

    logger.info("Opening patient in Solteq Tand application...")
    try:
        solteq_app.open_patient(cpr)
    except PatientNotFoundError as exc:
        raise BusinessError(
            f"Patient med CPR {cpr} findes ikke i Solteq Tand"
        ) from exc
    except NotMatchingError as exc:
        raise BusinessError(
            f"Opened patient's CPR did not match the requested CPR: {cpr}"
        ) from exc

    return solteq_app


def startup():
    """Function for starting applications"""
    logger.info("Starting applications...")

    logger.info("Starting Solteq Tand application...")
    try:
        creds = get_rpa_credentials("solteq_tand_svcrpambu001")

        application = SolteqTandApp(
            app_path=config.APP_PATH,
            username=creds["username"],
            password=creds["decrypted_password"],
        )
        application.start_application()
        application.login()

        # noqa: PLW0602, PLW0603
        global APP
        APP = application
    except Exception as e:
        logger.error("Failed to start Solteq Tand application: %s", e)
        raise


def soft_close():
    """Function for closing applications softly"""
    logger.info("Closing applications softly...")

    logger.info("Closing Solteq Tand application softly...")
    application = get_app()
    if application is None:
        logger.warning("No application instance to close")
        return

    try:
        application.close_solteq_tand()
        logger.info("Closed application softly")
    except AssertionError as e:
        logger.warning(
            "Soft close failed with assertion error (will force close): %s", e
        )
    except Exception as e:
        logger.warning("Could not close application softly (will force close): %s", e)


def hard_close(application: str):
    """Function for closing applications hard"""
    logger.info("Hard closing %s...", application)
    list_processes = ["wmic", "process", "get", "description"]
    if f"{application}" in sp.check_output(list_processes).strip().decode():
        try:
            kill_msg = sp.check_output(["taskkill", "/f", "/im", f"{application}"])
            logger.info(kill_msg)
        except CalledProcessError as e:
            logger.error(
                f"{application} found in subprocesses, but error while killing it: %s",
                e,
            )


def close():
    """Function for closing applications softly or hardly if necessary"""
    solteq_app = get_app()
    if solteq_app:
        soft_close()
    solteq_app = get_app()
    if solteq_app:
        hard_close(application="TMTand.exe")


def reset():
    """Function for resetting application"""
    close()
    startup()
