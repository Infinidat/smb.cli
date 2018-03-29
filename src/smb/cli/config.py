from smb import PROJECTROOT
from smb.cli.smb_log import get_logger, log, log_n_raise, SmbCliExited
from logging import INFO, WARNING
from os import path, mkdir
INFINIDAT_CONFIG_FILE_NAME = 'infinidat_config'
conf_dir = path.join(PROJECTROOT, 'config')
conf_file = path.join(conf_dir, INFINIDAT_CONFIG_FILE_NAME)
infinihost_bin = ('C:/Program Files/Infinidat/Host Power Tools/bin/infinihost.exe')

logger = get_logger()

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
    config = read_config(conf_file)
    if not config:
        log_n_raise(logger, "Problem reading config file")
    log(logger, "Changing {} = {}".format(key, value), level=INFO)
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


def validate_key_val(key, val):
    import re
    MAX_ROLE_NAME = 15
    MAX_POOL_NAME = 32
    key_lower = key.lower()
    regular_chars = re.compile('[a-zA-Z0-9\-\_]+$')
    dns_name = re.compile('([a-zA-Z0-9\-\_]+\.)+([a-zA-Z0-9\-\_]+$)')
    ip_address = re.compile('((25[0-5]|2[0-4][0-9]|[1][0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|[1][0-9][0-9]|[1-9]?[0-9])')
    ms_drive_letter = re.compile(r'^[a-zA-Z]{1}:{1}\\{1}$')
    if key_lower in [ 'fsrolename', 'poolname', 'cluster']:
        if not re.match(regular_chars, val):
            log_n_raise(logger, "Only non-spacial Characters are Supported for {}".format(key))
    if key_lower in ['fsrolename', 'cluster']:
        if len(val) > MAX_ROLE_NAME:
            log_n_raise(logger,"{} Value is to long. Max allowed Characters are {}".format(key, MAX_ROLE_NAME))
        # add verify that the cluster and cluster role is the same
    if key_lower == 'poolname' and len(val) > MAX_POOL_NAME:
        log_n_raise(logger, "{} Value is to long. Max allowed Characters are {}".format(key, MAX_POOL_NAME))
    if key_lower in ['mountroot', 'tempdriveletter']:
        if not re.match(ms_drive_letter, val):
            log_n_raise(logger, "{} Value is Invalid. value should be Microsoft drive letter. e.g. D:\ ".format(val))
        val = val.upper()
    if key_lower == 'iboxaddress':
        if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', val):
            if not re.match(ip_address, val):
                log_n_raise(logger, "{} is Invalid IP address".format(val))
        else:
            if not re.match(dns_name, val):
                log_n_raise(logger, "{} is Invalid InfiniBox DNS address".format(val))
    return key, val

def validate_config(config):
    import re
    default_val = re.compile('<.+>$')
    keys = ['FSRoleName', 'PoolName', 'Cluster', 'MountRoot', 'TempDriveLetter', 'IboxAddress']
    for key in keys:
        if not config.has_key(key):
            log_n_raise(logger, "Not all parameters are in the config file. Config file {} is Invalid".format(conf_file))
    for key, val in config.iteritems():
        if re.search(default_val, val):
            log_n_raise(logger, "Some configuration values are missing.\ne.g. {} = {}".format(key, val))


def read_config(filename):
    if path.exists(filename):
        config = powershell_config_to_dict(filename)
        if config is None:
            log(logger, "config file {} was empty!".format(filename, level=WARNING, color="yellow"))
            generate_config()
        return config
    else:
        log(logger, "Config file did not exist on {}. Generating it".format(filename), level=INFO)
        generate_config()

def generate_config():
    default_conf_content = '''@{
    TempDriveLetter = "Z:\"
    MountRoot = "G:\"
    PoolName = "<infinibox_pool>"
    Cluster = "<infinibox_cluster>"
    IboxAddress = "<infinibox_address>"
    FSRoleName = "<ms_role_name>"
}
'''
    with open(conf_file, 'w') as fd:
        fd.write(default_conf_content)
    log(logger, "Vanilla config file was generated at {}".format(conf_file), level=INFO, color="green")
    raise SmbCliExited()

def config_get(silent=False, skip_validation=False):
    config = read_config(conf_file)
    if silent or not config:
        return config
    log(logger, "Current Config:", level=INFO, raw=True)
    for key, val in config.items():
        message = "    {}: {}".format(key, val)
        log(logger, message, level=INFO, raw=True)
    if not skip_validation:
        validate_config(config)
    if not path.exists(infinihost_bin):
        log_n_raise(logger, 'smb.cli depends on "Host Power Tools" and can NOT find it!')
    return config


def config_set(key, value):
    from fs import _validate_pool_name
    key, value = validate_key_val(key, value)
    change_powershell_config(key, value)


if not path.exists(conf_dir):
    mkdir(conf_dir)
    generate_config()
