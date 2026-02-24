"""Handles checkpoints for clinic data and contractor validation"""

import logging

from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase
from mbu_rpa_core.exceptions import BusinessError, ProcessError

from helpers.config import DASHBOARD_STEP_6_NAME, DASHBOARD_STEP_7_NAME
from helpers.context_handler import get_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app
from processes.sub_processes.handlers.dashboard_data_handler import (
    check_if_clinic_data_match,
    update_dashboard_step_run,
)
from processes.sub_processes.handlers.solteq_contractor_handler import (
    match_clinic,
)

logger = logging.getLogger(__name__)


def check_clinic_data_and_consent():
    """Check if clinic data matches and consent is given"""
    try:
        # Update dashboard to indicate step is running
        update_dashboard_step_run(step_name=DASHBOARD_STEP_7_NAME, status="running")

        clinic_data_matches = check_if_clinic_data_match()
        consent_given = get_context_values("consent")

        if not clinic_data_matches and consent_given:
            clinic_match_and_consent_error = {
                "type": "BusinessError",
                "message": "Klinikdata matcher ikke, men samtykke givet.",
            }
            logger.error("Clinic data does not match, but consent has been given.")
            raise BusinessError(clinic_match_and_consent_error["message"])

        elif not clinic_data_matches and not consent_given:
            clinic_match_and_consent_error = {
                "type": "BusinessError",
                "message": "Klinikdata matcher ikke, og samtykke ikke givet.",
            }
            logger.error("Clinic data does not match, and consent has not been given.")
            raise BusinessError(clinic_match_and_consent_error["message"])

        update_dashboard_step_run(step_name=DASHBOARD_STEP_7_NAME, status="success")
    except BusinessError as be:
        logger.error("Business error: %s", be)
        update_dashboard_step_run(
            step_name=DASHBOARD_STEP_7_NAME,
            status="failed",
            failure=str(be),
            rerun=True,
        )
        raise
    except Exception as e:
        logger.error("Error checking clinic data and consent: %s", e)
        update_dashboard_step_run(
            step_name=DASHBOARD_STEP_7_NAME,
            status="failed",
            failure=str(e),
            rerun=True,
        )
        raise ProcessError(
            "An error occurred while checking clinic data and consent."
        ) from e


def validate_contractor():
    """Validate contractor in SolteqTand database and update contractor if exists."""
    try:
        # Update dashboard to indicate step is running
        update_dashboard_step_run(step_name=DASHBOARD_STEP_6_NAME, status="running")

        # Use the clinic lookup function
        match_result = match_clinic()

        if not match_result["success"]:
            contractor_lookup_error = {
                "type": "BusinessError",
                "message": f"""Vi kunne ikke matche den valgte tandklinik med en klinik i Solteq – hverken via ydernummer eller telefonnummer.
                Detaljer: {match_result["error"]}
                Kontakt Tandplejens administration, tandplejen@mbu.aarhus.dk, og bed om at få undersøgt,
                om tandklinikken er oprettet i Solteq eller om den mangler oplysninger om ydernummer eller telefonnummer, der matcher det i EDI.
                Afvent svar.
                Du kan genstarte processen, når klinikken er oprettet eller dens oplysninger er rettet i Solteq.""",
            }
            logger.error(
                "Contractor not found in SolteqTand database. Error: %s",
                match_result["error"],
            )
            raise BusinessError(contractor_lookup_error["message"])

        # Get matched clinic data
        matched_clinic = match_result["clinic"]
        logger.info("Matched clinic data: %s", matched_clinic)

        # Get current contractor data from patient
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
        solteq_db_obj = SolteqTandDatabase(conn_str=solteq_db_conn)
        filters = {
            "p.cpr": get_context_values("cpr"),
        }
        current_extern_dentist_data = solteq_db_obj.get_list_of_extern_dentist(
            filters=filters
        )

        logger.info("Current extern dentist data: %s", current_extern_dentist_data)
        logger.info("Matched clinic data: %s", matched_clinic)

        new_contractor_id = matched_clinic.get("contractorId", [])
        new_contractor_phone_number = matched_clinic.get("phoneNumber", [])

        logger.info("New contractor ID: %s", new_contractor_id)
        logger.info("New contractor phone number: %s", new_contractor_phone_number)

        current_contractor_id = (
            current_extern_dentist_data[0]["contractorId"]
            if current_extern_dentist_data
            else ""
        )
        current_contractor_phone_number = (
            current_extern_dentist_data[0]["phoneNumber"]
            if current_extern_dentist_data
            else ""
        )

        logger.info(
            "Comparing contractors - Current: %s vs New: %s",
            current_contractor_id,
            new_contractor_id,
        )

        # Update contractor if it has changed or if no current contractor is set
        if not current_extern_dentist_data or (
            current_contractor_id != new_contractor_id
            or current_contractor_phone_number != new_contractor_phone_number
        ):
            logger.info("Contractor data has changed, updating in Solteq...")
            solteq_app.change_private_clinic(
                private_clinic=matched_clinic.get("name", [])
            )

        update_dashboard_step_run(step_name=DASHBOARD_STEP_6_NAME, status="success")
    except BusinessError as be:
        logger.error("Business error: %s", be)
        update_dashboard_step_run(
            step_name=DASHBOARD_STEP_6_NAME,
            status="failed",
            failure=be,
            rerun=True,
        )
        raise
    except Exception as e:
        logger.error("Error validating contractor: %s", e)
        update_dashboard_step_run(
            step_name=DASHBOARD_STEP_6_NAME,
            status="failed",
            failure=e,
            rerun=True,
        )
        raise ProcessError(
            "An error occurred while validating contractor in SolteqTand database."
        ) from e
