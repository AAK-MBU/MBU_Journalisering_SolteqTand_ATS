"""Handler for the consent step in the frit valg process."""

import logging

from helpers.context_functions import get_context_values
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard
from processes.shared.handlers.journalizing.solteq_note_handler import (
    create_journalnote,
)
from processes.sub_processes.fritvalg import config

logger = logging.getLogger(__name__)


def create_receipt_journal_note():
    """Creates the journal note tied to the receipt from OS2Forms."""

    create_journalnote(
        journal_note_message=config.ADM_NOTE_MESSAGE,
        checkmark_in_complete=True,
        note_type=config.ADM_NOTE_TYPE,
    )


def consent_fritvalg_handler() -> None:
    """Handler for consent step, checks clinic data and consent, and creates journal note"""
    try:
        handle_process_dashboard(
            status="running",
            process_step_name=get_context_values("current_step_name"),
        )

        consent = get_context_values("consent")

        if consent:
            create_journalnote(
                journal_note_message=config.ADM_NOTE_CONSENT_MESSAGE,
                checkmark_in_complete=True,
                note_type=config.ADM_NOTE_CONSENT_TYPE,
            )
        elif not consent:
            create_journalnote(
                journal_note_message=config.ADM_NOTE_NO_CONSENT_MESSAGE,
                checkmark_in_complete=True,
                note_type=config.ADM_NOTE_NO_CONSENT_TYPE,
            )

        handle_process_dashboard(
            status="success",
            process_step_name=get_context_values("current_step_name"),
        )

    except Exception as e:
        logger.error("Error in consent handler: %s", e)
        raise e
