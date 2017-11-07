import sys
import infinisdk
from smb.cli import lib
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


def map_vol_to_cluster(volume):
    config = defaults_get(silent=True)
    ibox = lib.connect()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    try:
        mapping = cluster.map_volume(volume)
    except:
        error = sys.exc_info()[1]
        lib.print_red("Couldn't map vol {} to cluster {}! {!r}".format(volume.get_name(),
                                                                       cluster.get_name(), str(error.message)))
        exit()
    print "Volume {} was just mapped to {}".format(volume.get_name(), cluster.get_name())


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

def _validate_vol(ibox_sdk, vol_name):
    try:
        return ibox_sdk.volumes.choose(name=vol_name)
    except ObjectNotFound:
        lib.print_yellow("Volume {} couldn't be found on {}".format(vol_name, ibox_sdk.get_name()))
        exit()

def vol_create(volume_name, pool_name, size_str):
    ibox = lib.connect()
    size = _validate_size(size_str)
    pool = _validate_pool(pool_name, ibox, size)
    try:
        return ibox.volumes.create(name=volume_name, pool=pool, size=size, provtype='THIN')
    except:
        error = sys.exc_info()[1]
        lib.print_red("Volume {} couldn't be created. {!r}".format(volume_name, str(error.message)))
        exit()

