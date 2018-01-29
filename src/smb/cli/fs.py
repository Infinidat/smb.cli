import sys
from capacity import *
from os import path, mkdir
from smb.cli import lib, ps_cmd
from infi.execute import execute
from smb.cli.config import config_get
from smb.cli.smb_log import get_logger, log, log_n_exit
from logging import DEBUG, INFO, WARNING, ERROR
logger = get_logger()
config = config_get(silent=True)

MAX_ATTACHED_VOLUMES = 100  # maximum amount of simultaneously attached volumes

class Fs(object):
    def __init__(self, infinibox_vol, sdk, winid=None):
        self.ibox = sdk.get_ibox()
        self.cluster = sdk.get_cluster()
        self.ibox_vol = infinibox_vol
        self.name = infinibox_vol.get_name()
        self.mountpoint = _get_default_mountpoint(self.name)
        self.fs_sizes = lib.get_path_free_size(self.mountpoint)
        self.winid = ps_cmd._run_get_winid_by_serial(infinibox_vol.get_serial()) if winid is None else winid

    def get_name(self):
        return self.name

    def get_mountpoint(self):
        return self.mountpoint

    def get_winid(self):
        return self.winid

    def get_lun_number(self):
        return self.cluster.get_lun(infinibox_vol).get_lun()

    def get_fs_size(self):
        if self.fs_sizes is None:
            return
        return self.fs_sizes['size']

    def get_used_size(self):
        if self.fs_sizes is None:
            return
        return self.fs_sizes['used']

    def get_num_snaps(self):
        return len(self.ibox_vol.get_snapshots().to_list())

    def get_related_shares(self):
        pass


def _get_default_mountpoint(volume_name):
    default_mount_point = path.normcase(path.join(config['MountRoot'], volume_name).strip())
    return default_mount_point


def _winid_serial_table_to_dict():
    import re
    disk_list = []
    cmd_output = execute(['powershell', '-c', 'Get-Disk', '|', 'Select-Object', 'Number,SerialNumber']).get_stdout()
    cmd_output = cmd_output.replace("Number SerialNumber", "").replace("-", "")
    regex = re.compile(r'(?P<winid>\d+)\ (?P<serial>\w+)')
    for line in cmd_output.splitlines():
        result = re.search(regex, line)
        if result:
            disk_list.append(result.groupdict())
    log(logger, "winid serial dict: {}".format(disk_list))
    return disk_list

def _mountpoint_exist(mountpoint):
    '''Check if mount point exist otherwise create it
    '''
    if not path.exists(mountpoint):
        log(logger, "Creating mount path {}".format(mountpoint), level=INFO)
        mkdir(mountpoint)


def _validate_pool(pool_name, ibox_sdk, size):
    from infinisdk.core.type_binder import ObjectNotFound
    from capacity import GiB
    spare_size = 1 * GiB
    try:
        pool = ibox_sdk.pools.choose(name=pool_name)
    except ObjectNotFound:
        log_n_exit(logger, "Pool {} couldn't be found on {}".format(pool_name, ibox_sdk.get_name()))
    new_free = pool.get_free_virtual_capacity() - size - spare_size
    if int(new_free <= 0):
        log_n_exit(logger, "Pool {} doesn't have enough space to provision {!r}".format(pool_name, size))
    return pool


def _count_shares_on_fs(fs_path, shares_paths):
    count = 0
    for share in shares_paths:
        if share.startswith(fs_path):
            count = count + 1
    return count


def _validate_max_amount_of_volumes(sdk):
    from smb.cli.__version__ import __version__
    cluster = sdk.get_cluster()
    if len(cluster.get_luns()) >= MAX_ATTACHED_VOLUMES:
        message = "Version: {} Supports only up to {} simultaneously attached Volumes"
        log(logger, message.format(__version__, MAX_ATTACHED_VOLUMES), color="yellow", level=WARNING)
        exit()


