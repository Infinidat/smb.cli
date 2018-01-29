from smb import PROJECTROOT
from smb.cli.smb_log import get_logger, log, log_n_exit
from logging import DEBUG, INFO, WARNING, ERROR
logger = get_logger()
INFINIDAT_CONFIG_FILE = 'infinidat_config'


def powershell_config_to_dict(filename):
    '''receive filename containing powershell config return dict object with this config '''
    config = {}
    with open(filename, 'r') as file:
        file_content = file.readlines()
        file_content.pop(0)
        file_content.pop(-1)
        for line in file_content:
            key, val = line.strip().split(' = ')
            config[key] = val.replace('"', '')
        return config


def change_powershell_config(key, value):
    import fileinput
    from os import path, pardir
    conf_dir = path.join(PROJECTROOT, pardir, 'Config')
    file = path.join(conf_dir, INFINIDAT_CONFIG_FILE)
    if not read_config(file):
        log_n_exit(logger, "Problem reading config file")
    for line in fileinput.input(file, inplace=True):
        if "=" not in line:
            print line,
            continue
        line_key, line_val = line.split("=")
        if line_key.strip() == key:
            print "    {} = {}".format(key, value)
        else:
            print line,
    fileinput.close()


def read_config(filename):
    from smb.cli.lib import print_red
    from os import path, pardir
    try:
        conf_dir = path.join(PROJECTROOT, pardir, 'Config')
        if path.exists(conf_dir):
            config = powershell_config_to_dict(path.join(conf_dir, filename))
            if config is None:
                log(logger, "config file {} is empty!".format(path.abspath(conf_dir)), level=ERROR, color="yellow")
                return
            return config
        else:
            log(logger, "Couldn't find config file at {}".format(path.abspath(conf_dir)), level=ERROR, color="red")
    except:
        return


def config_get(silent=False):
    config = read_config(INFINIDAT_CONFIG_FILE)
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
