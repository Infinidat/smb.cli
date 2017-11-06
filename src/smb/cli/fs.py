import infinisdk
from smb.cli import lib
from infi.credentials_store import CLICredentialsStore
from smb.cli.defaults import defaults_get


class Fs(object):
    def __init__(self, vol_infinibox_name, lun_number, win_id, mountpoint):
        self.vol_infinibox_name = vol_infinibox_name
        self.lun_number = lun_number
        self.win_id = win_id
        self.mountpoint = mountpoint

    def get_mountpoint(self):
        return self.get_mountpoint

    def get_win_id(self):
        return self.get_win_id

    def get_lun_number(self):
        return self.lun_number

    def get_vol_infinibox_name(self):
        return self.get_vol_infinibox_name


class SMBCrdentialsStore(CLICredentialsStore):
    def _get_file_folder(self):
        return ".smb.credentials_store"

    def authenticate(self, key, credentilas):
        return True

    def ask_credentials_prompt(self, key):
        print 'Connecting to InfiniBox ' + str(key)


def initiate_store(store_name):
    crdentials_store = SMBCrdentialsStore("all_iboxes")
    return crdentials_store.get_credentials(store_name)


def connect():
    '''tries to connect using credintal store'''
    config = defaults_get(silent=True)
    store = initiate_store(config['IboxAddress'])
    ibox = infinisdk.InfiniBox(str(config['IboxAddress']),
                               auth=(store.get_username(), store.get_password()))
    response = ibox.login()
    if response.status_code == 200:
        return ibox
    else:
        print "Couldn't connect with current credentilas"
        exit()

def map_vol_to_cluster(volume):
    ibox = connect()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])


def _validate_mount(mount):
    from os.path import isdir
    if isdir(mount):
        return
    else:
        print "asd"

def _validate_size(size_str):
    import capacity
    try:
        size = capacity.from_string(size_str)
    except:
        lib.print_yellow("{} is an invalid capacity ! Please try one of the following:\n".format(size_str) +
                         "<number> KB, KiB, MB, MiB, GB, GiB, TB, TiB... ")
        exit()
    return size


def _validate_pool(pool_name, ibox_sdk, size):
    from infinisdk.core.type_binder import ObjectNotFound
    from capacity import GiB
    spare_size = 1 * GiB
    try:
        pool = ibox_sdk.pools.choose(name=pool_name)
    except ObjectNotFound:
        lib.print_yellow("Pool {} couldn't be found on {}".format(pool_name, ibox_sdk.get_name()))
        exit()
    new_free = pool.get_free_virtual_capacity() - size - spare_size
    if int(new_free <= 0):
        lib.print_red("Pool {} doesn't have enough space to provision {!r}".format(pool_name, size))
        exit()
    return pool


def vol_create(volume_name, pool_name, size_str):
    import sys
    ibox = connect()
    size = _validate_size(size_str)
    pool = _validate_pool(pool_name, ibox, size)
    try:
        ibox.volumes.create(name=volume_name, pool=pool, size=size, provtype='THIN')
    except:
        error = sys.exc_info()[1]
        lib.print_red("Volume {} couldn't be created. {!r}".format(volume_name, str(error.message)))
        exit()
