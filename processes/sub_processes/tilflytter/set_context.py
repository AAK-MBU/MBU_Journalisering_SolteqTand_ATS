"""Module to set context values for processing"""

from helpers.context_functions import set_context_values

from . import config


def set_context_vars(item_data: dict, item_reference: str, item_id: str):
    """Set context values based on item data"""

    set_context_values(
        os2_forms_url=item_data.get("url", ""),
        reference=item_reference,
        cpr=item_data.get("cpr", ""),
        citizen_phone_number=item_data.get("borger_telefonnummer", ""),
        work_item=item_id,
        document_file_path=config.DOCUMENT_PATH,
        document_file_name=config.DOCUMENT_FILE_NAME,
        current_step_name=None,
    )
