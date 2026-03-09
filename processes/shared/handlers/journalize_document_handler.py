"""Handler for journalizing documents in Solteq Tand application"""

from helpers.context_functions import get_context_values, set_context_values
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard
from processes.shared.handlers.document_handler import journalize_document
from processes.shared.handlers.journalnote_handler import create_journalnote
from processes.shared.handlers.os2forms_handler import get_os2forms_document


def journalize_form_document(
    current_step_name: str,
    document_type: str,
    document_file_name: str,
    journal_note_message: str,
):
    """Function to handle the journalization of a form document."""

    set_context_values(current_step_name=current_step_name)

    get_os2forms_document()

    handle_process_dashboard(
        status="running",
        process_step_name=get_context_values("current_step_name"),
    )

    journalize_document(
        document_type=document_type,
        document_file_name=document_file_name,
    )

    create_journalnote(journal_note_message=journal_note_message)

    handle_process_dashboard(
        status="success",
        process_step_name=get_context_values("current_step_name"),
    )
