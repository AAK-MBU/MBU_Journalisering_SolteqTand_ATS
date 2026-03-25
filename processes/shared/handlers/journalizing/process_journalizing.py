"""Handler for journalization process steps."""

from processes.shared.handlers.journalizing.solteq_document_handler import (
    journalize_document,
)
from processes.shared.handlers.os2forms_handler import get_os2forms_document


def process_journalization_step(
    document_type: str,
    document_file_name: str,
) -> None:
    """Journalize form document in Solteq."""
    get_os2forms_document()

    journalize_document(
        document_type=document_type,
        document_file_name=document_file_name,
    )
