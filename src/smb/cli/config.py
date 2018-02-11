from smb import PROJECTROOT
from smb.cli.smb_log import get_logger, log, log_n_exit
from logging import DEBUG, INFO, WARNING, ERROR
from os import path
logger = get_logger()
INFINIDAT_CONFIG_FILE_NAME = 'infinidat_config'
conf_dir = path.join(PROJECTROOT, 'config')
conf_file = path.join(conf_dir, INFINIDAT_CONFIG_FILE_NAME)


def powershell_config_to_dict(filename):
    '''receive filename containing powershell config return dict object with this config '''
    config = {}
    with open(filename, 'r') as file:
        file_content = file.readlines()
        for line in file_content[1:-1]:
            key, val = line.strip().split(' = ')
            config[key] = val.replace('"', '')
        return config


def change_powershell_config(key, value):
    import fileinput
    if not read_config(conf_file):
        log_n_exit(logger, "Problem reading config file")
    for line in fileinput.input(conf_file, inplace=True):
        if "=" not in line:
            print line,
            continue
        line_key, line_val = line.split("=")
        if line_key.strip() == key:
            print '    {} = "{}"'.format(key, value)
        else:
            print line,
    fileinput.close()


def read_config(filename):
    from smb.cli.lib import print_red
    if path.exists(filename):
        config = powershell_config_to_dict(filename)
        if config is None:
            log(logger, "config file {} is empty!".format(filename, level=ERROR, color="yellow"))
            return
        return config
    else:
        log(logger, "Couldn't find config file at {}".format(filename, level=ERROR, color="red"))


def config_get(silent=False):
    config = read_config(conf_file)
    if silent or not config:
        return config
    msg = """
Current Config:
    default PoolName:  {pool}
""".format(pool=config['PoolName'])
    log(logger, msg, level=INFO, raw=True)
    return config


def config_set(key, value, sdk):
    from fs import _validate_pool_name
    if key.lower() != 'poolname':
        log_n_exit(logger, "Currently only PoolName is supported for user config change")
    _validate_pool_name(value, sdk.get_ibox())
    log(logger, "Changing {} = {}".format(key, value), level=INFO)
    change_powershell_config(key, value)
