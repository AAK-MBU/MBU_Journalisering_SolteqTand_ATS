"""Handler for the 'Udskrivning 22 år' process."""

import logging

from mbu_rpa_core.exceptions import BusinessError

from helpers.context_functions import get_context_values
from processes.application_handler import get_app
from processes.shared.handlers.checkpoints_handler import (
    check_clinic_data_and_consent,
    validate_contractor,
)
from processes.shared.handlers.dashboard_data_handler import (
    handle_process_dashboard,
    update_process_run_metadata,
)
from processes.shared.handlers.journalize_document_handler import (
    journalize_form_document,
)
from processes.shared.handlers.journalizing_db_handler import update_process_status
from processes.shared.utils.clean_up import release_keys
from processes.sub_processes.udskrivning_22_aar.set_context import set_context_vars

from . import config

logger = logging.getLogger(__name__)


def process_udskrivning_22_aar(item_data: dict, item_reference: str, item_id: str):
    """Function to handle the 'Udskrivning 22 år' process item."""
    try:
        logger.info(
            "Processing 'Udskrivning 22 år' item with reference: %s and id: %s",
            item_reference,
            item_id,
        )

        release_keys()

        # Set context variables for further processing
        set_context_vars(
            item_data=item_data, item_reference=item_reference, item_id=item_id
        )

        # Update process run metadata with clinic phone number and dispatch ID
        update_process_run_metadata(
            item_data=item_data, process_name=config.DASHBOARD_PROCESS_NAME
        )

        # Step 4
        logger.info(
            "Handling dashboard update for step: %s ...",
            config.DASHBOARD_STEP_4_NAME,
        )
        handle_process_dashboard(
            status="running",
            process_step_name=config.DASHBOARD_STEP_4_NAME,
        )
        handle_process_dashboard(
            status="success",
            process_step_name=config.DASHBOARD_STEP_4_NAME,
        )

        # Set journalizing process status in RPA database
        update_process_status("InProgress")

        # Get the application instance
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        logger.info("Opening patient in Solteq Tand application...")
        solteq_app.open_patient(get_context_values("cpr"))

        # Step 5
        # Journalize form document
        journalize_form_document(
            current_step_name=config.DASHBOARD_STEP_5_NAME,
            document_type=config.DOCUMENT_TYPE,
            document_file_name=config.DOCUMENT_FILE_NAME,
            journal_note_message=config.JOURNAL_NOTE_DOCUMENT_MESSAGE,
        )

        # Step 6
        # Check if contractor exists in SolteqTand database and update contractor if exists.
        validate_contractor(
            step_name=config.DASHBOARD_STEP_6_NAME,
        )

        # Step 7
        # Check if clinic data matches and if consent is given
        check_clinic_data_and_consent(
            process_name=config.DASHBOARD_PROCESS_NAME,
            process_step_name=config.DASHBOARD_STEP_7_NAME,
        )

        # Update journalizing process status in RPA database
        update_process_status("Successful")
    except BusinessError as be:
        logger.error("Business error occurred: %s", be)

        # Update process status to "Failed" in journalizing database
        update_process_status("Failed")
        raise be
    except Exception as e:
        logger.error("Application error occurred: %s", e)

        # Update process status to "Failed" in journalizing database
        update_process_status("Failed")
        raise e
