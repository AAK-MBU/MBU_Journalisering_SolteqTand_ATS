"""Handles downloading documents from OS2 Forms."""

import logging
import os

from mbu_dev_shared_components.os2forms.documents import download_file_bytes

import helpers.config as config
from helpers.context_handler import get_context_values, set_context_values
from helpers.credential_constants import get_rpa_credentials

logger = logging.getLogger(__name__)


def get_os2forms_document():
    """Downloads the document from OS2 Forms and saves it to the specified path."""

    def _ensure_file_exists(file_path):
        """Checks if the specified file exists.

        Args:
            file_path (str): The full path of the file to check.

        Raises:
            OSError: If the file does not exist.
        """
        if not os.path.exists(file_path):
            raise OSError("File does not exists")

        logger.info('File "%s" exists.', file_path)

    def _ensure_folder_exists(full_path):
        """Ensures that the folder for the given path exists. Creates the folder if it doesn't exist.

        Args:
            full_path (str): The full path where the folder should be created.

        Raises:
            OSError: If there is an error creating the folder.
        """
        folder_path = os.path.dirname(full_path)

        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                logger.info('Folder "%s" has been created.', folder_path)
            except OSError as e:
                logger.error('Failed to create folder "%s". Reason: %s', folder_path, e)
                raise
        else:
            logger.info('Folder "%s" already exists.', folder_path)

    def _delete_file(full_path: str):
        """Deletes the specified file if it exists.

        Args:
            full_path (str): The full path of the file to be deleted.

        Raises:
            OSError: If an error occurs while trying to delete the file.
        """
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
                logger.info('File "%s" has been deleted.', full_path)
            except OSError as e:
                logger.error('Failed to delete file "%s". Reason: %s', full_path, e)
                raise
        else:
            logger.warning(
                'File "%s" does not exist or is not a valid file.', full_path
            )

    try:
        logger.info("Starting document download from OS2 Forms.")
        api_key = get_rpa_credentials("os2_api")
        full_path = os.path.join(config.DOCUMENT_PATH, config.DOCUMENT_FILE_NAME)

        _ensure_folder_exists(full_path)
        _delete_file(full_path)

        file_bytes = download_file_bytes(
            os2_api_key=api_key["decrypted_password"],
            url=get_context_values("url"),
        )

        with open(full_path, "wb") as file:
            file.write(file_bytes)

        logger.info("File created: %s", full_path)

        _ensure_file_exists(full_path)

        set_context_values(os2forms_document_path=full_path)
        logger.info("Document download from OS2 Forms completed successfully.")
    except OSError as e:
        logger.error("File system error when attempting to download the receipt. %s", e)
        raise
    except Exception as e:
        logger.error("An unexpected error occurred during receipt download: %s", e)
        raise

