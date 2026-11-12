"""Utility functions for RPA operations"""

from typing import Any

import pyodbc
from mbu_dev_shared_components.database.connection import RPAConnection


def get_rpa_constant(constant_name: str) -> str:
    """
    Get a constant value from RPA connection

    Args:
        constant_name (str): Name of the constant to retrieve

    Returns:
        str: The constant value, empty string if not found
    """
    with RPAConnection(db_env="PROD", commit=False) as rpa_conn:
        return rpa_conn.get_constant(constant_name).get("value", "")


def get_rpa_credentials(credential_name: str) -> dict[str, Any]:
    """
    Get credentials from RPA connection

    Args:
        credential_name (str): Name of the credential to retrieve

    Returns:
        dict[str, Any]: Dictionary containing username, password,
                       and other credential data
    """
    with RPAConnection(db_env="PROD", commit=False) as rpa_conn:
        return rpa_conn.get_credential(credential_name)


_PROVIDER_NUMBER_REDIRECT_QUERY = """
    SELECT [target_provider_number], [target_phone_number]
    FROM [RPA].[rpa].[ProviderNumberRedirects]
    WHERE [source_provider_number] = ?
      AND [scope] = N'SOLTEQ'
      AND [is_active] = 1
"""


def get_provider_number_redirect(provider_number: str | None) -> dict | None:
    """
    Look up an active SOLTEQ-scoped provider number (ydernummer) redirect in
    the RPA database.

    Some contractors don't exist in Solteq under their real provider number,
    so they are redirected to a stand-in clinic that does. Redirects are
    maintained in [RPA].[rpa].[ProviderNumberRedirects] (managed via
    automation-hub). At most one active redirect exists per source number
    and scope.

    Only scope 'SOLTEQ' applies here. 'EDI' rows (clinics that exist in
    Solteq but are reached via another recipient in the EDI portal) are
    handled by downstream processes and must NOT affect the Solteq lookup.
    A SOLTEQ redirect implicitly covers EDI too, since the stand-in clinic
    is what gets set on the patient.

    Args:
        provider_number (str | None): The provider number entered by the citizen.

    Returns:
        dict | None: {"provider_number": str, "phone_number": str | None} for the
        stand-in clinic, or None if no active redirect exists.
        phone_number None means: keep the citizen's phone number.
    """
    provider_number = (provider_number or "").strip()
    if not provider_number:
        return None

    with RPAConnection(db_env="PROD", commit=False) as rpa_conn:
        rows = rpa_conn.execute_query(
            _PROVIDER_NUMBER_REDIRECT_QUERY, [provider_number], return_dict=True
        )

    if not rows:
        return None

    row = rows[0]
    return {
        "provider_number": row["target_provider_number"],
        "phone_number": row["target_phone_number"],
    }


_EDI_REDIRECT_QUERY = """
    SELECT [target_provider_number], [target_phone_number]
    FROM [RPA].[rpa].[ProviderNumberRedirects]
    WHERE [source_provider_number] = ?
      AND [scope] = N'EDI'
      AND [is_active] = 1
"""


def get_edi_redirect(contractor_id: str | None) -> dict | None:
    """
    Look up an active EDI-scoped redirect in the RPA database.

    Some clinics exist in Solteq under their own provider number, but are
    reached through a shared recipient in the EDI portal (e.g. Hasle Torv and
    Brobjergparken -> 485055). The clinic set on the patient in Solteq stays
    the real one; only EDI portal lookups use the redirected recipient. The
    downstream EDI sending processes apply the same redirect.

    Args:
        contractor_id (str | None): The matched clinic's provider number in Solteq
            (i.e. after any SOLTEQ redirect).

    Returns:
        dict | None: {"provider_number": str, "phone_number": str | None} for the
        EDI recipient, or None if no active EDI redirect exists.
        phone_number None means: keep the clinic's own phone number.
    """
    contractor_id = (contractor_id or "").strip()
    if not contractor_id:
        return None

    with RPAConnection(db_env="PROD", commit=False) as rpa_conn:
        rows = rpa_conn.execute_query(
            _EDI_REDIRECT_QUERY, [contractor_id], return_dict=True
        )

    if not rows:
        return None

    row = rows[0]
    return {
        "provider_number": row["target_provider_number"],
        "phone_number": row["target_phone_number"],
    }


def get_exceptions(db_connection: str) -> list[dict]:
    """Get exceptions from the database."""
    conn = pyodbc.connect(db_connection)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                [exception_code]
                ,[message_text]
            FROM
                [RPA].[rpa].[BusinessExceptionMessages]
            """
        )
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row, strict=True)) for row in rows]
        return result
    finally:
        cursor.close()
