"""Handler for fetching and updating dashboard data."""

import datetime
import logging
import os

import requests
from mbu_rpa_core.exceptions import BusinessError

from helpers import config
from helpers.context_handler import get_context_values

logger = logging.getLogger(__name__)


def get_dashboard_process_data() -> dict:
    """
    Fetches dashboard data from an external API using the CPR number from context values.

    Returns:
        dict: JSON response from the dashboard API.

    Raises:
        RuntimeError: For any errors during the API request or data retrieval.
        ValueError: If required context values are missing.
        KeyError: If the expected data is not found in the API response.
        requests.RequestException: For any errors during the API request.
    """
    try:
        cpr = get_context_values("cpr")
        if not cpr:
            raise ValueError("CPR number not found in context values.")

        base_endpoint = os.environ.get("DASHBOARD_API_URL")
        if not base_endpoint:
            raise ValueError("DASHBOARD_API_URL environment variable not set.")

        url = f"{base_endpoint}/runs/?process_id=1&meta_filter=cpr:{cpr}&order_by=created_at&sort_direction=desc"

        api_key = os.environ.get("API_ADMIN_TOKEN")
        if not api_key:
            raise ValueError("API_ADMIN_TOKEN environment variable not set.")

        response = requests.get(url=url, headers={"x-api-key": api_key}, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Error fetching dashboard data: {e}") from e
    except ValueError as ve:
        raise RuntimeError(f"Value error: {ve}") from ve
    except Exception as ex:
        raise RuntimeError(f"An unexpected error occurred: {ex}") from ex


def get_dashboard_process_id(process_name: str, api_context: dict) -> dict:
    """Retrieve the process ID for a given process name."""
    logger.info("Retrieving process ID for process name: %s", process_name)
    try:
        endpoint = api_context["endpoint"]
        headers = api_context["headers"]

        processes = requests.get(
            f"{endpoint}/processes/?include_deleted=false",
            headers=headers,
            timeout=30,
        ).json()
        process = next(p for p in processes["items"] if p["name"] == process_name)
        process_id = process["id"]

        return process_id
    except Exception as e:
        logger.error("Error retrieving process ID: %s", e)
        raise


def get_dashboard_step_run_id(
    process_id: int, step_name: str, api_context: dict
) -> dict:
    """Retrieve the step ID for a given process ID and step name."""
    logger.info("Retrieving step ID for step name: %s", step_name)
    try:
        endpoint = api_context["endpoint"]
        headers = api_context["headers"]

        steps = requests.get(
            f"{endpoint}/steps/process/{process_id}?include_deleted=false",
            headers=headers,
            timeout=30,
        ).json()
        step = next(s for s in steps if s["name"] == step_name)
        step_id = step["id"]
        return step_id
    except Exception as e:
        logger.error("Error retrieving step ID: %s", e)
        raise


def get_dashboard_run_id(process_id: int, cpr: str, api_context: dict) -> dict:
    """Retrieve the latest run ID for a given process ID and CPR number."""
    try:
        endpoint = api_context["endpoint"]
        headers = api_context["headers"]

        runs_url = f"{endpoint}/runs/?process_id={process_id}&meta_filter=cpr:{cpr}"
        runs = requests.get(runs_url, headers=headers, timeout=30).json()
        run_id = runs["items"][0]["id"]
        return run_id
    except Exception as e:
        logger.error("Error retrieving run ID: %s", e)
        raise


def get_dashboard_step_run_details(
    run_id: int, step_id: int, api_context: dict
) -> dict:
    """Retrieve the step run details for a given run ID and step ID."""
    # 4. Get the step run by run_id and step_id
    try:
        endpoint = api_context["endpoint"]
        headers = api_context["headers"]

        step_run = requests.get(
            f"{endpoint}/step-runs/run/{run_id}/step/{step_id}?include_deleted=false",
            headers=headers,
            timeout=30,
        ).json()
        return step_run
    except Exception as e:
        logger.error("Error retrieving step run details: %s", e)
        raise


def get_step_run_id_for_process_step_cpr(
    process_name: str, step_name: str, cpr: str, api_context: dict
) -> int:
    """
    Retrieves the step run ID for the given process name, step name, and CPR number.
    """
    process_id = get_dashboard_process_id(process_name, api_context)
    step_id = get_dashboard_step_run_id(process_id, step_name, api_context)
    run_id = get_dashboard_run_id(process_id, cpr, api_context)
    step_run_details = get_dashboard_step_run_details(run_id, step_id, api_context)
    step_run_id = step_run_details.get("id")
    if step_run_id is None:
        raise RuntimeError("Step run ID not found in step run details.")
    return step_run_id


def update_dashboard_step_run_by_id(
    step_run_id: int, update_data: dict, api_context: dict
) -> tuple[dict, int]:
    """Update the step run details for a given step run ID."""
    try:
        endpoint = api_context["endpoint"]
        headers = api_context["headers"]

        response = requests.patch(
            f"{endpoint}/step-runs/{step_run_id}",
            headers={**headers, "Accept-Charset": "utf-8"},
            json=update_data,
            timeout=30,
        )
        response.raise_for_status()
        return response.json(), response.status_code
    except Exception as e:
        logger.error("Error updating step run details: %s", e)
        raise


def build_step_run_update(
    status: str, failure: Exception | None = None, rerun: bool = False
) -> dict:
    """Builds the update data for a dashboard step run."""
    current_time = (
        datetime.datetime.now(datetime.UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

    # Determine failure content based on exception type
    failure_data = None
    if failure:
        if isinstance(failure, BusinessError):
            # For BusinessError, use the exception details as-is
            failure_data = {
                "error_code": type(failure).__name__,
                "message": str(failure),
                "details": str(failure.__traceback__)
                if failure.__traceback__
                else None,
            }
        else:
            # For all other exceptions, use predefined error message
            failure_data = {
                "message": "Processen er fejlet",
                "code": (
                    "Digitalisering er i gang med at undersøge fejlen og genstarte processen.\n\n"
                    "Kontakt Digitalisering, hvis fejlen ikke er rettet efter 2 arbejdsdage."
                ),
            }

    # Rerun configuration
    rerun_data = {}
    if rerun:
        rerun_data = {
            "workitem_id": f"{get_context_values('work_item')}",
        }

    update_data = {
        "status": status,
        "started_at": current_time,
        "finished_at": current_time,
        "failure": failure_data,
        "rerun_config": rerun_data,
    }
    return update_data


def update_dashboard_step_run(
    step_name: str, status: str, failure: Exception | None = None, rerun: bool = False
) -> None:
    """Update dashboard step run status for a given step name and status."""
    logger.info("Updating dashboard step run: %s to status: %s", step_name, status)
    step_run_id = get_step_run_id_for_process_step_cpr(
        process_name=config.DASHBOARD_PROCESS_NAME,
        step_name=step_name,
        cpr=get_context_values("cpr"),
        api_context=get_context_values("api_context"),
    )
    logger.info("Step run ID for step '%s': %s", step_name, step_run_id)
    update_data = build_step_run_update(status=status, failure=failure, rerun=rerun)
    logger.info("Update data prepared: %s", update_data)
    update_dashboard_step_run_by_id(
        step_run_id=step_run_id,
        update_data=update_data,
        api_context=get_context_values("api_context"),
    )
    logger.info("Dashboard step run updated for step '%s'", step_name)


def check_if_clinic_data_match() -> bool:
    """
    Checks if the clinic data from the dashboard matches the context values.

    Returns:
        bool: True if clinic data matches, False otherwise.
    """
    try:
        dashboard_data = get_dashboard_process_data()
        runs = dashboard_data.get("items", [])
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
    except Exception as exc:
        raise RuntimeError(
            f"An error occurred while checking clinic data match: {exc}"
        ) from exc


def update_process_run_metadata(item_data: dict) -> dict:
    """Update process run metadata with clinic phone number and dispatch ID"""
    process_run_metadata = {}
    phone = item_data.get("klinik_telefonnummer", "")
    ydernummer = item_data.get("klinik_ydernummer", "")

    if phone:
        process_run_metadata["new_clinic_phone_number"] = phone
    if ydernummer:
        process_run_metadata["new_clinic_ydernummer"] = ydernummer

    logger.info("Updating process run metadata: %s", process_run_metadata)

    api_context = get_context_values("api_context")
    endpoint = api_context["endpoint"]
    headers = api_context["headers"]
    HTTP_STATUS_OK = 200

    process_id = get_dashboard_process_id(config.DASHBOARD_PROCESS_NAME, api_context)
    if not process_id:
        logger.error("Process ID not found for process name")
        raise RuntimeError("Process ID not found for process name.")

    process_run_id = get_dashboard_run_id(
        process_id=process_id,
        cpr=get_context_values("cpr"),
        api_context=get_context_values("api_context"),
    )

    if not process_run_id:
        logger.error("Process run ID not found")
        raise RuntimeError("Process run ID not found.")

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

    return response.json()
