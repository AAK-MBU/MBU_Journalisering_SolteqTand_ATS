"""Module to set context values for processing"""

import os

from helpers.context_handler import set_context_values


def set_context_vars(item_data: dict, item_reference: str, item_id: str):
    """Set context values based on item data"""
    api_context = {
        "endpoint": os.environ.get("DASHBOARD_API_URL"),
        "api_key": os.environ.get("API_ADMIN_TOKEN"),
        "headers": {"X-API-Key": os.environ.get("API_ADMIN_TOKEN")},
    }
    set_context_values(
        url=item_data.get("url", ""),
        reference=item_reference,
        cpr=item_data.get("cpr", ""),
        clinic_name=item_data.get("klinik_navn", ""),
        clinic_address=item_data.get("klinik_adresse", ""),
        clinic_phone_number=item_data.get("klinik_telefonnummer", ""),
        clinic_provider_number=item_data.get("klinik_ydernummer", ""),
        form_data=item_data.get("form_data", ""),
        consent=bool(item_data.get("samtykke_valg", False)),
        api_context=api_context,
        work_item=item_id,
    )
