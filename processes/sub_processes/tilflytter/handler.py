"""Handler for consent handling in tilflytter process."""

import logging
import os

from mbu_solteqtand_shared_components.application import SolteqTandApp
from mbu_solteqtand_shared_components.database.db_handler import SolteqTandDatabase

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
    logger.info("Consent generel value: %s", consent_generel)
    if consent_generel is None:
        logger.info("Generel consent is None. Skipping journal note creation.")
    elif consent_generel:
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
        raise ValueError("Treatment consent must be True, False or None.")

    # Create administrative note in SolteqTand based on consent for fetching previous journal
    consent_treatment = get_context_values("treatment_consent")
    logger.info("Consent treatment value: %s", consent_treatment)
    if consent_treatment is None:
        logger.info("Treatment consent is None. Skipping journal note creation.")
    elif consent_treatment is True:
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
    elif consent_treatment is False:
        create_journalnote(
            journal_note_message=config.DIAGNOSE_NOTE_NO_CONSENT_MESSAGE,
            checkmark_in_complete=True,
            note_type=config.DIAGNOSE_NOTE_NO_CONSENT_TYPE,
        )
    else:
        logger.error(
            "Invalid value for treatment consent: %r. Must be True, False or None.",
            consent_treatment,
        )
        raise ValueError("Treatment consent must be True, False or None.")


def _get_primary_clinic_data() -> list:
    """Check if primary clinic is set."""
    try:
        logger.info("Getting primary clinic data")
        solteq_db_conn = os.getenv("DBCONNECTIONSTRINGSOLTEQTAND")
        solteq_db = SolteqTandDatabase(solteq_db_conn)

        filter_params = {
            "p.cpr": get_context_values("cpr"),
        }
        result = solteq_db.get_list_of_primary_dental_clinics(filters=filter_params)

        logger.info("Primary clinic data: %s", result)

        return result
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise


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
    # Anvend den eksisterende klinik (tag den fra databasen), hvis ikke den er udfyldt i formularen
    try:
        if not get_context_values("clinic_name"):
            clinic_data = _get_primary_clinic_data()
            clinic_name = clinic_data[0]["preferredDentalClinicName"]
        else:
            clinic_name = get_context_values("clinic_name")

        logger.info("Clinic name: %s", clinic_name)

        solteq_app.create_new_event(
            clinic_name="Tandplejen Aarhus - Kontaktcenter",
            event_text=config.EVENT_TEXT,
        )
    except Exception as e:
        logger.error("Error creating event: %s", e)
        raise e
