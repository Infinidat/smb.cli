import sys
from capacity import *
from os import path, mkdir
from smb.cli import lib, ps_cmd
from infi.execute import execute
from smb.cli.config import config_get
from smb.cli.smb_log import get_logger, log, log_n_raise, SmbCliExited
from logging import DEBUG, INFO, WARNING, ERROR
from smb.cli.__version__ import __version__
logger = get_logger()
config = config_get(silent=True)

MAX_ATTACHED_VOLUMES = 100  # maximum amount of simultaneously attached volumes
MAX_VOL_NAME_LENGTH = 24

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
        log(logger, "Creating mount path {}".format(mountpoint), level=DEBUG)
        mkdir(mountpoint)


def _validate_vol_name(volume_name):
    '''Spaces in names aren't allowed'''
    if ' ' in volume_name:
        log_n_raise(logger, "Spaces aren't allowed in FS names. Please rename '{}'".format(volume_name),
            level=WARNING)
    if len(volume_name) > MAX_VOL_NAME_LENGTH:
        log_n_raise(logger, "'{}' FileSystem name is too long! (can be up to {} characters)".format(volume_name, MAX_VOL_NAME_LENGTH),
            level=WARNING)


def _validate_pool_name(pool_name, ibox_sdk):
    from infinisdk.core.type_binder import ObjectNotFound
    try:
        pool = ibox_sdk.pools.choose(name=pool_name)
        return pool
    except ObjectNotFound:
        log_n_raise(logger, "Pool {} couldn't be found on {}".format(pool_name, ibox_sdk.get_name()))


def _validate_pool(pool_name, ibox_sdk, size):
    from capacity import GiB
    pool = _validate_pool_name(pool_name, ibox_sdk)
    spare_size = 1 * GiB
    new_free = pool.get_free_virtual_capacity() - size - spare_size
    if int(new_free <= 0):
        log_n_raise(logger, "Pool {} doesn't have enough space to provision {!r}".format(pool_name, size))
    return pool


def _validate_max_amount_of_volumes(sdk):
    from smb.cli.__version__ import __version__
    cluster = sdk.get_cluster()
    if len(cluster.get_luns()) >= MAX_ATTACHED_VOLUMES:
        message = "Version: {} Supports only up to {} simultaneously attached Volumes"
        log_n_raise(logger, message.format(__version__, MAX_ATTACHED_VOLUMES), level=WARNING)


def _validate_vol(ibox_sdk, volume_name):
    from infinisdk.core.type_binder import ObjectNotFound
    try:
        return ibox_sdk.volumes.choose(name=volume_name)
    except ObjectNotFound:
        log_n_raise(logger, "Volume {} couldn't be found on {}".format(volume_name, ibox_sdk.get_name()))


def unmap_vol_from_cluster_infinibox(volume_name, sdk):
    ibox = sdk.get_ibox()
    cluster = sdk.get_cluster()
    volume = ibox.volumes.choose(name=volume_name)
    cluster.unmap_volume(volume)
    log(logger, "Volume {} was unmapped".format(volume.get_name()), color="yellow", level=INFO)


def unmap_volume(volume_name, mountpoint, sdk):
    import os
    unmap_vol_from_cluster_infinibox(volume_name, sdk)
    try:
        if os.listdir(mountpoint) == []:
            os.rmdir(mountpoint)
        else:
            log(logger, "Not Deleting {} Because it's Not Empty".format(mountpoint), color="yellow", level=INFO)
    except Exception as e:
        log(logger, "{}".format(e))


