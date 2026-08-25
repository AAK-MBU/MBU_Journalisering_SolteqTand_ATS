"""Module to handle Solteq contractor operations."""

import logging

from mbu_rpa_core.exceptions import BusinessError
from mbu_solteqtand_shared_components.application import SolteqTandApp
from mbu_solteqtand_shared_components.database.db_handler import SolteqTandDatabase

from helpers.context_functions import get_context_values, set_context_values
from helpers.credential_constants import get_rpa_constant
from processes.application_handler import get_app
from processes.shared.handlers.dashboard_data_handler import handle_process_dashboard

logger = logging.getLogger(__name__)


# Some contractors don't exist in Solteq under their real provider number,
# so they are redirected to a stand-in clinic that does. The redirect must be
# applied everywhere the provider number is used for a Solteq lookup (clinic
# matching, extern clinic deal check, etc.).
_PROVIDER_NUMBER_REDIRECTS = {
    "469378": {"provider_number": "472034", "phone_number": "86124500"},
}


def resolve_provider_number(provider_number: str) -> str:
    """Return the effective Solteq provider number, applying any redirect."""
    redirect = _PROVIDER_NUMBER_REDIRECTS.get(provider_number)
    return redirect["provider_number"] if redirect else provider_number


def _all_same_values(clinics: list, fields: list) -> bool:
    """Return True if all clinics share identical values for every field in fields."""
    value_sets = {tuple(c.get(f) for f in fields) for c in clinics}
    return len(value_sets) == 1


_RESTART_TEXT = "Du kan genstarte processen, når klinikken er oprettet eller dens oplysninger er rettet i Solteq."


def _more_than_one_clinic_found_error(provider_number=None, phone_number=None):
    """Raise BusinessError when multiple clinics match the given search values."""
    if provider_number and phone_number:
        message = (
            f"Der er fundet flere klinikker i Solteq med ydernummeret '{provider_number}' og telefonnummeret '{phone_number}'.\n"
            "Kontakt Tandplejens administration tandplejen@mbu.aarhus.dk og bed om at få undersøgt hvilken klinik der er korrekt.\n\n"
            f"{_RESTART_TEXT}"
        )
    elif provider_number:
        message = (
            f"Der er fundet flere klinikker i Solteq med ydernummeret '{provider_number}'.\n"
            "Kontakt Tandplejens administration tandplejen@mbu.aarhus.dk og bed om at få rettet til så kun en tandklinik har ydernummeret.\n\n"
            f"{_RESTART_TEXT}"
        )
    else:
        message = (
            f"Der er fundet flere klinikker i Solteq med telefonnummeret '{phone_number}'.\n"
            "Kontakt Tandplejens administration tandplejen@mbu.aarhus.dk og bed om at få rettet til så kun en tandklinik har telefonnummeret.\n\n"
            f"{_RESTART_TEXT}"
        )
    logger.error(
        "Multiple clinics found in SolteqTand database: provider=%s, phone=%s.",
        provider_number,
        phone_number,
    )
    raise BusinessError(message)


def _resolve_clinics(
    clinics: list, check_fields: list, provider_number=None, phone_number=None
) -> list:
    """Return a single-element list if all multiple matches are duplicates of the same clinic.

    Clinics are considered duplicates when all check_fields values are identical across
    every result. The fields to check depend on how the search was performed:
    - Both values provided: only streetAddress (search already ensured contractorId + phoneNumber match)
    - Only provider number: streetAddress + phoneNumber (search only guaranteed contractorId)
    - Only phone number: streetAddress + contractorId (search only guaranteed phoneNumber)
    """
    if _all_same_values(clinics, check_fields):
        logger.info(
            "Multiple clinics found but all share the same %s — treating as one clinic.",
            " and ".join(check_fields),
        )
        return [clinics[0]]
    _more_than_one_clinic_found_error(
        provider_number=provider_number, phone_number=phone_number
    )


def _try_match_by_provider_and_phone(
    database: SolteqTandDatabase, provider_number, phone_number
):
    """Match clinic by both provider number and phone number."""
    clinics_by_provider = database.get_list_of_clinics(
        filters={"contractorId": provider_number}
    )
    if not clinics_by_provider:
        return None
    matching_clinics = [
        c for c in clinics_by_provider if c.get("phoneNumber") == phone_number
    ]
    if len(matching_clinics) > 1:
        return _resolve_clinics(
            matching_clinics,
            ["streetAddress"],
            provider_number=provider_number,
            phone_number=phone_number,
        )
    elif len(matching_clinics) == 1:
        return matching_clinics
    return None


def _try_match_by_provider(database: SolteqTandDatabase, provider_number):
    """Match clinic by provider number only."""
    clinics = database.get_list_of_clinics(filters={"contractorId": provider_number})
    if len(clinics) > 1:
        return _resolve_clinics(
            clinics, ["streetAddress", "phoneNumber"], provider_number=provider_number
        )
    elif len(clinics) == 1:
        return clinics
    return None


def _try_match_by_phone(database: SolteqTandDatabase, phone_number):
    """Match clinic by phone number only."""
    clinics = database.get_list_of_clinics(filters={"phoneNumber": phone_number})
    if len(clinics) > 1:
        return _resolve_clinics(
            clinics, ["streetAddress", "contractorId"], phone_number=phone_number
        )
    elif len(clinics) == 1:
        return clinics
    return None


