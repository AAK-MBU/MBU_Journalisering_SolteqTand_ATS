"""Process module for handling the 'Fritvalg' subprocess."""

import logging

from helpers.context_functions import get_context_values, set_context_values
from processes.application_handler import get_app
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard
from processes.shared.handlers.event_handler import create_event
from processes.shared.handlers.journalizing.db_handler import update_process_status
from processes.shared.handlers.journalizing.process_journalizing import (
    process_journalization_step,
)
from processes.shared.handlers.solteq_contractor_handler import (
    check_extern_clinic_deal,
    validate_contractor,
)
from processes.shared.utils.clean_up import release_keys
from processes.sub_processes.fritvalg.handler import (
    consent_fritvalg_handler,
    create_receipt_journal_note,
)
from processes.sub_processes.fritvalg.set_context import set_context_vars

from . import config

logger = logging.getLogger(__name__)


def process_fritvalg(
    item_data: dict,
    item_reference: str,
    item_id: str,
) -> None:
    """Function to handle the 'Fritvalg' process item."""
    try:
        logger.info(
            "Processing 'Fritvalg' item with reference: %s and id: %s",
            item_reference,
            item_id,
        )

        release_keys()

        # Set context variables for further processing
        set_context_vars(
            item_data=item_data,
            item_reference=item_reference,
            item_id=item_id,
        )

        # Set journalizing process status in RPA database
        update_process_status("InProgress")

        # Get the application instance and open patient in Solteq Tand application
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        logger.info("Opening patient in Solteq Tand application...")
        solteq_app.open_patient(get_context_values("cpr"))

        # Step 2
        # Journalize form document in Solteq
        set_context_values(current_step_name=config.DASHBOARD_STEP_2_NAME)

        logger.info(
            "Handling step 2: %s ...",
            config.DASHBOARD_STEP_2_NAME,
        )

        handle_process_dashboard(
            status="running",
            process_step_name=get_context_values("current_step_name"),
        )

        process_journalization_step(
            document_type=config.DOCUMENT_TYPE,
            document_file_name=config.DOCUMENT_FILE_NAME,
        )

        # Create journal note linked to the receipt.
        create_receipt_journal_note()

        handle_process_dashboard(
            status="success",
            process_step_name=get_context_values("current_step_name"),
        )

        # Step 3
        # Check if contractor exists in SolteqTand database and update contractor if exists.
        set_context_values(current_step_name=config.DASHBOARD_STEP_3_NAME)

        logger.info(
            "Handling step 3: %s ...",
            config.DASHBOARD_STEP_3_NAME,
        )

        validate_contractor()

        # Step 4
        # Check if clinic has contract with Aarhus Kommune and add contractor to solteq if contract exists.
        set_context_values(current_step_name=config.DASHBOARD_STEP_4_NAME)

        logger.info(
            "Handling step 4: %s ...",
            config.DASHBOARD_STEP_4_NAME,
        )

        handle_process_dashboard(
            status="running",
            process_step_name=get_context_values("current_step_name"),
        )

        check_extern_clinic_deal(
            contractor_id=get_context_values("clinic_provider_number"),
        )

        handle_process_dashboard(
            status="success",
            process_step_name=get_context_values("current_step_name"),
        )

        # Step 5
        # Check if clinic data matches and if consent is given.
        set_context_values(current_step_name=config.DASHBOARD_STEP_5_NAME)

        logger.info(
            "Handling step 5: %s ...",
            config.DASHBOARD_STEP_5_NAME,
        )

        consent_fritvalg_handler()

        # Step 6
        # Create event
        create_event(event_message=config.EVENT_MESSAGE, clinic_name=config.CLINIC_NAME)

        # Update journalizing process status in RPA database
        update_process_status("Successful")

    except Exception as e:
        logger.error("Error processing 'Fritvalg' item: %s", e)
        raise
