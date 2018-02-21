import logging
import logging.handlers
from logging import DEBUG, INFO, WARNING, ERROR
from os import path, mkdir
from smb import PROJECTROOT
LOG_FILE = 'smb_cli.log'

class SmbCliExited(Exception):
    pass

def get_logger():
    LOG_FILE_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
    log_formatter = logging.Formatter(LOG_FILE_FORMAT)
    log_folder = path.join(PROJECTROOT, 'Logs')
    if not path.exists(log_folder):
        mkdir(log_folder)
    logger = logging.getLogger('smb.cli')
    file = logging.handlers.RotatingFileHandler(path.join( log_folder, LOG_FILE ),
                                                maxBytes=(3*1024*1024), backupCount=5)
    file.setLevel(DEBUG)
    file.setFormatter(log_formatter)
    if not logger.handlers:
        logger.addHandler(file)
    logger.setLevel(DEBUG)
    return logger


def log(logger, message, level=DEBUG, color=None, raw=False, disable_print=False):
    from smb.cli.lib import print_green, print_yellow, print_red
    logger.log(level, message)
    if disable_print or level == DEBUG:
        return

    CONSOLE_FORMAT = '{}: {}'.format(logging.getLevelName(level), message)
    if raw:
        print_format = message
    else:
        print_format = CONSOLE_FORMAT
    if color == "green":
        print_green(print_format)
    elif color == "yellow":
        print_yellow(print_format)
    elif color == "red":
        print_red(print_format)
    else:
        print print_format


def log_n_raise(logger, message, level=ERROR, disable_print=False):
    if level == ERROR:
        log(logger, message, level=ERROR, color="red", disable_print=disable_print)
    if level == WARNING:
        log(logger, message, level=WARNING, color="yellow", disable_print=disable_print)
    raise SmbCliExited()
