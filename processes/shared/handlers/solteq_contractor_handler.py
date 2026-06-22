"""Module to handle Solteq contractor operations."""

import logging
import os

from mbu_dev_shared_components.solteqtand.database import SolteqTandDatabase
from mbu_rpa_core.exceptions import BusinessError

from helpers.context_functions import get_context_values, set_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard

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


def _try_match_by_provider_and_phone(
    database: SolteqTandDatabase, provider_number, phone_number
):
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


def validate_contractor():
    """Validate contractor in SolteqTand database and update contractor if exists."""
    try:
        # Update dashboard to indicate step is running
        handle_process_dashboard(
            status="running", process_step_name=get_context_values("current_step_name")
        )

        # Use the clinic lookup function
        match_result = match_clinic()

        if not match_result["success"]:
            contractor_lookup_error = {
                "type": "BusinessError",
                "message": """Kontakt Tandplejens administration, tandplejen@mbu.aarhus.dk, og bed om at få undersøgt, om tandklinikken er oprettet i Solteq eller om den mangler oplysninger om ydernummer eller telefonnummer, der matcher det i EDI.
                Afvent svar.
                Du kan genstarte processen, når klinikken er oprettet eller dens oplysninger er rettet i Solteq. """,
            }
            logger.error(
                "Contractor not found in SolteqTand database. Error: %s",
                match_result["error"],
            )
            raise BusinessError(contractor_lookup_error["message"])

        # Get matched clinic data
        matched_clinic = match_result["clinic"]
        logger.info("Matched clinic data: %s", matched_clinic)

        # Get current contractor data from patient
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
        solteq_db_obj = SolteqTandDatabase(conn_str=solteq_db_conn)
        filters = {
            "p.cpr": get_context_values("cpr"),
        }
        current_extern_dentist_data = solteq_db_obj.get_list_of_extern_dentist(
            filters=filters
        )

        logger.info("Current extern dentist data: %s", current_extern_dentist_data)
        logger.info("Matched clinic data: %s", matched_clinic)

        new_contractor_id = matched_clinic.get("contractorId", [])
        new_contractor_phone_number = matched_clinic.get("phoneNumber", [])

        logger.info("New contractor ID: %s", new_contractor_id)
        logger.info("New contractor phone number: %s", new_contractor_phone_number)

        current_contractor_id = (
            current_extern_dentist_data[0]["contractorId"]
            if current_extern_dentist_data
            else ""
        )
        current_contractor_phone_number = (
            current_extern_dentist_data[0]["phoneNumber"]
            if current_extern_dentist_data
            else ""
        )

        logger.info(
            "Comparing contractors - Current: %s vs New: %s",
            current_contractor_id,
            new_contractor_id,
        )

        # Update contractor if it has changed or if no current contractor is set
        logger.info("Checking if contractor data has changed or is missing...")
        if not current_extern_dentist_data or (
            current_contractor_id != new_contractor_id
            or current_contractor_phone_number != new_contractor_phone_number
        ):
            logger.info(
                "Contractor data has changed or is missing. Updating contractor information..."
            )
            solteq_app.change_private_clinic(
                private_clinic=matched_clinic.get("name", [])
            )

        handle_process_dashboard(
            status="success", process_step_name=get_context_values("current_step_name")
        )
    except BusinessError as be:
        logger.error("Business error: %s", be)
        raise be
    except Exception as e:
        logger.error("Error validating contractor: %s", e)
        raise e


def check_extern_clinic_deal(contractor_id: str) -> None:
    """Check if extern clinic has a valid deal with Aarhus Kommune.

    Args:
        contractor_id (str): Unique identifier for the contractor

    Raises:
        ValueError: If contractor ID is missing or if extern clinic does not have a deal with Aarhus Kommune
        TypeError: If db_conn does not have the required attribute or method
        RuntimeError: If there is an error during database operation
    """
    if not contractor_id or not isinstance(contractor_id, str):
        raise ValueError("Contractor ID is required to check extern clinic deal.")

    db_conn = SolteqTandDatabase(conn_str=get_rpa_constant("solteq_tand_db_connstr"))

    filter_params = {
        "type": "3",
        "contractorId": contractor_id,
    }

    try:
        logger.info(
            "Checking if extern clinic has a deal with Aarhus Kommune with contractorId: %s",
            contractor_id,
        )
        result = db_conn.get_list_of_clinics(filters=filter_params)
    except RuntimeError as re:
        logger.error(
            "Runtime error occurred while checking extern clinic deal for contractor %s: %s",
            contractor_id,
            str(re),
        )
        raise
    except Exception as e:
        logger.error(
            "Unexpected error occurred while checking extern clinic deal for contractor %s: %s",
            contractor_id,
            str(e),
        )
        raise

    if not result:
        logger.error(
            "No deal found for extern clinic with contractorId: %s.",
            contractor_id,
        )
        #  raise ValueError("Extern clinic does not have a deal with Aarhus Kommune.")
        #  raise CancelledError("Extern clinic does not have a deal with Aarhus Kommune.")
        raise BusinessError(
            "Den eksterne klinik har ikke en aftale med Aarhus Kommune."
        )

    logger.info("Extern clinic has a deal with Aarhus Kommune.")
