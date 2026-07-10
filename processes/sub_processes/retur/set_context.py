"""Module to set context values for processing"""

from helpers.context_functions import set_context_values


def set_context_vars(item_data: dict, item_reference: str, item_id: str):
    """Set context values based on item data"""

    set_context_values(
        os2_forms_url=item_data.get("url", ""),
        reference=item_reference,
        cpr=item_data.get("cpr", ""),
        form_data=item_data.get("form_data", ""),
        work_item=item_id,
    )
