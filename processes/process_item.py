"""Module to handle item processing"""

import logging

from mbu_rpa_core.exceptions import BusinessError, ProcessError

from helpers.config import (
    DASHBOARD_STEP_4_NAME,
    DASHBOARD_STEP_5_NAME,
)
from helpers.context_handler import get_context_values
from processes.application_handler import close, get_app
from processes.sub_processes.clean_up import clean_up, release_keys
from processes.sub_processes.handlers.checkpoints_handler import (
    check_clinic_data_and_consent,
    validate_contractor,
)
from processes.sub_processes.handlers.dashboard_data_handler import (
    update_dashboard_step_run,
    update_process_run_metadata,
)
from processes.sub_processes.handlers.document_handler import journalize_document
from processes.sub_processes.handlers.journalizing_db_handler import (
    update_process_status,
)
from processes.sub_processes.handlers.journalnote_handler import create_journalnote
from processes.sub_processes.handlers.os2forms_handler import get_os2forms_document
from processes.sub_processes.init_set_context import set_context_vars

logger = logging.getLogger(__name__)


def process_item(item_data: dict, item_reference: str, item_id: str):
    """Function to handle item processing"""
    try:
        release_keys()

        # Set context variables for further processing
        set_context_vars(item_data, item_reference, item_id)

        # Update process run metadata with clinic phone number and dispatch ID
        update_process_run_metadata(item_data)

        # Update dashboard for step 4
        update_dashboard_step_run(step_name=DASHBOARD_STEP_4_NAME, status="running")

        update_dashboard_step_run(step_name=DASHBOARD_STEP_4_NAME, status="success")

        # Set journalizing process status in RPA database
        update_process_status("InProgress")

        # Get the application instance
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        logger.info("Opening patient in Solteq Tand application...")
        solteq_app.open_patient(get_context_values("cpr"))

        # Download document from OS2
        get_os2forms_document()

        def journalize_form_document():
            """Journalize form document in Solteq Tand application"""
            update_dashboard_step_run(step_name=DASHBOARD_STEP_5_NAME, status="running")

            journalize_document()
            create_journalnote()

            update_dashboard_step_run(step_name=DASHBOARD_STEP_5_NAME, status="success")

        # Journalize form document
        journalize_form_document()

        # Check if contractor exists in SolteqTand database and update contractor if exists.
        # Step 6
        validate_contractor()

        # Check if clinic data matches and if consent is given
        # Step 7
        check_clinic_data_and_consent()

        # Update journalizing process status in RPA database
        update_process_status("Successful")
    except BusinessError as be:
        logger.error("Business error occurred: %s", be)
        update_process_status("Failed")
        raise be
    except Exception as e:
        logger.error("%s", e)
        update_process_status("Failed")
        raise ProcessError("A process error occurred.") from e
    finally:
        clean_up()
        close()
