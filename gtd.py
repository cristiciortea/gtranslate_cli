import logging

LOGGER = logging.getLogger(__name__)


def start_trans(file_path, language):
    LOGGER.debug(f'File path used is: {file_path}')
    LOGGER.debug(f'Target language is: {language}')