def _validate_vol(ibox_sdk, volume_name):
    from infinisdk.core.type_binder import ObjectNotFound
    try:
        return ibox_sdk.volumes.choose(name=volume_name)
    except ObjectNotFound:
        log_n_exit(logger, "Volume {} couldn't be found on {}".format(volume_name, ibox_sdk.get_name()))


def unmap_vol_from_cluster_infinibox(volume_name, sdk):
    ibox = sdk.get_ibox()
    cluster = sdk.get_cluster()
    volume = ibox.volumes.choose(name=volume_name)
    cluster.unmap_volume(volume)
    log(logger, "Volume {} was unmapped".format(volume.get_name()), color="yellow", level=INFO)


def unmap_volume(volume_name, mountpoint, sdk):
    import os
    unmap_vol_from_cluster_infinibox(volume_name, sdk)
    os.rmdir(mountpoint)


def map_vol_to_cluster(volume, sdk):
    cluster = sdk.get_cluster()
    try:
        mapping = cluster.map_volume(volume)
    except:
        error = sys.exc_info()[1]
        log_n_exit(logger, "Couldn't Map Volume {} to {}! {!r}".format(volume.get_name(),
                                                                       cluster.get_name(), str(error.message)))
    log(logger, "Mapping {} to {}".format(volume.get_name(), cluster.get_name()), level=INFO)


def delete_volume_on_infinibox(volume_name, sdk):
    ibox = sdk.get_ibox()
    volume = ibox.volumes.choose(name=volume_name)
    volume.delete()
    log(logger, "Volume {} was deleted".format(volume_name), level=INFO, color="yellow")


def create_volume_on_infinibox(volume_name, pool_name, size, sdk):
    ibox = sdk.get_ibox()
    pool = _validate_pool(pool_name, ibox, size)
    try:
        log(logger, "Creating Volume {} at {}".format(volume_name, pool_name), level=INFO)
        return ibox.volumes.create(name=volume_name, pool=pool, size=size, provtype='THIN')
    except:
        error = sys.exc_info()[1]
        log_n_exit(logger, "Volume {} couldn't be created. {!r}".format(volume_name, str(error.message)))


def _get_mapped_vols(sdk):
    cluster = sdk.get_cluster()
    mapped_vols = cluster.get_lun_to_volume_dict()
    return [volume for volume in mapped_vols.itervalues()]


def _print_format(val, val_type):
    def _trim(val):
        # only for name and mount
        return val[0:15] + "..."

    def _fill(val, val_type):
        if val_type == "name":
            return val.ljust(18)
        if val_type == "mount":
            return val.ljust(18)
        if val_type in ["size", "used_size"]:
            return val.ljust(12)
        if val_type in ["snaps", "shares"]:
            return val.ljust(7)

    def _trim_or_fill(val, val_type):
        if val_type in ["name", "mount"]:
            if len(val) == 18:
                return (val)
            if len(val) > 18:
                return _trim(val)
            return _fill(val, val_type)
        if val_type in ["size", "used_size", "snaps", "shares"]:
            return _fill(val, val_type)

    return _trim_or_fill(val, val_type)


def print_fs_query(mapped_vols, print_units, serial_list, sdk):
    from smb.cli.share import _share_query_to_share_instance
    shares = _share_query_to_share_instance()
    shares_paths = [share.get_path() for share in shares]
    if len(mapped_vols) > 2:
        ibox = mapped_vols[0].get_system()
    else:
        log(logger, "No volumes are mapped", level=INFO, raw=True)
        exit()
    header = 'Name               Mount              Size         Used Size    Snaps   Shares'
    log(logger, header, level=INFO, raw=True)
    for volume in mapped_vols:
        # Hide irrelevant stuff
        if volume.get_name() in ["mountpoint", "witness"]:
            continue
        if not path.exists(_get_default_mountpoint(volume.get_name())):
            continue
        volume_serial = volume.get_serial()
        for disk in serial_list:
            if disk['serial'] == volume_serial:
                win_id = disk['winid']
                break
        if not win_id:
            win_id = None
        fs = Fs(volume, sdk, win_id)
        num_of_shares = _count_shares_on_fs(fs.get_mountpoint(), shares_paths)
        if print_units:
            fs_size = str((fs.get_fs_size() / print_units)) + " " + str(print_units)[2:]
            used_size = str((fs.get_used_size() / print_units)) + " " + str(print_units)[2:]
        else:
            fs_size = fs.get_fs_size() if Capacity(0) != fs.get_fs_size() else 0
            used_size = fs.get_used_size() if Capacity(0) != fs.get_used_size() else 0
        line = [_print_format(fs.get_name(), "name"),
                _print_format(fs.get_mountpoint(), "mount"),
                _print_format(str(fs_size), "size",),
                _print_format(str(used_size), "used_size"),
                _print_format(str(fs.get_num_snaps()), "snaps"),
                _print_format(str(num_of_shares), "shares")]
        log(logger, line)
        print " ".join(line)


