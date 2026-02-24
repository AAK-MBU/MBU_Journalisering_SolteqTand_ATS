"""Module to handle Solteq contractor operations."""

import logging
import os

from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase
from mbu_rpa_core.exceptions import BusinessError

from helpers.context_handler import get_context_values, set_context_values

logger = logging.getLogger(__name__)


def _more_than_one_clinic_found_error():
    """Raise error when multiple clinics are found."""
    error_message = (
        "Fandt flere klinikker i Solteq med samme ydernummer eller telefonnummer."
    )
    logger.error(
        "Multiple clinics found in SolteqTand database for the given provider number or phone number."
    )
    raise BusinessError(error_message)


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
            "phoneNumber": get_context_values(
                "clinic_phone_number"
            ),  # Phonenumber from form data
            "contractorId": get_context_values(
                "clinic_provider_number"
            ),  # Provider number from form data
        }

        result = database.get_list_of_clinics(or_filters=[filters])

        # Set private clinic data from the database to context
        set_context_values(private_clinic_data=result)

        exists = result is not None and len(result) > 0
        logger.info("Clinic check result: %s", exists)

        return exists
    except Exception as e:
        logger.error("Error occurred while checking clinic: %s", e)
        return False


def _try_match_by_provider_and_phone(database, provider_number, phone_number):
    """Try to match clinic by provider number and optionally phone number."""
    clinics_by_provider = database.get_list_of_clinics(
        filters={"contractorId": provider_number}
    )

    if not clinics_by_provider:
        return None

    if phone_number:
        matching_clinics = [
            c for c in clinics_by_provider if c.get("phoneNumber") == phone_number
        ]
        if len(matching_clinics) > 1:
            _more_than_one_clinic_found_error()
        elif len(matching_clinics) == 1:
            return matching_clinics
    else:
        if len(clinics_by_provider) > 1:
            _more_than_one_clinic_found_error()
        return clinics_by_provider

    return None


def _try_match_by_phone(database, phone_number):
    """Try to match clinic by phone number only."""
    clinics_by_phone = database.get_list_of_clinics(
        filters={"phoneNumber": phone_number}
    )

    if len(clinics_by_phone) > 1:
        _more_than_one_clinic_found_error()
    elif len(clinics_by_phone) == 1:
        return clinics_by_phone

    return None


def match_clinic():
    """
    Clinic matching with the following logic:
    1. If provider number exists: match on provider number + phone number
       - If multiple clinics found with same provider number AND phone number: return error
       - If no match found: try phone number only
    2. If no provider number (or no match in step 1): match on phone number only
       - If multiple clinics found with same phone number: return error
    3. If no match found in either case: return error

    Returns:
        dict: {
            "success": bool,
            "clinic": dict,  # Matched clinic object
            "error": str or None  # Error message if any
        }
    """
    result = {
        "success": False,
        "clinic": None,
        "error": None,
    }

    try:
        provider_number = get_context_values("clinic_provider_number")
        phone_number = get_context_values("clinic_phone_number")

        logger.info(
            "Starting clinic lookup with provider_number: %s, phone_number: %s",
            provider_number,
            phone_number,
        )

        database = SolteqTandDatabase(
            os.environ.get("DBCONNECTIONSTRINGSOLTEQTAND", "")
        )

        # Step 1: Try matching by provider number and phone number
        if provider_number:
            logger.info(
                "Step 1: Provider number provided, searching with provider number + phone number."
            )
            match_result = _try_match_by_provider_and_phone(
                database, provider_number, phone_number
            )
            if match_result:
                result["success"] = True
                result["clinic"] = match_result[0]
                set_context_values(private_clinic_data=match_result)
                logger.info("Match found by provider number")
                return result

        # Step 2: Try matching by phone number only
        if phone_number and not result["success"]:
            logger.info("Step 2: Searching by phone number only.")
            match_result = _try_match_by_phone(database, phone_number)
            if match_result:
                result["success"] = True
                result["clinic"] = match_result[0]
                set_context_values(private_clinic_data=match_result)
                logger.info("Match found by phone number")
                return result

        # Step 3: No match found
        if not result["success"]:
            result["error"] = (
                "No clinic found matching the provided provider number or phone number."
            )
            logger.error(result["error"])

    except Exception as e:
        logger.error("Error occurred during clinic matching: %s", e)
        result["error"] = f"An error occurred: {str(e)}"

    return result
