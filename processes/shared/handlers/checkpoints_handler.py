"""Handles checkpoints for clinic data and contractor validation"""

import logging

from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase
from mbu_process_dashboard_shared_components.process import find_process_id_and_steps
from mbu_process_dashboard_shared_components.process_dashboard_client import (
    ProcessDashboardClient,
)
from mbu_process_dashboard_shared_components.process_run import get_all_process_runs
from mbu_rpa_core.exceptions import BusinessError

from helpers.context_functions import get_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app
from processes.shared.handlers.dashboard_data_handler import (
    handle_process_dashboard,
)
from processes.shared.handlers.solteq_contractor_handler import (
    match_clinic,
)

logger = logging.getLogger(__name__)


def _check_if_clinic_data_match(
    client: ProcessDashboardClient, process_name: str
) -> bool:
    """
    Checks if the clinic data from the dashboard matches the context values.

    Returns:
        bool: True if clinic data matches, False otherwise.
    """
    try:
        process_id, _ = find_process_id_and_steps(client, process_name)
        if not process_id:
            raise ValueError(
                f"Process with name '{process_name}' not found in dashboard."
            )

        runs = get_all_process_runs(
            client=client,
            process_id=process_id,
            meta_filter=f"cpr:{get_context_values('cpr')}",
        )
        if not runs:
            return False

        latest_run = runs[0]
        meta = latest_run.get("meta", {})

        # Extract clinic data from dashboard meta
        dashboard_clinic_phone = (
            (meta.get("new_clinic_phone_number") or "").strip().lower()
        )
        dashboard_clinic_provider = (
            (meta.get("new_clinic_ydernummer") or "").strip().lower()
        )

        # Extract clinic data from context values
        context_clinic_phone = (
            (get_context_values("clinic_phone_number") or "").strip().lower()
        )
        context_clinic_provider = (
            (get_context_values("clinic_provider_number") or "").strip().lower()
        )

        return (
            dashboard_clinic_phone == context_clinic_phone
            or dashboard_clinic_provider == context_clinic_provider
        )
    except Exception as e:
        logger.error("Error checking clinic data match: %s", e)
        raise e


def check_clinic_data_and_consent(process_step_name: str, process_name: str):
    """Check if clinic data matches and consent is given"""
    try:
        # Update dashboard to indicate step is running
        handle_process_dashboard(status="running", process_step_name=process_step_name)

        clinic_data_matches = _check_if_clinic_data_match(
            client=get_context_values("client"), process_name=process_name
        )
        consent_given = get_context_values("consent")

        if not clinic_data_matches and consent_given:
            clinic_match_and_consent_error = {
                "type": "BusinessError",
                "message": "Klinikdata matcher ikke, men samtykke givet.",
            }
            logger.error("Clinic data does not match, but consent has been given.")
            raise BusinessError(clinic_match_and_consent_error["message"])

        elif not clinic_data_matches and not consent_given:
            clinic_match_and_consent_error = {
                "type": "BusinessError",
                "message": "Klinikdata matcher ikke, og samtykke ikke givet.",
            }
            logger.error("Clinic data does not match, and consent has not been given.")
            raise BusinessError(clinic_match_and_consent_error["message"])

        handle_process_dashboard(status="success", process_step_name=process_step_name)
    except BusinessError as be:
        logger.error("Business error: %s", be)
        raise be
    except Exception as e:
        logger.error("Error checking clinic data and consent: %s", e)
        raise e


def validate_contractor(step_name: str):
    """Validate contractor in SolteqTand database and update contractor if exists."""
    try:
        # Update dashboard to indicate step is running
        handle_process_dashboard(status="running", process_step_name=step_name)

        # Use the clinic lookup function
        match_result = match_clinic()

        if not match_result["success"]:
            contractor_lookup_error = {
                "type": "BusinessError",
                "message": f"""Vi kunne ikke matche den valgte tandklinik med en klinik i Solteq – hverken via ydernummer eller telefonnummer.
                Detaljer: {match_result["error"]}
                Kontakt Tandplejens administration, tandplejen@mbu.aarhus.dk, og bed om at få undersøgt,
                om tandklinikken er oprettet i Solteq eller om den mangler oplysninger om ydernummer eller telefonnummer, der matcher det i EDI.
                Afvent svar.
                Du kan genstarte processen, når klinikken er oprettet eller dens oplysninger er rettet i Solteq.""",
            }
            logger.error(
                "Contractor not found in SolteqTand database. Error: %s",
                match_result["error"],
            )
            raise BusinessError(contractor_lookup_error["message"])

        # Get matched clinic data
        matched_clinic = match_result["clinic"]
        logger.info("Matched clinic data: %s", matched_clinic)

        # Get current contractor data from patient
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
        solteq_db_obj = SolteqTandDatabase(conn_str=solteq_db_conn)
        filters = {
            "p.cpr": get_context_values("cpr"),
        }
        current_extern_dentist_data = solteq_db_obj.get_list_of_extern_dentist(
            filters=filters
        )

        logger.info("Current extern dentist data: %s", current_extern_dentist_data)
        logger.info("Matched clinic data: %s", matched_clinic)

        new_contractor_id = matched_clinic.get("contractorId", [])
        new_contractor_phone_number = matched_clinic.get("phoneNumber", [])

        logger.info("New contractor ID: %s", new_contractor_id)
        logger.info("New contractor phone number: %s", new_contractor_phone_number)

        current_contractor_id = (
            current_extern_dentist_data[0]["contractorId"]
            if current_extern_dentist_data
            else ""
        )
        current_contractor_phone_number = (
            current_extern_dentist_data[0]["phoneNumber"]
            if current_extern_dentist_data
            else ""
        )

        logger.info(
            "Comparing contractors - Current: %s vs New: %s",
            current_contractor_id,
            new_contractor_id,
        )

        # Update contractor if it has changed or if no current contractor is set
        logger.info("Checking if contractor data has changed or is missing...")
        if not current_extern_dentist_data or (
            current_contractor_id != new_contractor_id
            or current_contractor_phone_number != new_contractor_phone_number
        ):
            logger.info(
                "Contractor data has changed or is missing. Updating contractor information..."
            )
            solteq_app.change_private_clinic(
                private_clinic=matched_clinic.get("name", [])
            )

        handle_process_dashboard(status="success", process_step_name=step_name)
    except BusinessError as be:
        logger.error("Business error: %s", be)
        raise be
    except Exception as e:
        logger.error("Error validating contractor: %s", e)
        raise e
