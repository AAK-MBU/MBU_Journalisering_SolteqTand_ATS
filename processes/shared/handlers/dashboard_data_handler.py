"""Handler for fetching and updating dashboard data."""

import logging
import os
from typing import Any

import requests
from mbu_process_dashboard_shared_components import (
    process,
    process_run,
    process_step_run,
)
from mbu_process_dashboard_shared_components.process_dashboard_client import (
    ProcessDashboardClient,
)

from helpers.context_functions import get_context_values, set_context_values

logger = logging.getLogger(__name__)

# Initialize the ProcessDashboardClient once and reuse it for all function calls
CLIENT = ProcessDashboardClient(api_admin_token=os.environ.get("API_ADMIN_TOKEN"))
set_context_values(client=CLIENT)


def handle_process_dashboard(
    status: str,
    process_step_name: str,
    failure: Exception | None = None,
    rerun_config: dict | None = None,
):
    """
    Method for handling updating the process dashboard
    """

    client = CLIENT

    status_update_data: dict[str, Any] = {"status": status}

    citizen_cpr = get_context_values("cpr")

    logger.info("before get_step_run_id_for_process_step_cpr() ...")

    step_run_id = process_step_run.get_step_run_id_for_process_step_cpr(
        client=client,
        process_name="Udskrivning 22 år",
        step_name=process_step_name,
        cpr=citizen_cpr,
    )

    if failure:
        step_run_update_data = process_step_run.build_step_run_update(
            status=status, failure=failure, rerun_config=rerun_config
        )

        status_update_data["failure"] = failure

    else:
        step_run_update_data = process_step_run.build_step_run_update(status=status)

    logger.info("before update_dashboard_step_run_by_id() ...")

    updated_step_run_data, status_code = (
        process_step_run.update_dashboard_step_run_by_id(
            client=client,
            step_run_id=step_run_id,
            update_data=step_run_update_data,
        )
    )

    return updated_step_run_data, status_code


def update_process_run_metadata(item_data: dict, process_name: str) -> dict:
    """Update process run metadata with clinic phone number and dispatch ID"""

    process_run_metadata = {}
    phone = item_data.get("klinik_telefonnummer", "")
    ydernummer = item_data.get("klinik_ydernummer", "")

    if phone:
        process_run_metadata["new_clinic_phone_number"] = phone
    if ydernummer:
        process_run_metadata["new_clinic_ydernummer"] = ydernummer

    logger.info("Updating process run metadata: %s", process_run_metadata)

    client = CLIENT
    citizen_cpr = get_context_values("cpr")

    process_id = process.get_dashboard_process_id(
        client=client, process_name=process_name
    )

    if not process_id:
        logger.error("Process ID not found for process name")
        raise RuntimeError("Process ID not found for process name.")

    process_run_id = process_run.get_dashboard_run_id(
        client=client,
        process_id=int(process_id),
        cpr=citizen_cpr,
    )

    if not process_run_id:
        logger.error("Process run ID not found")
        raise RuntimeError("Process run ID not found.")

    api_context = get_context_values("api_context")
    endpoint = api_context["endpoint"]
    headers = api_context["headers"]
    HTTP_STATUS_OK = 200

    response = requests.patch(
        url=(f"{endpoint}/runs/{process_run_id}/metadata"),
        json={"meta": process_run_metadata},
        headers=headers,
        timeout=10,
    )

    if response.status_code != HTTP_STATUS_OK:
        logger.error(
            "Failed to update process run metadata. Status code: %s, Response: %s",
            response.status_code,
            response.text,
        )
        raise RuntimeError("Failed to update process run metadata.")

    logger.info("Process run metadata updated successfully: %s", process_run_metadata)

    return response.json()
