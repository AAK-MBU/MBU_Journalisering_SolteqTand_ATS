"""Module for handling journalizing database operations"""

import json
import logging

from mbu_dev_shared_components.utils.db_stored_procedure_executor import (
    execute_stored_procedure,
)

from helpers.context_handler import get_context_values
from helpers.credential_constants import get_rpa_constant

logger = logging.getLogger(__name__)


def update_process_status(status: str):
    """Function to update journalizing process status in RPA database"""
    try:
        logger.info("Updating process status to: %s", status)

        rpa_db_conn = get_rpa_constant("srvsql59_connection_string")
        reference = get_context_values("reference")

        status_params = {
            "Status": ("str", status),
            "form_id": ("str", f"{reference}"),
        }
        execute_stored_procedure(
            connection_string=rpa_db_conn,
            stored_procedure="journalizing.sp_update_status",
            params=status_params,
        )

        logger.info("Process status updated successfully.")
    except Exception as e:
        logger.error("Error updating process status: %s", e)
        raise RuntimeError("Error updating process status: " + str(e)) from e


def update_response_metadata(step_name: str, json_fragment: dict):
    """Function to update journalizing response metadata in RPA database"""
    try:
        logger.info("Updating response metadata for step: %s", step_name)

        rpa_db_conn = get_rpa_constant("srvsql59_connection_string")
        item_reference = get_context_values("reference")

        sql_data_params = {
            "StepName": ("str", step_name),
            "JsonFragment": ("str", json.dumps(json_fragment)),
            "form_id": ("str", item_reference),
        }
        execute_stored_procedure(
            connection_string=rpa_db_conn,
            stored_procedure="journalizing.sp_update_response",
            params=sql_data_params,
        )

        logger.info("Response metadata updated successfully for step: %s", step_name)
    except Exception as e:
        logger.error("Error updating response metadata for step %s: %s", step_name, e)
        raise RuntimeError("Error updating response metadata: " + str(e)) from e