def _get_all_fs(sdk):
    serial_list = _winid_serial_table_to_dict()
    mapped_vols = _get_mapped_vols(sdk)
    for disk in serial_list:
        for ibox_vol in mapped_vols:
            if disk['serial'] == ibox_vol.get_serial():
                disk['fsname'] = ibox_vol.get_name()
                disk['mount'] = _get_default_mountpoint(disk['fsname'])
    return [vol for vol in serial_list if 'mount' in vol]


def fs_query(units, sdk):
    from smb.cli.lib import _validate_size
    if units:
        units = _validate_size(units)
    serial_list = _winid_serial_table_to_dict()
    print_fs_query(_get_mapped_vols(sdk), units, serial_list, sdk)


def fs_attach(volume_name, sdk, force=False):
    ibox = sdk.get_ibox()
    _validate_max_amount_of_volumes(sdk)
    volume = _validate_vol(ibox, volume_name)
    if force and lib.is_volume_mapped_to_cluster(volume, sdk):
        pass
    else:
        map_vol_to_cluster(volume, sdk)
    lib.exit_if_vol_not_mapped(volume)
    fs = Fs(volume, sdk)
    _mountpoint_exist(fs.get_mountpoint())
    ps_cmd._run_attach_vol_to_cluster_scirpt(fs)
    log(logger, "Volume {} Attached to Cluster Successfully.".format(volume_name), level=INFO, color="green")


def fs_detach(fsname, sdk):
    from smb.cli.share import get_all_shares_data, join_fs_and_share
    from smb.cli.share import share_delete
    all_filesystems = _get_all_fs(sdk)
    if fsname not in [fs['fsname'] for fs in all_filesystems]:
        log_n_exit(logger, "{} Does NOT exist. Typo?".format(fsname))
    volume = _validate_vol(sdk.get_ibox(), fsname)
    volume_name = volume.get_name()
    fs = Fs(volume, sdk)
    shares = get_all_shares_data()
    full_share_list = join_fs_and_share(all_filesystems, shares)
    for s in full_share_list:
        if s.get_fs()['fsname'] == fs.get_name():
            share_delete(s.get_name())
    ps_cmd._run_move_cluster_volume_offline(volume_name)
    lib.wait_for_ms_volume_removal(volume_name)
    unmap_volume(volume_name, _get_default_mountpoint(volume_name), sdk)


def fs_delete(fsname, sdk):
    fs_detach(fsname, sdk)
    delete_volume_on_infinibox(fsname, sdk)


def fs_create(volume_name, volume_pool, volume_size, sdk):
    _validate_max_amount_of_volumes(sdk)
    ibox = sdk.get_ibox()
    volume = create_volume_on_infinibox(volume_name, volume_pool, volume_size, sdk)
    map_vol_to_cluster(volume, sdk)
    fs = Fs(volume, sdk)
    ps_cmd._run_prep_vol_to_cluster_scirpt(fs)
    try:
        fs_attach(volume_name, sdk, force=True)
    except:
        e = sys.exc_info
        log(logger, "Something went wrong. Rolling back operations...", level=ERROR, color="red")
        unmap_volume(volume_name, mountpoint, sdk)
        delete_volume_on_infinibox(volume_name, sdk)
