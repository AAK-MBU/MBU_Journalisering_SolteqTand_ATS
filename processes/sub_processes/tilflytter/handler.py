"""Handler for the 'Tilflytter' process."""

import logging

from processes.shared.utils.clean_up import release_keys
from processes.sub_processes.tilflytter.set_context import set_context_vars

from . import config

logger = logging.getLogger(__name__)


def process_tilflytter(item_data: dict, item_reference: str, item_id: str):
    """Function to handle the 'Tilflytter' process item."""
    logger.info(
        "Processing 'Tilflytter' item with reference: %s and id: %s",
        item_reference,
        item_id,
    )

    release_keys()

    # Set context variables for further processing
    set_context_vars(item_data, item_reference, item_id)
