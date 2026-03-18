"""Module to set context values for processing"""

from helpers import config as helper_config
from helpers.context_functions import set_context_values

from . import config


def set_context_vars(item_data: dict, item_reference: str, item_id: str):
    """Set context values based on item data"""

    set_context_values(
        os2_forms_url=item_data.get("url", ""),
        reference=item_reference,
        cpr=item_data.get("cpr", ""),
        citizen_phone_number=item_data.get("borger_telefonnummer", ""),
        clinic_name=item_data.get("klinik_navn", ""),
        journal_consent=item_data.get("journal_samtykke"),
        treatment_consent=item_data.get("behandling_samtykke"),
        work_item=item_id,
        document_file_path=helper_config.DOCUMENT_PATH,
        document_file_name=config.DOCUMENT_FILE_NAME,
        process_name=config.DASHBOARD_PROCESS_NAME,
        current_step_name=None,
    )
