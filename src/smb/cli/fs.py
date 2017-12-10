import sys
from capacity import *
from smb.cli import lib
from smb.cli.config import config_get

class Fs(object):
    def __init__(self, infinibox_vol_name, lun_number, winid, mountpoint, fs_size, used_size, num_snaps, num_shares):
        self.infinibox_vol_name = infinibox_vol_name
        self.lun_number = lun_number
        self.winid = int(winid)
        self.mountpoint = mountpoint.strip()
        self.fs_size = fs_size
        self.used_size = used_size
        self.num_snaps = num_snaps
        self.num_shares = num_shares

    def get_mountpoint(self):
        return self.mountpoint

    def get_winid(self):
        return self.winid

    def get_lun_number(self):
        return self.lun_number

    def get_infinibox_vol_name(self):
        return self.infinibox_vol_name

    def get_fs_size(self):
        return self.fs_size

    def get_used_size(self):
        return self.used_size

    def get_num_snaps(self):
        return self.num_snaps

    def get_num_shares(self):
        return self.num_shares


def instance_fs(volume):
    ''' recives an infinisdk volume object and create a usable fs instance
    '''
    # TODO: Get number of shares
    from os import path
    ibox = volume.get_system()
    config = config_get(silent=True)
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    lun_number = cluster.get_lun(volume).get_lun()
    mountpoint = path.realpath(path.join(config['MountRoot'], volume.get_name()))
    win_id = _get_winid_by_serial(volume.get_serial())
    num_snaps = len(volume.get_snapshots().to_list())
    return Fs(volume.get_name(), lun_number, win_id, mountpoint, volume.get_size(), volume.get_used_size(),
              num_snaps, 0)


def _get_winid_by_serial(luid):
    '''logical unit id (luid) is also the infinibox volume serial
    '''
    from infi.execute import execute
    cmd_output = execute(['powershell', '-c', 'Get-Disk', '-SerialNumber',
                          str(luid), '|', 'Select-Object -ExpandProperty number']).get_stdout()
    return cmd_output


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
    vol_to_cluster_script = path.realpath(path.join(PROJECTROOT, pardir, 'src', 'prep_and_add_vol_to_cluster.ps1'))
    cmd = execute_assert_success(['powershell', '.', '"' + vol_to_cluster_script.replace('\\', '/') +
                                 '"' + " -DiskNumber {} -MountPath {}".format(fs.get_winid(), fs.get_mountpoint())])
    import pdb ; pdb.set_trace()


def _run_attach_vol_to_cluster_scirpt(fs):
    from infi.execute import execute_assert_success
    from smb import PROJECTROOT
    from os import path, pardir
    attach_vol_to_cluster_script = path.realpath(path.join(PROJECTROOT, pardir, 'src', 'add_vol_to_cluster.ps1'))
    cmd = execute_assert_success(['powershell', '.', '"' + attach_vol_to_cluster_script.replace('\\', '/') +
                                 '"' + " -DiskNumber {}".format(fs.get_winid())])


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


def unmap_vol_from_cluster_windows(volume_name):
    pass

def unmap_vol_from_cluster_infinibox(volume_name):
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
    print "Volume {} is now mapped to {}".format(volume.get_name(), cluster.get_name())


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
        print "Creating volume {} in {} Pool".format(volume_name, pool_name)
        return ibox.volumes.create(name=volume_name, pool=pool, size=size, provtype='THIN')
    except:
        error = sys.exc_info()[1]
        lib.print_red("Volume {} couldn't be created. {!r}".format(volume_name, str(error.message)))
        exit()


def clean_fs(fs):
    import os
    unmap_vol_from_cluster_infinibox(fs.get_infinibox_vol_name())
    if _mountpoint_exist(fs.get_mountpoint()):
        os.rmdir(fs.get_mountpoint())
        lib.print_yellow("Dirctory {} was deleted".format(fs.get_mountpoint()))
    delete_volume_on_infinibox(fs.get_infinibox_vol_name())

def _get_mapped_vols():
    config = config_get(silent=True)
    ibox = lib.connect()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    mapped_vols  = cluster.get_lun_to_volume_dict()
    return [ volume for volume in mapped_vols.itervalues()]

def _print_format(val, val_type):
    def _trim(val):
        # only for name and mount
        return val[0:15] + "..."

    def _fill(val, val_type):
        if val_type == "name":
            return val.ljust(18)
        if val_type == "mount":
            return val.ljust(18)
        if val_type in [ "size", "used_size"]:
            return val.ljust(12)
        if val_type in [ "snaps", "shares"]:
            return val.ljust(7)


    def _trim_or_fill(val, val_type):
        if val_type in ["name", "mount"]:
            if len(val) == 18:
                return (val)
            if len(val) > 18:
                return _trim(val)
            return _fill(val, val_type)
        if val_type in [ "size", "used_size", "snaps", "shares" ]:
            return _fill(val, val_type)

    return _trim_or_fill(val, val_type)

def print_fs_query(mapped_vols, print_units):
    header = 'Name               Mount              Size         Used Size    Snaps   Shares'
    print header
    for volume in mapped_vols:
        fs = instance_fs(volume)
        if print_units:
            fs_size = str((fs.get_fs_size() / print_units)) + str(print_units)[2:]
            used_size = str((fs.get_used_size() / print_units)) + str(print_units)[2:]
        else:
            fs_size = str(fs.get_fs_size())
            used_size = str(fs.get_used_size())
        line = [_print_format(fs.get_infinibox_vol_name(), "name"),
                _print_format(fs.get_mountpoint(), "mount"),
                _print_format(fs_size, "size",),
                _print_format(used_size, "used_size"),
                _print_format(str(fs.get_num_snaps()),"snaps"),
                _print_format(str(fs.get_num_shares()), "shares")]
        print " ".join(line)

def fs_query(units):
    if units:
        units = _validate_size(units)
    print_fs_query(_get_mapped_vols(), units)



def fs_attach(volume, force=False):
    if force and lib.is_volume_mapped_to_cluster(volume):
        pass
    else:
        map_vol_to_cluster(volume)
    lib.exit_if_vol_not_mapped(volume)
    existing_fs = instance_fs(volume)
    _mountpoint_exist(new_fs.get_mountpoint(), create=True)
    _run_attach_vol_to_cluster_scirpt(existing_fs)


def fs_create(volume):
    map_vol_to_cluster(volume)
    lib.exit_if_vol_not_mapped(volume)
    new_fs = instance_fs(volume)
    try:
        _mountpoint_exist(new_fs.get_mountpoint(), create=True)
        _run_vol_to_cluster_scirpt(new_fs)
    except:
        e = sys.exc_info
        lib.print_red("Something went wrong. Rolling back operations...")
        clean_fs(new_fs)
