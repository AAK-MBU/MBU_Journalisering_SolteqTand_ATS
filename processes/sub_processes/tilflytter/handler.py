"""Handler for the 'Tilflytter' process."""

import logging

from mbu_rpa_core.exceptions import BusinessError

from helpers.context_functions import get_context_values
from processes.application_handler import get_app
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard
from processes.shared.handlers.journalizing.db_handler import update_process_status
from processes.shared.handlers.journalizing.process_journalizing import (
    process_journalization_step,
)
from processes.shared.handlers.journalizing.solteq_note_handler import (
    create_journalnote,
    create_sub_note,
)
from processes.shared.utils.clean_up import release_keys
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
        set_context_vars(item_data, item_reference, item_id)

        logger.info(
            "Handling dashboard update for step: %s ...",
            config.DASHBOARD_STEP_6_NAME,
        )
        handle_process_dashboard(
            status="running",
            process_step_name=config.DASHBOARD_STEP_6_NAME,
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

        # Create administrativ note in Solteq based on form input
        create_journalnote(
            journal_note_message=config.ADM_NOTE_MESSAGE,
            checkmark_in_complete=True,
            note_type=config.ADM_NOTE_TYPE,
        )

        # Create administrative note in SolteqTand based on consent for school kids
        consent_generel = get_context_values("journal_consent")
        if consent_generel:
            create_journalnote(
                journal_note_message=config.ADM_NOTE_CONSENT_MESSAGE,
                checkmark_in_complete=True,
                note_type=config.ADM_NOTE_CONSENT_TYPE,
            )
        elif not consent_generel:
            create_journalnote(
                journal_note_message=config.ADM_NOTE_NO_CONSENT_MESSAGE,
                checkmark_in_complete=True,
                note_type=config.ADM_NOTE_NO_CONSENT_TYPE,
            )
        else:
            raise ValueError("Journal consent must be True or False.")

        # Create administrative note in SolteqTand based on consent for fetching previous journal
        consent_treatment = get_context_values("treatment_consent")
        if consent_treatment:
            create_journalnote(
                journal_note_message=config.DIAGNOSE_NOTE_CONSENT_MESSAGE,
                checkmark_in_complete=True,
                note_type=config.DIAGNOSE_NOTE_CONSENT_TYPE,
            )
            create_sub_note(
                parent_note="",
                sub_note_message=config.DIAGNOSE_SUB_NOTE_CONSENT_MESSAGE,
                sub_note_type=config.DIAGNOSE_SUB_NOTE_CONSENT_TYPE,
                checkmark_in_complete=True,
            )
        elif not consent_treatment:
            create_journalnote(
                journal_note_message=config.DIAGNOSE_NOTE_NO_CONSENT_MESSAGE,
                checkmark_in_complete=True,
                note_type=config.DIAGNOSE_NOTE_NO_CONSENT_TYPE,
            )
        else:
            raise ValueError("Treatment consent must be True or False.")

        # Update or insert phone number in SolteqTand
        solteq_app.update_or_change_phone_number(
            get_context_values("citizen_phone_number")
        )

        # Create event in SolteqTand
        solteq_app.create_new_event(
            clinic_name=get_context_values("clinic_name"),
            event_text=config.EVENT_TEXT,
        )

        logger.info(
            "Handling dashboard update for step: %s ...",
            config.DASHBOARD_STEP_6_NAME,
        )
        handle_process_dashboard(
            status="success",
            process_step_name=config.DASHBOARD_STEP_6_NAME,
        )

    except BusinessError as be:
        logger.error("Business error occurred: %s", be)
        logger.info(
            "Handling updating journalizing database with status failed...",
        )
        update_process_status("Failed")
        raise be
    except Exception as e:
        logger.error("Application error occurred: %s", e)
        logger.info(
            "Handling updating journalizing database with status failed...",
        )
        update_process_status("Failed")
        raise e