def match_clinic():
    """
    Clinic matching logic based on which values the user provided:
    - Both provider number AND phone number: match on both fields combined.
    - Only provider number: match by provider number; error if multiple clinics share it.
    - Only phone number: match by phone number; error if multiple clinics share it.
    - Neither provided: error.
    No fallthrough between cases — each path is independent.

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
        user_provider_number = get_context_values("clinic_provider_number")
        redirect = _PROVIDER_NUMBER_REDIRECTS.get(user_provider_number)
        if redirect:
            provider_number = redirect["provider_number"]
            phone_number = redirect["phone_number"]
        else:
            provider_number = user_provider_number
            phone_number = get_context_values("clinic_phone_number")

        logger.info(
            "Starting clinic lookup with provider_number: %s, phone_number: %s",
            provider_number,
            phone_number,
        )

        solteq_db_conn = get_rpa_constant("srvapptmtsql03_connection_string")
        database = SolteqTandDatabase(solteq_db_conn)

        if provider_number and phone_number:
            logger.info("Searching by both provider number and phone number.")
            match_result = _try_match_by_provider_and_phone(
                database, provider_number, phone_number
            )
        elif provider_number:
            logger.info("Searching by provider number only.")
            match_result = _try_match_by_provider(database, provider_number)
        elif phone_number:
            logger.info("Searching by phone number only.")
            match_result = _try_match_by_phone(database, phone_number)
        else:
            result["error"] = "Neither provider number nor phone number was provided."
            logger.error(result["error"])
            return result

        if match_result:
            result["success"] = True
            result["clinic"] = match_result[0]
            set_context_values(private_clinic_data=match_result)
            logger.info("Clinic match found.")
        else:
            if provider_number and phone_number:
                result["error"] = (
                    f"Ingen klinik fundet i Solteq med ydernummer '{provider_number}' og telefonnummer '{phone_number}'.\n"
                    "Kontakt Tandplejens administration tandplejen@mbu.aarhus.dk og bed om at få undersøgt, "
                    "om tandklinikken er oprettet i Solteq eller om den mangler korrekte oplysninger.\n\n"
                    f"{_RESTART_TEXT}"
                )
            elif provider_number:
                result["error"] = (
                    f"Ingen klinik fundet i Solteq med ydernummer '{provider_number}'.\n"
                    "Kontakt Tandplejens administration tandplejen@mbu.aarhus.dk og bed om at få undersøgt, "
                    "om tandklinikken er oprettet i Solteq eller om den mangler det rette ydernummer.\n\n"
                    f"{_RESTART_TEXT}"
                )
            else:
                result["error"] = (
                    f"Ingen klinik fundet i Solteq med telefonnummer '{phone_number}'.\n"
                    "Kontakt Tandplejens administration tandplejen@mbu.aarhus.dk og bed om at få undersøgt, "
                    "om tandklinikken er oprettet i Solteq og om den har samme telefonnummer som oplyst i EDI-portalen.\n\n"
                    f"{_RESTART_TEXT}"
                )
            logger.error(result["error"])

    except BusinessError:
        raise
    except Exception as e:
        logger.error("Error occurred during clinic matching: %s", e)
        result["error"] = f"An error occurred: {str(e)}"

    return result


def _check_clinic_in_edi_portal(
    solteq_app: SolteqTandApp, matched_clinic: dict
) -> None:
    """Open EDI portal and verify the matched clinic's contractor ID and phone number.

    Raises:
        BusinessError: If the clinic is not found or its phone number doesn't match.
    """
    solteq_app.open_edi_portal()
    try:
        contractor_id = matched_clinic.get("contractorId", "")
        phone_number = matched_clinic.get("phoneNumber", "")

        extern_clinic_data = [
            {"contractorId": contractor_id, "phoneNumber": phone_number}
        ]
        result = solteq_app.edi_portal_check_contractor_id(extern_clinic_data)

        if result is None:
            raise RuntimeError("EDI portal contractor check returned None.")

        user_provider_number = get_context_values("clinic_provider_number")
        user_phone_number = get_context_values("clinic_phone_number")
        user_info = f"Bruger oplyste: ydernummer='{user_provider_number}', telefonnummer='{user_phone_number}'"

        if result["rowCount"] == 0:
            logger.warning("Matched clinic not found in EDI portal.")
            raise BusinessError(
                f"Fandt ikke ydernummer '{contractor_id}' i EDI Portalen. "
                f"{user_info}. "
                "Kontakt Tandplejens administration, tandplejen@mbu.aarhus.dk."
            )

        if not result["isPhoneNumberMatch"]:
            logger.warning("Matched clinic phone number does not match EDI portal.")
            edi_phone_numbers = ", ".join(result.get("ediPhoneNumbers", []))
            raise BusinessError(
                f"Valgt klinik med ydernummer '{contractor_id}' står i Solteq med "
                f"telefonnummer '{phone_number}', hvilket ikke matcher telefonnummer "
                f"i EDI Portalen som er '{edi_phone_numbers}'. "
                "Kontakt Tandplejens administration, tandplejen@mbu.aarhus.dk."
            )

        logger.info("Matched clinic verified in EDI portal.")
    finally:
        solteq_app.close_edi_portal()


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
            logger.error(
                "Contractor not found in SolteqTand database. Error: %s",
                match_result["error"],
            )
            raise BusinessError(match_result["error"])

        # Get matched clinic data
        matched_clinic = match_result["clinic"]
        logger.info("Matched clinic data: %s", matched_clinic)

        # Get current contractor data from patient
        solteq_app = get_app()
        if solteq_app is None:
            raise ValueError("Could not get application instance.")

        # Verify the matched clinic exists in the EDI portal and its phone number matches
        _check_clinic_in_edi_portal(solteq_app, matched_clinic)

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