def map_vol_to_cluster_infinibox(volume, sdk):
    cluster = sdk.get_cluster()
    try:
        mapping = cluster.map_volume(volume)
    except:
        error = sys.exc_info()[1]
        log_n_raise(logger, "Couldn't Map Volume {} to {}! {!r}".format(volume.get_name(),
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
        volume = ibox.volumes.create(name=volume_name, pool=pool, size=size, provtype='THIN')
        volume.set_metadata('volume.provisionedby', 'smb.cli-{}'.format(__version__))
        return volume
    except:
        error = sys.exc_info()[1]
        log_n_raise(logger, "Volume {} couldn't be created. {!r}".format(volume_name, str(error.message)))


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


def print_fs_query(mapped_vols, print_units, serial_list, sdk, detailed=False):
    from smb.cli.share import _share_query_to_share_instance
    shares = _share_query_to_share_instance()
    shares_paths = [share.get_path() for share in shares]
    if len(mapped_vols) <= 2:
        log(logger, "No InfiniBox Volumes are Mapped to the Cluster", level=INFO)
        return
    ibox = mapped_vols[0].get_system()
    vols_in_cluster = ps_cmd._get_cluster_vols().splitlines()
    print_output = ""
    for volume in mapped_vols:
        volume_name = volume.get_name()
        # Hide irrelevant stuff
        if volume_name in ["mountpoint", "witness"]:
            continue
        if volume_name not in vols_in_cluster:
            continue
        if not path.exists(_get_default_mountpoint(volume_name)):
            continue
        volume_serial = volume.get_serial()
        win_id = None
        for disk in serial_list:
            if disk['serial'] == volume_serial:
                win_id = disk['winid']
                break
        fs = Fs(volume, sdk, win_id)
        num_of_shares = lib.count_shares_on_fs(fs.get_mountpoint(), shares_paths)
        if print_units:
            fs_size = "{:.2f}".format(float(str(float(fs.get_fs_size().roundup(MiB) / MiB) * MiB / print_units)))
            fs_size = fs_size + " " + str(print_units)[2:]
            used_size = "{:.2f}".format(float(str(float(fs.get_used_size().roundup(MiB) / MiB) * MiB / print_units)))
            used_size = used_size + " " + str(print_units)[2:]
        else:
            fs_size = fs.get_fs_size() if Capacity(0) != fs.get_fs_size() else 0
            used_size = fs.get_used_size() if Capacity(0) != fs.get_used_size() else 0
        if detailed:
            line = ["{}: {}".format("name", fs.get_name()),
                    "{}: {}".format("mount", fs.get_mountpoint()),
                    "{}: {}".format("size", str(fs_size)),
                    "{}: {}".format("used_size", str(used_size)),
                    "{}: {}".format("snaps", str(fs.get_num_snaps())),
                    "{}: {}".format("shares", str(num_of_shares))]
        else:
            line = [_print_format(fs.get_name(), "name"),
                    _print_format(fs.get_mountpoint(), "mount"),
                    _print_format(str(fs_size), "size",),
                    _print_format(str(used_size), "used_size"),
                    _print_format(str(fs.get_num_snaps()), "snaps"),
                    _print_format(str(num_of_shares), "shares")]
        log(logger, line)
        print_output = print_output + " ".join(line) + '\n'
    if print_output.splitlines() == []:
        log(logger, "No InfiniBox Volumes are Mapped to the Cluster", level=INFO)
        return
    header = 'Name               Mount              Size         Used Size    Snaps   Shares'
    log(logger, header, level=INFO, raw=True)
    print print_output


def _get_all_fs(sdk):
    serial_list = _winid_serial_table_to_dict()
    mapped_vols = _get_mapped_vols(sdk)
    vols_in_cluster = ps_cmd._get_cluster_vols().splitlines()
    for disk in serial_list:
        for ibox_vol in mapped_vols:
            vol_name = ibox_vol.get_name()
            if vol_name not in vols_in_cluster:
                continue
            if disk['serial'] == ibox_vol.get_serial():
                disk['fsname'] = vol_name
                disk['mount'] = _get_default_mountpoint(disk['fsname'])
                disk['sizes'] = lib.get_path_free_size(disk['mount'])
    return [vol for vol in serial_list if 'mount' in vol]


def fs_query(units, sdk, detailed):
    from smb.cli.lib import _validate_size
    if units:
        units = _validate_size(units)
    serial_list = _winid_serial_table_to_dict()
    ibox_mapped_vols = _get_mapped_vols(sdk)
    print_fs_query(ibox_mapped_vols, units, serial_list, sdk, detailed)


def fs_attach(volume_name, sdk, force=False):
    ibox = sdk.get_ibox()
    _validate_max_amount_of_volumes(sdk)
    _validate_vol_name(volume_name)
    volume = _validate_vol(ibox, volume_name)
    if force and lib.is_volume_mapped_to_cluster(volume, sdk):
        pass
    else:
        map_vol_to_cluster_infinibox(volume, sdk)
    lib.exit_if_vol_not_mapped(volume)
    fs = Fs(volume, sdk)
    _mountpoint_exist(fs.get_mountpoint())
    try:
        ps_cmd._run_attach_vol_to_cluster_script(fs)
    except:
        log_n_raise(logger, "Couldn't add {} to SMB Cluster".format(volume_name))
    log(logger, "Volume {} Attached to Cluster Successfully.".format(volume_name), level=INFO, color="green")


def fs_detach(fsname, sdk):
    from smb.cli.share import get_all_shares_data, join_fs_and_share
    from smb.cli.share import share_delete
    all_filesystems = _get_all_fs(sdk)
    if fsname not in [fs['fsname'] for fs in all_filesystems]:
        log_n_raise(logger, "{} Does NOT exist. Typo?".format(fsname))
    volume = _validate_vol(sdk.get_ibox(), fsname)
    volume_name = volume.get_name()
    fs = Fs(volume, sdk)
    shares = get_all_shares_data()
    full_share_list = join_fs_and_share(all_filesystems, shares)
    for s in full_share_list:
        if s.get_fs()['fsname'] == fs.get_name():
            share_delete(s.get_name())
    ps_cmd._run_remove_partition_access_path(fs.get_winid(), fs.get_mountpoint())
    ps_cmd._run_move_cluster_volume_offline(volume_name)
    lib.cluster_remove_ms_volume_and_wait(volume_name)
    unmap_volume(volume_name, fs.get_mountpoint(), sdk)


def fs_delete(fsname, sdk):
    fs_detach(fsname, sdk)
    delete_volume_on_infinibox(fsname, sdk)


def fs_create(volume_name, volume_pool, volume_size, sdk):
    _validate_max_amount_of_volumes(sdk)
    _validate_vol_name(volume_name)
    ibox = sdk.get_ibox()
    volume = create_volume_on_infinibox(volume_name, volume_pool, volume_size, sdk)
    try:
        map_vol_to_cluster_infinibox(volume, sdk)
        lib.exit_if_vol_not_mapped(volume)
    except:
        log(logger, "Something went wrong. Rolling back operations...", level=ERROR, color="red")
        unmap_volume(volume_name, _get_default_mountpoint(volume_name), sdk)
        delete_volume_on_infinibox(volume_name, sdk)
        raise SmbCliExited
    fs = Fs(volume, sdk)
    log(logger, "Preparing Filesystem for {}. This might take a while. \nDO NOT EXIT!".format(volume_name),
            level=INFO, color="yellow")
    if fs.get_winid() is None:
        fs = Fs(volume, sdk)
    try:
        ps_cmd._run_prep_vol_to_cluster_script(fs)
    except:
        log(logger, "Something went wrong. Rolling back operations...", level=ERROR, color="red")
        unmap_volume(volume_name, _get_default_mountpoint(volume_name), sdk)
        delete_volume_on_infinibox(volume_name, sdk)
        raise SmbCliExited
    try:
        fs_attach(volume_name, sdk, force=True)
    except:
        log(logger, "Something went wrong. Rolling back operations...", level=ERROR, color="red")
        try:
            ps_cmd._run_move_cluster_volume_offline(volume_name)
        except:
            pass
        try:
            lib.cluster_remove_ms_volume_and_wait(volume_name)
        except:
            pass
        unmap_volume(volume_name, _get_default_mountpoint(volume_name), sdk)
        delete_volume_on_infinibox(volume_name, sdk)
        raise SmbCliExited
