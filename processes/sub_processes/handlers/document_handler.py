"""Module to handle document journalizing in SolteqTand"""

import logging

from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase

from helpers import config
from helpers.context_handler import get_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app
from processes.sub_processes.handlers.dashboard_data_handler import (
    update_dashboard_step_run,
)
from processes.sub_processes.handlers.journalizing_db_handler import (
    update_process_status,
    update_response_metadata,
)

logger = logging.getLogger(__name__)


def journalize_document():
    """Function to journalize document in SolteqTand"""
    try:
        logger.info("Starting document journalizing process.")

        # Get the application instance
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
        document_type = config.DOCUMENT_TYPE
        full_path = get_context_values("os2forms_document_path")
        item_reference = get_context_values("reference")

        # Create RPA database object
        solteq_db_obj = SolteqTandDatabase(conn_str=solteq_db_conn)

        # Check if document already exists else journalize it
        filters = {
            "p.cpr": get_context_values("cpr"),
            "ds.OriginalFilename": config.DOCUMENT_FILE_NAME,
            "ds.DocumentType": document_type,
            "ds.DocumentDescription": f"%{item_reference}%",
            "ds.rn": "1",
            "ds.DocumentStoreStatusId": "1",
        }
        document_exists = solteq_db_obj.get_list_of_documents(filters=filters)

        if not document_exists:
            solteq_app.create_document(
                document_full_path=full_path,
                document_type=document_type,
                document_description=item_reference,
            )

            check_document_journalized = solteq_db_obj.get_list_of_documents(
                filters=filters
            )

            if not check_document_journalized:
                raise RuntimeError("Document journalizing failed.")

        # Update journalizing response metadata in RPA database
        update_response_metadata(
            step_name="Document", json_fragment={"DocumentCreated": True}
        )
        logger.info("Document journalized successfully.")
    except Exception as e:
        update_response_metadata(
            step_name="Document", json_fragment={"DocumentCreated": False}
        )
        update_process_status("Failed")
        update_dashboard_step_run(
            step_name=config.DASHBOARD_STEP_5_NAME,
            status="failed",
            failure=e,
            rerun=True,
        )
        logger.error("Error journalizing document: %s", e)
        raise RuntimeError("Error journalizing document: " + str(e)) from e
