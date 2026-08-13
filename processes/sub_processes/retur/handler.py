"""Handler for the consent step in the 'Retur' process."""

import logging

from mbu_solteqtand_shared_components.database.db_handler import SolteqTandDatabase

from helpers.credential_constants import get_rpa_constant
from processes.shared.handlers.journalizing.solteq_note_handler import (
    create_journalnote,
)
from processes.sub_processes.retur import config

logger = logging.getLogger(__name__)


def create_receipt_journal_note():
    """Creates the journal note tied to the receipt from OS2Forms."""

    create_journalnote(
        journal_note_message=config.ADM_NOTE_MESSAGE,
        checkmark_in_complete=True,
        note_type=config.ADM_NOTE_TYPE,
    )


def get_clinic_name(ssn: str):
    """Fetches the name of the given patients primary clinic."""

    solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
    database = SolteqTandDatabase(solteq_db_conn)

    clinic_response = database.get_list_of_primary_dental_clinics(
        filters={"p.cpr": ssn}
    )

    primary_dental_clinic_name = (
        clinic_response[0].get("preferredDentalClinicName") if clinic_response else None
    )

    return primary_dental_clinic_name
