"""Process module for handling the 'Tilflytter' subprocess."""

import logging

from mbu_rpa_core.exceptions import BusinessError

from helpers.context_functions import get_context_values, set_context_values
from processes.application_handler import get_app
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard

# from processes.shared.handlers.journalizing.db_handler import update_process_status
from processes.shared.handlers.journalizing.process_journalizing import (
    process_journalization_step,
)
from processes.shared.utils.clean_up import release_keys
from processes.sub_processes.tilflytter.handler import (
    consent_tilflytter_handler,
    solteq_journal_update_handler,
)
from processes.sub_processes.tilflytter.set_context import set_context_vars

from . import config

logger = logging.getLogger(__name__)


def process_tilflytter(item_data: dict, item_reference: str, item_id: str):
    """Function to handle the 'Tilflytter' process item."""
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
        set_context_values(current_step_name=config.DASHBOARD_STEP_6_NAME)

        logger.info(
            "Handling step 6: %s ...",
            config.DASHBOARD_STEP_6_NAME,
        )

        handle_process_dashboard(
            status="running",
            process_step_name=get_context_values("current_step_name"),
        )

        # Get the application instance
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        logger.info("Opening patient in Solteq Tand application...")
        solteq_app.open_patient(get_context_values("cpr"))

        # Journalize form document in Solteq
        process_journalization_step(
            document_type=config.DOCUMENT_TYPE,
            document_file_name=config.DOCUMENT_FILE_NAME,
        )

        # Handle consent and create journal note(s) in Solteq
        consent_tilflytter_handler()

        # Update or insert phone number and create event in SolteqTand
        solteq_journal_update_handler(solteq_app)

        handle_process_dashboard(
            status="success",
            process_step_name=get_context_values("current_step_name"),
        )

    except BusinessError as be:
        logger.error("Business error occurred: %s", be)
        logger.info(
            "Handling updating journalizing database with status failed...",
        )
        # update_process_status("Failed")
        raise be
    except Exception as e:
        logger.error("Application error occurred: %s", e)
        logger.info(
            "Handling updating journalizing database with status failed...",
        )
        # update_process_status("Failed")
        raise e
