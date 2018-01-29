import logging
import logging.handlers
from logging import DEBUG, INFO, WARNING, ERROR
from os import path, mkdir
from smb import PROJECTROOT
LOG_FILE = 'smb_cli.log'


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


def log(logger, message, level=DEBUG, color=None, raw=False):
    from smb.cli.lib import print_green, print_yellow, print_red
    CONSOLE_FORMAT = '{}: {}'.format(logging.getLevelName(level), message)
    if raw:
        print_format = message
    else:
        print_format = CONSOLE_FORMAT
    logger.log(level, message)
    if color == "green":
        print_green(print_format)
    elif color == "yellow":
        print_yellow(print_format)
    elif color == "red":
        print_red(print_format)
    elif level > DEBUG:
        print print_format


def log_n_exit(logger, message):
    log(logger, message, level=ERROR, color="red")
    exit()
