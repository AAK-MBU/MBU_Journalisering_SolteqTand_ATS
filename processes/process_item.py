"""Module to handle item processing"""

import logging

from mbu_rpa_core.exceptions import BusinessError, ProcessError

from helpers.config import SUBPROCESS_CHOICES
from processes.application_handler import close
from processes.shared.utils.clean_up import clean_up
from processes.sub_processes.udskrivning_22_aar.handler import (
    process_udskrivning_22_aar,
)

logger = logging.getLogger(__name__)


def process_item(item_data: dict, item_reference: str, item_id: str, subprocess: str):
    """Function to handle item processing"""
    try:
        if subprocess not in SUBPROCESS_CHOICES:
            raise ValueError(
                f"Unknown subprocess: '{subprocess}'. Must be one of {SUBPROCESS_CHOICES}"
            )

        if subprocess == "udskrivning22ar":
            process_udskrivning_22_aar(item_data, item_reference, item_id)
        elif subprocess == "tilflytter":
            process_tilflytter(item_data, item_reference, item_id)

    except BusinessError as be:
        logger.error("Business error occurred: %s", be)
        update_process_status("Failed")
        raise be
    except Exception as e:
        logger.error("%s", e)
        update_process_status("Failed")
        raise ProcessError("A process error occurred.") from e
    finally:
        clean_up()
        close()
