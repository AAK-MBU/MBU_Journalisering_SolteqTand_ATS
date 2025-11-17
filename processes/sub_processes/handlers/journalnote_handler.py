"""Module to handle journal note creation in SolteqTand"""

import logging

from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase

import helpers.config as config
from helpers.context_handler import get_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app
from processes.sub_processes.handlers.journalizing_db_handler import (
    update_process_status,
    update_response_metadata,
)

logger = logging.getLogger(__name__)


def create_journalnote():
    """Function to create a journal note in SolteqTand"""
    try:
        logger.info("Starting journal note creation process.")

        # Get the application instance
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        # Check if journal note already exists else create it
        solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
        solteq_db_obj = SolteqTandDatabase(conn_str=solteq_db_conn)
        journal_note_message_sql_lookup = config.JOURNAL_NOTE_DOCUMENT_MESSAGE.replace(
            "Administrativt notat ", ""
        ).replace("'", "")

        filters = {
            "p.cpr": get_context_values("cpr"),
            "dn.Beskrivelse": journal_note_message_sql_lookup,
        }

        journal_note_exists = solteq_db_obj.get_list_of_journal_notes(filters=filters)
        if not journal_note_exists:
            solteq_app.create_journal_note(
                note_message=config.JOURNAL_NOTE_DOCUMENT_MESSAGE,
                checkmark_in_complete=True,
            )

            check_journal_note_created = solteq_db_obj.get_list_of_journal_notes(
                filters=filters
            )

            if not check_journal_note_created:
                raise RuntimeError("Journal note creation failed.")

        # Update journal note response metadata in RPA database
        update_response_metadata(
            step_name="JournalNote", json_fragment={"JournalNoteCreated": True}
        )
        logger.info("Journal note creation process completed successfully.")
    except Exception as e:
        update_response_metadata(
            step_name="JournalNote", json_fragment={"JournalNoteCreated": False}
        )
        update_process_status("Failed")
        logger.error("Error creating journal note: %s", e)
        raise RuntimeError("Error creating journal note: " + str(e)) from e

