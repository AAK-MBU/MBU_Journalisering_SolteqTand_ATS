# processes/shared/handlers/event_handler.py
"""Module to handle events in Solteq"""

import datetime
import logging
from zoneinfo import ZoneInfo

from dateutil import relativedelta
from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase

from helpers.context_functions import get_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app

logger = logging.getLogger(__name__)


def _get_events(event_message: str) -> list:
    """
    Query the Solteq database for non-archived events matching the given
    message for a specific patient within the last month.

    Args:
        event_message: The event state text to filter by.
        patient_cpr: The CPR number of the patient.

    Returns:
        A list of matching event records.

    Raises:
        ValueError: If the database connection string cannot be retrieved.
    """
    solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
    solteq_db_obj = SolteqTandDatabase(conn_str=solteq_db_conn)

    one_month_ago = (
        datetime.datetime.now(ZoneInfo("Europe/Copenhagen")) - relativedelta(months=1)
    ).date()

    return solteq_db_obj.get_list_of_events(
        filters={
            "p.cpr": get_context_values("cpr"),
            "e.currentStateText": event_message,
            "e.archived": 0,
            "e.currentStateDate": (">=", one_month_ago),
        }
    )


def create_event(event_message: str, clinic_name: str) -> None:
    """
    Create an event in the Solteq application if it does not already exist.

    Args:
        event_message: The event text/identifier to create.
        clinic_name: The name of the clinic under which the event is created.

    Raises:
        ValueError: If the Solteq application instance cannot be obtained.
        RuntimeError: If the event could not be confirmed after creation.
    """
    solteq_app = get_app()
    if solteq_app is None:
        raise ValueError("Could not get application instance.")

    logger.info("Checking if event '%s' exists for patient.", event_message)

    if _get_events(event_message=event_message):
        logger.info("Event already exists.")
        return

    logger.info("Creating event...")
    solteq_app.create_new_event(
        clinic_name=clinic_name,
        event_text=event_message,
    )

    if not _get_events(event_message=event_message):
        raise RuntimeError(f"Failed to create event '{event_message}'.")

    logger.info("Event was created.")
