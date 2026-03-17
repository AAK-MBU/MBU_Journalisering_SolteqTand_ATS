"""Handles checkpoints for clinic data and contractor validation"""

import logging

from mbu_process_dashboard_shared_components.process import find_process_id_and_steps
from mbu_process_dashboard_shared_components.process_dashboard_client import (
    ProcessDashboardClient,
)
from mbu_process_dashboard_shared_components.process_run import get_all_process_runs
from mbu_rpa_core.exceptions import BusinessError

from helpers.context_functions import get_context_values
from processes.shared.handlers.dashboard_data_handler import (
    handle_process_dashboard,
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
