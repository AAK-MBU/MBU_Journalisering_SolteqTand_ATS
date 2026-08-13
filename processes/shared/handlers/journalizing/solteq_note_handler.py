"""Module to handle journal note creation in SolteqTand"""

import logging
import time

from mbu_solteqtand_shared_components.database.db_handler import SolteqTandDatabase

from helpers.context_functions import get_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app
from processes.shared.handlers.journalizing.db_handler import (
    update_process_status,
    update_response_metadata,
)

logger = logging.getLogger(__name__)

NOTE_VERIFY_TIMEOUT_SECONDS = 30
NOTE_VERIFY_POLL_INTERVAL_SECONDS = 2


def _wait_for_journal_note(
    solteq_db_obj: SolteqTandDatabase,
    filters: dict,
    timeout: int = NOTE_VERIFY_TIMEOUT_SECONDS,
    poll_interval: int = NOTE_VERIFY_POLL_INTERVAL_SECONDS,
) -> list:
    """Poll the database until the journal note appears, or raise on timeout.

    Returns the matching rows. Raises RuntimeError if the note has not
    appeared within `timeout` seconds.
    """
    started = time.monotonic()
    deadline = started + timeout
    attempt = 0

    while True:
        attempt += 1
        rows = solteq_db_obj.get_list_of_journal_notes(filters=filters)
        if rows:
            elapsed = time.monotonic() - started
            logger.info(
                "Journal note verified in database after %.1fs (%d lookup(s)).",
                elapsed,
                attempt,
            )
            return rows

        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"Journal note not found in database after {timeout}s "
                f"({attempt} lookup(s)). filters={filters!r}"
            )

        time.sleep(poll_interval)


def create_journalnote(
    journal_note_message: str,
    checkmark_in_complete: bool,
    note_type: str,
):
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
        journal_note_message_sql_lookup = journal_note_message.replace(
            note_type + " ", ""
        ).replace("'", "")

        filters = {
            "p.cpr": get_context_values("cpr"),
            "dn.Beskrivelse": journal_note_message_sql_lookup,
        }

        journal_note_exists = solteq_db_obj.get_list_of_journal_notes(filters=filters)
        note_message = f"{note_type} {journal_note_message}"

        logger.info("Note message to create: %s", note_message)

        if not journal_note_exists:
            solteq_app.create_journal_note(
                note_message=note_message,
                checkmark_in_complete=checkmark_in_complete,
            )

            _wait_for_journal_note(solteq_db_obj=solteq_db_obj, filters=filters)
        else:
            logger.info("Journal note already exists. Skipping creation.")

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


def create_sub_note(
    parent_note_message: str,
    parent_note_type: str,
    sub_note_message: str,
    sub_note_type: str,
    checkmark_in_complete: bool,
):
    """Function to create a sub note to an existing journal note in SolteqTand"""
    try:
        logger.info("Starting journal sub note creation process.")

        # Get the application instance
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        # Check if journal note already exists else create it
        solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
        solteq_db_obj = SolteqTandDatabase(conn_str=solteq_db_conn)
        journal_note_message_sql_lookup = sub_note_message.replace(
            sub_note_type + " ", ""
        ).replace("'", "")

        filters = {
            "p.cpr": get_context_values("cpr"),
            "dn.Beskrivelse": journal_note_message_sql_lookup,
        }

        journal_note_exists = solteq_db_obj.get_list_of_journal_notes(filters=filters)
        if not journal_note_exists:
            solteq_app.create_journal_sub_note(
                parent_note_message=parent_note_message,
                parent_note_type=parent_note_type,
                note_message=f"{sub_note_type} {sub_note_message}",
                checkmark_in_complete=checkmark_in_complete,
            )
        else:
            logger.info("Journal sub note already exists. Skipping creation.")

            time.sleep(3)  # Wait for the journal note to be created

            _wait_for_journal_note(solteq_db_obj=solteq_db_obj, filters=filters)

        # Update journal note response metadata in RPA database
        update_response_metadata(
            step_name="JournalSubNote", json_fragment={"JournalSubNoteCreated": True}
        )
        logger.info("Journal sub note creation process completed successfully.")
    except Exception as e:
        update_response_metadata(
            step_name="JournalSubNote", json_fragment={"JournalSubNoteCreated": False}
        )
        update_process_status("Failed")
        logger.error("Error creating journal sub note: %s", e)
        raise RuntimeError("Error creating journal sub note: " + str(e)) from e
