"""Module to handle item processing"""

import logging

from mbu_rpa_core.exceptions import BusinessError, ProcessError

from helpers.config import SUBPROCESS_CHOICES
from helpers.context_functions import get_context_values
from processes.application_handler import close, get_app
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard
from processes.shared.utils.clean_up import clean_up
from processes.sub_processes.fritvalg.process import process_fritvalg
from processes.sub_processes.tilflytter.process import process_tilflytter
from processes.sub_processes.udskrivning_22_aar.process import (
    process_udskrivning_22_aar,
)

logger = logging.getLogger(__name__)


def process_item(item_data: dict, item_reference: str, item_id: str, subprocess: str):
    """Function to handle item processing"""
    success = False
    try:
        if subprocess not in SUBPROCESS_CHOICES:
            raise ValueError(
                f"Unknown subprocess: '{subprocess}'. Must be one of {SUBPROCESS_CHOICES}"
            )

        if subprocess == "udskrivning22ar":
            process_udskrivning_22_aar(
                item_data=item_data,
                item_reference=item_reference,
                item_id=item_id,
            )
        elif subprocess == "tilflytter":
            process_tilflytter(
                item_data=item_data,
                item_reference=item_reference,
                item_id=item_id,
            )
        elif subprocess == "fritvalg":
            process_fritvalg(
                item_data=item_data,
                item_reference=item_reference,
                item_id=item_id,
            )

        success = True

    except BusinessError as be:
        logger.error("Business error occurred: %s", be)
        handle_process_dashboard(
            status="failed",
            process_step_name=get_context_values("current_step_name"),
            failure=be,
            rerun_config={"workitem_id": item_id},
        )
        raise be
    except Exception as e:
        logger.error("%s", e)
        handle_process_dashboard(
            status="failed",
            process_step_name=get_context_values("current_step_name"),
            failure=e,
        )
        raise ProcessError("A process error occurred.") from e
    finally:
        clean_up()
        if success:
            app = get_app()
            if app is not None:
                try:
                    app.close_patient_window()
                    logger.info(
                        "Patient window closed successfully after successful processing."
                    )
                except Exception as e:
                    logger.warning(
                        "Could not close patient window after success (will fall back to full close): %s",
                        e,
                    )
                    close()
        else:
            logger.info(
                "Closing application after failure to ensure clean state for next item."
            )
            close()
