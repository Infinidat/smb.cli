import sys
from capacity import *
from smb.cli import lib
from infi.execute import execute_assert_success, execute
from smb.cli.config import config_get
config = config_get(silent=True)
MAX_ATTACHED_VOLUMES = 100  # maximum amount of simultaneously attached volumes

class Fs(object):
    def __init__(self, infinibox_vol_name, lun_number, winid, num_snaps):
        self.infinibox_vol_name = infinibox_vol_name
        self.lun_number = lun_number
        self.winid = winid
        self.mountpoint = _get_default_mountpoint(infinibox_vol_name)
        self.fs_sizes = lib.get_path_free_size(self.mountpoint)
        self.num_snaps = num_snaps

    def get_mountpoint(self):
        return self.mountpoint

    def get_winid(self):
        return self.winid

    def get_lun_number(self):
        return self.lun_number

    def get_infinibox_vol_name(self):
        return self.infinibox_vol_name

    def get_fs_size(self):
        return self.fs_sizes['size'] * KiB

    def get_used_size(self):
        return self.fs_sizes['used'] * KiB

    def get_num_snaps(self):
        return self.num_snaps


def instance_fs(volume, cluster, win_id=None):
    ''' receives an infinisdk volume object and create a usable fs instance
    '''
    volume_name = volume.get_name()
    lun_number = cluster.get_lun(volume).get_lun()
    if win_id is None:
        win_id = _get_winid_by_serial(volume.get_serial())
    num_snaps = len(volume.get_snapshots().to_list())
    return Fs(volume_name, lun_number, win_id, num_snaps)


def _get_default_mountpoint(vol_name):
    from os import path
    return path.normcase(path.join(config['MountRoot'], vol_name).strip())


def _get_winid_by_serial(luid):
    '''logical unit id (luid) is also the infinibox volume serial
    '''
    cmd_output = execute(['powershell', '-c', 'Get-Disk', '-SerialNumber',
                          str(luid), '|', 'Select-Object -ExpandProperty number']).get_stdout()
    try:
        return int(cmd_output)
    except:
        return

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
    return disk_list

def _mountpoint_exist(mountpoint):
    '''Check if mount point exist otherwise create it
    '''
    from os import path, mkdir
    if not path.exists(mountpoint):
        print "Creating mount path {}".format(mountpoint)
        mkdir(mountpoint)


def _run_prep_vol_to_cluster_scirpt(fs):
    from smb import PROJECTROOT
    from os import path, pardir
    vol_to_cluster_script = path.realpath(path.join(PROJECTROOT, pardir, 'SMB-cluster', 'src', 'prep_vol_to_cluster.ps1'))
    try:
        cmd = execute_assert_success(['powershell', '.', '"' + vol_to_cluster_script.replace('\\', '/') +
                                 '"' + " -DiskNumber {} -MountPath {}".format(fs.get_winid(), fs.get_mountpoint())])
    except:
        error = sys.exc_info()[1]
        lib.print_red("{} failed with error: {}".format(vol_to_cluster_script, error))
        exit()


def _run_attach_vol_to_cluster_scirpt(fs):
    from smb import PROJECTROOT
    from os import path, pardir
    attach_vol_to_cluster_script = path.realpath(path.join(PROJECTROOT, pardir, 'SMB-cluster', 'src', 'add_vol_to_cluster.ps1'))
    try:
        cmd = execute_assert_success(['powershell', '.', '"' + attach_vol_to_cluster_script.replace('\\', '/') +
                                 '"' + " -DiskNumber {}".format(fs.get_winid())])
    except:
        error = sys.exc_info()[1]
        lib.print_red("{} failed with error: {}".format(attach_vol_to_cluster_script, error))
        exit()


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


def _validate_max_amount_of_volumes(lib_sdk):
    from smb.cli.__version__ import __version__
    cluster = lib_sdk.get_cluster()
    if len(cluster.get_luns()) >= MAX_ATTACHED_VOLUMES:
        message = "Version: {} Supports only up to {} simultaneously attached Volumes"
        lib.print_yellow(message.format(__version__, MAX_ATTACHED_VOLUMES))
        exit()


def _validate_vol(ibox_sdk, vol_name):
    from infinisdk.core.type_binder import ObjectNotFound
    try:
        return ibox_sdk.volumes.choose(name=vol_name)
    except ObjectNotFound:
        lib.print_yellow("Volume {} couldn't be found on {}".format(vol_name, ibox_sdk.get_name()))
        exit()

def _count_shares_on_fs(fs_path, shares_paths):
    count = 0
    for share in shares_paths:
        if share.startswith(fs_path):
            count = count + 1
    return count


def unmap_vol_from_cluster_windows(volume_name):
    pass


def unmap_vol_from_cluster_infinibox(volume_name):
    sdk = lib.InfiSdkObjects()
    ibox = sdk.get_ibox()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    volume = ibox.volumes.choose(name=volume_name)
    cluster.unmap_volume(volume)
    lib.print_yellow("Volume {} was just unmapped".format(volume.get_name()))


def map_vol_to_cluster(volume):
    sdk = lib.InfiSdkObjects()
    ibox = sdk.get_ibox()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    try:
        mapping = cluster.map_volume(volume)
    except:
        error = sys.exc_info()[1]
        lib.print_red("Couldn't Map Volume {} to {}! {!r}".format(volume.get_name(),
                                                                       cluster.get_name(), str(error.message)))
        exit()
    print "Mapping {} to {}".format(volume.get_name(), cluster.get_name())


