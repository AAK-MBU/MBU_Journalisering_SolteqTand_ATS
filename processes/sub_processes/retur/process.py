"""Process module for handling the 'Retur' subprocess."""

import logging

from helpers.context_functions import get_context_values
from processes.application_handler import get_app
from processes.shared.handlers.event_handler import create_event
from processes.shared.handlers.journalizing.process_journalizing import (
    process_journalization_step,
)
from processes.shared.utils.clean_up import release_keys
from processes.sub_processes.retur.handler import (
    create_receipt_journal_note,
    get_clinic_name,
)
from processes.sub_processes.retur.set_context import set_context_vars

from . import config

logger = logging.getLogger(__name__)


def process_retur(item_data: dict, item_reference: str, item_id: str):
    """Function to handle the 'Retur' process item."""

    try:
        logger.info(
            "Processing 'Tilflytter' item with reference: %s and id: %s",
            item_reference,
            item_id,
        )

        release_keys()

        # Set context variables for further processing
        set_context_vars(
            item_data=item_data, item_reference=item_reference, item_id=item_id
        )

        # Get the application instance
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        logger.info("Opening patient in Solteq Tand application...")
        solteq_app.open_patient(get_context_values("cpr"))

        # Step 1: Journalize form document in Solteq
        # and create journal note linked to the receipt.
        process_journalization_step(
            document_type=config.DOCUMENT_TYPE,
            document_file_name=config.DOCUMENT_FILE_NAME,
        )

        create_receipt_journal_note()

        # Step 2: Create event
        primary_clinic_name = get_clinic_name(ssn=get_context_values("cpr"))
        create_event(
            event_message=config.EVENT_MESSAGE, clinic_name=primary_clinic_name
        )

    except Exception as e:
        logger.error("Application error occurred: %s", e)
        raise e
