import sys
from smb.cli import lib
from smb.cli.config import config_get

class Fs(object):
    def __init__(self, infinibox_vol_name, lun_number, winid, mountpoint):
        self.infinibox_vol_name = infinibox_vol_name
        self.lun_number = lun_number
        self.winid = winid
        self.mountpoint = mountpoint

    def get_mountpoint(self):
        return self.mountpoint

    def get_winid(self):
        return self.winid

    def get_lun_number(self):
        return self.lun_number

    def get_infinibox_vol_name(self):
        return self.infinibox_vol_name


def _get_winid_by_serial(luid):
    '''logical unit id (luid) is also the infinibox volume serial
    '''
    from infi.execute import execute
    cmd_output = execute(['powershell', '-c', 'Get-Disk', '-SerialNumber', str(luid)]).get_stdout()
    for line in cmd_output.splitlines():
        if 'InfiniBox' in line:
            return line.split()[0]


def _mountpoint_exist(mountpoint, create=False):
    '''Check if mount point exist or not, if create=True and mountpoint doesn't exist, create it
    '''
    from os import path, mkdir
    if not create:
        return path.exists(mountpoint)
    print "Createing mount path {}".format(mountpoint)
    mkdir(mountpoint)
    return True


def _run_vol_to_cluster_scirpt(fs):
    from infi.execute import execute_assert_success
    from smb import PROJECTROOT
    from os import path, pardir
    vol_to_cluster_script = path.realpath(path.join(PROJECTROOT, pardir, 'prep_and_join_vol_to_cluster.ps1'))
    cmd = execute_assert_success(['powershell', '.', '"' + vol_to_cluster_script.replace('\\', '/') +
                                 '"' + "-DiskNumber {} -MountPath {}".format(fs.get_winid(), fs.get_mountpoint())])
    print cmd.get_stdout()
    print cmd.get_stderr()

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
    from infinisdk.core.type_binder import ObjectNotFound
    try:
        return ibox_sdk.volumes.choose(name=vol_name)
    except ObjectNotFound:
        lib.print_yellow("Volume {} couldn't be found on {}".format(vol_name, ibox_sdk.get_name()))
        exit()


def instance_fs(volume):
    ''' recives an infinisdk volume object and create a usable fs instance
    '''
    from os import path
    ibox = volume.get_system()
    config = config_get(silent=True)
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    lun_number = cluster.get_lun(volume).get_lun()
    mountpoint = path.join(config['MountRoot'], volume.get_name())
    win_id = _get_winid_by_serial(volume.get_serial())
    return Fs(volume.get_name(), lun_number, win_id, mountpoint)


def unmap_vol_from_cluster(volume_name):
    config = config_get(silent=True)
    ibox = lib.connect()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    volume = ibox.volumes.choose(name=volume_name)
    cluster.unmap_volume(volume)
    lib.print_yellow("Volume {} was just unmapped".format(volume.get_name()))


def map_vol_to_cluster(volume):
    config = config_get(silent=True)
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


def delete_volume_on_infinibox(volume_name):
    ibox = lib.connect()
    volume = ibox.volumes.choose(name=volume_name)
    volume.delete()
    lib.print_yellow("Volume {} was deleted".format(volume_name))


def create_volume_on_infinibox(volume_name, pool_name, size_str):
    ibox = lib.connect()
    size = _validate_size(size_str)
    pool = _validate_pool(pool_name, ibox, size)
    try:
        print "Creating volume {} in {}".format(volume_name, pool_name)
        return ibox.volumes.create(name=volume_name, pool=pool, size=size, provtype='THIN')
    except:
        error = sys.exc_info()[1]
        lib.print_red("Volume {} couldn't be created. {!r}".format(volume_name, str(error.message)))
        exit()


def clean_fs(fs):
    import os
    unmap_vol_from_cluster(fs.get_infinibox_vol_name())
    if _mountpoint_exist(fs.get_mountpoint()):
        os.rmdir(fs.get_mountpoint())
        lib.print_yellow("Dirctory {} was deleted".format(fs.get_mountpoint()))
    delete_volume_on_infinibox(fs.get_infinibox_vol_name())


def fs_create(volume):
    map_vol_to_cluster(volume)
    lib.exit_if_vol_not_mapped(volume)
    new_fs = instance_fs(volume)
    try:
        _mountpoint_exist(new_fs.get_mountpoint(), create=True)
        _run_vol_to_cluster_scirpt(new_fs)
    except:
        lib.print_red("Something went wrong. Rolling back operations...")
        clean_fs(new_fs)
