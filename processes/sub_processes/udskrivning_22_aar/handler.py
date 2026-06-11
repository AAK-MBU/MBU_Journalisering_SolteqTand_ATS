"""Handler for the consent step in the Udskrivning 22 år process."""

import logging
import os

from mbu_process_dashboard_shared_components.process import find_process_id_and_steps
from mbu_process_dashboard_shared_components.process_run import (
    ProcessDashboardClient,
    get_all_process_runs,
)
from mbu_rpa_core.exceptions import BusinessError

from helpers.context_functions import get_context_values
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard
from processes.shared.handlers.journalizing.solteq_note_handler import (
    create_journalnote,
)
from processes.sub_processes.udskrivning_22_aar import config

logger = logging.getLogger(__name__)


def _check_if_clinic_data_match(process_name: str) -> bool:
    """
    Checks if the clinic data from the dashboard matches the context values.

    Returns:
        bool: True if clinic data matches, False otherwise.
    """
    try:
        api_admin_token = os.environ.get("API_ADMIN_TOKEN")
        if not api_admin_token:
            raise ValueError("API_ADMIN_TOKEN environment variable is not set")

        client = ProcessDashboardClient(api_admin_token=api_admin_token)

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


def _check_clinic_data_and_consent(process_name: str):
    """Check if clinic data matches and consent is given"""
    try:
        clinic_data_matches = _check_if_clinic_data_match(process_name=process_name)
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

    except BusinessError as be:
        logger.error("Business error: %s", be)
        raise be
    except Exception as e:
        logger.error("Error checking clinic data and consent: %s", e)
        raise e


def consent_udskrivning22aar_handler() -> None:
    """Handler for consent step, checks clinic data and consent, and creates journal note"""
    try:
        handle_process_dashboard(
            status="running",
            process_step_name=get_context_values("current_step_name"),
        )

        create_journalnote(
            journal_note_message=config.ADM_NOTE_MESSAGE,
            checkmark_in_complete=True,
            note_type=config.ADM_NOTE_TYPE,
        )

        _check_clinic_data_and_consent(
            process_name=config.DASHBOARD_PROCESS_NAME,
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
