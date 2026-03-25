"""Handler for consent handling in tilflytter process."""

import logging

from mbu_dev_shared_components.solteqtand.application import SolteqTandApp

from helpers.context_functions import get_context_values
from processes.shared.handlers.journalizing.solteq_note_handler import (
    create_journalnote,
    create_sub_note,
)
from processes.sub_processes.tilflytter import config

logger = logging.getLogger(__name__)


def consent_tilflytter_handler() -> None:
    """Function wrapper that handles consent logic and creating journal notes in SolteqTand."""

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
        logger.error("Invalid value for journal consent. Value must be True or False.")
        raise ValueError("Journal consent must be True or False.")

    # Create administrative note in SolteqTand based on consent for fetching previous journal
    consent_treatment = get_context_values("treatment_consent")
    if consent_treatment:
        create_journalnote(
            journal_note_message=config.DIAGNOSE_NOTE_CONSENT_MESSAGE,
            checkmark_in_complete=False,
            note_type=config.DIAGNOSE_NOTE_CONSENT_TYPE,
        )
        create_sub_note(
            parent_note_message=config.DIAGNOSE_NOTE_CONSENT_MESSAGE,
            parent_note_type=config.DIAGNOSE_NOTE_CONSENT_TYPE,
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
        logger.error(
            "Invalid value for treatment consent. Value must be True or False."
        )
        raise ValueError("Treatment consent must be True or False.")


def solteq_journal_update_handler(solteq_app: SolteqTandApp) -> None:
    """Function wrapper that handles updating or inserting phone number and create event in SolteqTand."""

    # Update or insert phone number in SolteqTand
    try:
        solteq_app.update_or_change_phone_number(
            get_context_values("citizen_phone_number")
        )
    except Exception as e:
        logger.error("Error updating phone number: %s", e)
        raise e

    # Create event in SolteqTand
    try:
        # Temp workaround if clinic name is not provided in form, as clinic name is required to create event in SolteqTand.
        # Clinic name should be provided in form in future, and default value can be removed.
        if not get_context_values("clinic_name"):
            clinic_name = "Tandplejen Aarhus"
        else:
            clinic_name = get_context_values("clinic_name")

        solteq_app.create_new_event(
            clinic_name=clinic_name,
            event_text=config.EVENT_TEXT,
        )
    except Exception as e:
        logger.error("Error creating event: %s", e)
        raise e
