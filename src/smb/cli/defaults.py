CUSTOMER_CONFIG_FILE = 'customer_config'
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
            config[key] = val.replace('"','')
        return config


def read_config(filename):
    from os import path, pardir
    from smb import PROJECTROOT
    try:
        conf_dir = path.join(PROJECTROOT, pardir, 'Config')
        if path.exists(conf_dir):
            config = powershell_config_to_dict(path.join(conf_dir, filename))
            return config
    finally:
        return


def defaults_get():
    config = read_config(INFINIDAT_CONFIG_FILE)
    print \
    """
    defaults:
        default mountpoint: {mount}
        default pool:       {pool}
    """.format(mount=config.MountRoot, pool=config.PoolName)


def defaults_set():
    print "asd"






