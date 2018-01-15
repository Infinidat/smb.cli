from smb import PROJECTROOT
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
        exit()
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
                print_red("config file {} is empty!".format(path.abspath(conf_dir)))
                return
            return config
        else:
            print_red("Couldn't find config file at {}".format(path.abspath(conf_dir)))
    except:
        return


def config_get(silent=False):
    config = read_config(INFINIDAT_CONFIG_FILE)
    if silent or not config:
        return config
    print """
config:
    default MountRoot: {mount}
    default PoolName:  {pool}
""".format(mount=config['MountRoot'], pool=config['PoolName'])
    return config


def config_set(key, value):
    print "Changing {} = {}".format(key, value)
    change_powershell_config(key, value)
