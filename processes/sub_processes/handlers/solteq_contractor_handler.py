"""Module to handle Solteq contractor operations."""

import logging
import os

from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase

from helpers.context_handler import get_context_values, set_context_values

logger = logging.getLogger(__name__)


def check_if_clinic_is_in_database() -> bool:
    """
    Check if the clinic exists in the SolteqTand database based on context values.

    Returns:
        bool: True if the clinic exists, False otherwise.

    Raises:
        Exception: For any errors during database access or context retrieval.
    """
    try:
        logger.info("Checking if clinic exists in the SolteqTand database.")
        database = SolteqTandDatabase(
            os.environ.get("DBCONNECTIONSTRINGSOLTEQTAND", "")
        )

        filters = {
            "phoneNumber": get_context_values("clinic_phone_number"),
            "contractorId": get_context_values("clinic_provider_number"),
        }

        result = database.get_list_of_clinics(or_filters=[filters])
        set_context_values(private_clinic_data=result)

        exists = result is not None and len(result) > 0
        logger.info("Clinic check result: %s", exists)

        return exists
    except Exception as e:
        logger.error("Error occurred while checking clinic: %s", e)
        return False
