"""Handler for journalization and journal note creation step"""

from helpers.context_functions import get_context_values
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard
from processes.shared.handlers.journalizing.solteq_document_handler import (
    journalize_document,
)
from processes.shared.handlers.os2forms_handler import get_os2forms_document


def process_journalization_step(
    document_type: str,
    document_file_name: str,
) -> None:
    """Journalize form document in Solteq."""
    handle_process_dashboard(
        status="running",
        process_step_name=get_context_values("current_step_name"),
    )

    get_os2forms_document()

    journalize_document(
        document_type=document_type,
        document_file_name=document_file_name,
    )

    handle_process_dashboard(
        status="success",
        process_step_name=get_context_values("current_step_name"),
    )