def delete_volume_on_infinibox(volume_name):
    sdk = lib.InfiSdkObjects()
    ibox = sdk.get_ibox()
    volume = ibox.volumes.choose(name=volume_name)
    volume.delete()
    lib.print_yellow("Volume {} was deleted".format(volume_name))


def create_volume_on_infinibox(volume_name, pool_name, size):
    sdk = lib.InfiSdkObjects()
    ibox = sdk.get_ibox()
    pool = _validate_pool(pool_name, ibox, size)
    try:
        print "Creating Volume {} at {}".format(volume_name, pool_name)
        return ibox.volumes.create(name=volume_name, pool=pool, size=size, provtype='THIN')
    except:
        error = sys.exc_info()[1]
        lib.print_red("Volume {} couldn't be created. {!r}".format(volume_name, str(error.message)))
        exit()


def clean_fs(fs):
    import os
    unmap_vol_from_cluster_infinibox(fs.get_infinibox_vol_name())
    os.rmdir(fs.get_mountpoint())
    lib.print_yellow("Directory {} was deleted".format(fs.get_mountpoint()))
    delete_volume_on_infinibox(fs.get_infinibox_vol_name())


def _get_mapped_vols():
    sdk = lib.InfiSdkObjects()
    ibox = sdk.get_ibox()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
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


def print_fs_query(mapped_vols, print_units, serial_list):
    from smb.cli.share import _share_query_to_share_instance
    shares = _share_query_to_share_instance()
    shares_paths = [share.get_path() for share in shares]
    if len(mapped_vols) > 2:
        ibox = mapped_vols[0].get_system()
    else:
        print "No volumes are mapped"
        exit()
    header = 'Name               Mount              Size         Used Size    Snaps   Shares'
    print header
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
    for volume in mapped_vols:
        if volume.get_name() in ["mountpoint", "witness"]:
            continue
        volume_serial = volume.get_serial()
        for disk in serial_list:
            if disk['serial'] == volume_serial:
                win_id = disk['winid']
                break
        if not win_id:
            win_id = None
        fs = instance_fs(volume, cluster, win_id)
        num_of_shares = _count_shares_on_fs(fs.get_mountpoint(), shares_paths)
        if print_units:
            fs_size = str((fs.get_fs_size() / print_units)) + " " + str(print_units)[2:]
            used_size = str((fs.get_used_size() / print_units)) + " " + str(print_units)[2:]
        else:
            fs_size = fs.get_fs_size() if Capacity(0) != fs.get_fs_size() else 0
            used_size = fs.get_used_size() if Capacity(0) != fs.get_used_size() else 0
        line = [_print_format(fs.get_infinibox_vol_name(), "name"),
                _print_format(fs.get_mountpoint(), "mount"),
                _print_format(str(fs_size), "size",),
                _print_format(str(used_size), "used_size"),
                _print_format(str(fs.get_num_snaps()), "snaps"),
                _print_format(str(num_of_shares), "shares")]
        print " ".join(line)

def _get_all_fs():
    serial_list = _winid_serial_table_to_dict()
    mapped_vols = _get_mapped_vols()
    for disk in serial_list:
        for ibox_vol in mapped_vols:
            if disk['serial'] == ibox_vol.get_serial():
                disk['fsname'] = ibox_vol.get_name()
                disk['mount'] = _get_default_mountpoint(disk['fsname'])
    return [vol for vol in serial_list if 'mount' in vol]


def fs_query(units):
    from smb.cli.lib import _validate_size
    if units:
        units = _validate_size(units)
    serial_list = _winid_serial_table_to_dict()
    print_fs_query(_get_mapped_vols(), units, serial_list)


def fs_attach(volume_name, force=False):
    sdk = lib.InfiSdkObjects()
    ibox = sdk.get_ibox()
    _validate_max_amount_of_volumes(sdk)
    volume = _validate_vol(ibox, vol_name=volume_name)
    if force and lib.is_volume_mapped_to_cluster(volume):
        pass
    else:
        map_vol_to_cluster(volume)
    lib.exit_if_vol_not_mapped(volume)
    fs = instance_fs(volume, sdk.get_cluster())
    _mountpoint_exist(fs.get_mountpoint())
    _run_attach_vol_to_cluster_scirpt(fs)
    lib.print_green("Volume {} Attached to Cluster Successfully.".format(volume_name))

def fs_detach():
    '''
    Stop-ClusterResource -name -Cluster # offline
    Remove-ClusterResource [[-Name] -Cluster
    '''
    pass

def fs_create(volume_name, volume_pool, volume_size):
    sdk = lib.InfiSdkObjects()
    _validate_max_amount_of_volumes(sdk)
    volume = create_volume_on_infinibox(volume_name, volume_pool, volume_size)
    map_vol_to_cluster(volume)
    fs = instance_fs(volume, sdk.get_cluster())
    _run_prep_vol_to_cluster_scirpt(fs)
    try:
        fs_attach(volume_name, force=True)
    except:
        e = sys.exc_info
        lib.print_red("Something went wrong. Rolling back operations...")
        fs = instance_fs(volume, sdk.get_cluster())
        clean_fs(fs) # should be relaced with delete
