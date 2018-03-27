import sys
from capacity import *
from smb.cli import lib
from infi.execute import execute_assert_success, execute
from smb.cli import config_get
from smb.cli.smb_log import get_logger, log_n_raise
from logging import DEBUG, INFO, WARNING, ERROR
logger = get_logger()
config = config_get(silent=True)


def run(cmd, error_prefix):
    result = execute(cmd)
    if result.get_returncode() == 0:
        return result.get_stdout()
    if "You do not have administrative privileges on the cluster" in result.get_stderr():
        log_n_raise(logger, "{} Cluster Permissions issue".format(error_prefix))
    log_n_raise(logger, "{} {}".format(error_prefix, result.get_stderr()), disable_print=True)


def _run_share_create(share_name, share_path):
    cmd = ['powershell', '-c', 'New-SmbShare', '-Name', lib.pad_text(share_name),
           '-Path', lib.pad_text(share_path), '-ScopeName', config['FSRoleName'],
           '-ContinuouslyAvailable:$true', '-CachingMode', 'None', '-FullAccess', 'Everyone']
    error_prefix = "New-SmbShare failed with error:"
    run(cmd, error_prefix)


def _run_share_delete(share_name):
    cmd = ['powershell', '-c', 'Remove-SmbShare', '-Name', lib.pad_text(share_name),
                                '-ScopeName', config['FSRoleName'], '-Confirm:$False']
    error_prefix = "Remove-SmbShare failed with error:"
    run(cmd, error_prefix)


def _run_share_query():
    cmd = ['powershell', '-c', 'Get-SmbShare', '-ScopeName', config['FSRoleName'],
           '|', 'Format-Custom', 'Name, Path']
    error_prefix = "Get-SmbShare failed with error:"
    return run(cmd, error_prefix)


def _run_share_quota_get():
    cmd = ['powershell', '-c', 'Get-FSRMQuota', '|', 'Select-Object',
           'Path, Disabled, size, Usage, Softlimit', '|', 'Format-Custom']
    error_prefix = "Get-SmbShare failed with error:"
    return run(cmd, error_prefix)


def _run_create_share_limit_default(share_path):
    # This can be always set over and over from any state
    cmd = ['powershell', '-c', 'New-FSRMQuota', '-Path', lib.pad_text(share_path), '-Size 1KB', '-Disabled:$True']
    error_prefix = "New-FSRMQuota failed with error:"
    run(cmd, error_prefix)


def _run_share_limit_set_default(share_path):
    # This can be always set over and over from any state
    cmd = ['powershell', '-c', 'Set-FSRMQuota', '-Path', lib.pad_text(share_path), '-Size 1KB', '-Disabled:$True']
    error_prefix = "New-FSRMQuota failed with error:"
    run(cmd, error_prefix)


def _run_share_limit_set(share_path, size):
    # Size differnces between capacity and windows ( in Win KB is KiB)
    size = str((size / byte) / 1024) + "KB"
    cmd = ['powershell', '-c', 'Set-FSRMQuota', '-Path', lib.pad_text(share_path), '-Size',
           size, '-Disabled:$False']
    error_prefix = "Set-FSRMQuota failed with error:"
    run(cmd, error_prefix)


def _run_share_limit_delete(share_path):
    # This can be always set over and over from any state
    cmd = ['powershell', '-c', 'Remove-FSRMQuota', '-Path', lib.pad_text(share_path), '-Confirm:$False']
    error_prefix = "Remove-FSRMQuota failed with error:"
    run(cmd, error_prefix)


def _run_get_winid_by_serial(luid):
    '''logical unit id (luid) is also the infinibox volume serial
    '''
    cmd_output = execute(['powershell', '-c', 'Get-Disk', '-SerialNumber',
                          str(luid), '|', 'Select-Object -ExpandProperty number']).get_stdout()
    try:
        return int(cmd_output)
    except ValueError:
        return


def _run_prep_vol_to_cluster_script(fs):
    # TODO: move to run
    # TODO: handle the cases where fs.get_winid is None
    from smb import PROJECTROOT
    from os import path
    vol_to_cluster_script = path.realpath(path.join(PROJECTROOT, 'src', 'smb', 'cli',
                                                    'powershell', 'prep_vol_to_cluster.ps1'))
    if fs.get_winid() is None:
        log_n_raise(logger, "Can't prepare volume {}".format(fs.get_name()), level=ERROR, color="red")
    try:
        cmd = execute_assert_success(['powershell', '.', '"' + vol_to_cluster_script.replace('\\', '/') +
                                 '"' + " -DiskNumber {} -MountPath {}".format(fs.get_winid(), fs.get_mountpoint())])
    except:
        error = sys.exc_info()[1]
        log_n_raise(logger, "{} failed with error: {}".format(vol_to_cluster_script, error), disable_print=True)


def _run_attach_vol_to_cluster_script(fs):
    # TODO: move to run
    from smb import PROJECTROOT
    from os import path
    attach_vol_to_cluster_script = path.realpath(path.join(PROJECTROOT, 'src', 'smb', 'cli',
                                                           'powershell', 'add_vol_to_cluster.ps1'))
    try:
        cmd = execute_assert_success(['powershell', '.', '"' + attach_vol_to_cluster_script.replace('\\', '/') +
                                 '"' + " -DiskNumber {}".format(fs.get_winid())])
    except:
        error = sys.exc_info()[1]
        log_n_raise(logger, "{} failed with error: {}".format(attach_vol_to_cluster_script, error), disable_print=True)


def _perform_cluster_failover():
    ''' Used only for tests'''
    cmd = ['powershell', '-c', 'Move-ClusterGroup', '-Name', lib.pad_text(config['FSRoleName'])]
    error_prefix = "Move-ClusterGroup failed with error:"
    run(cmd, error_prefix)


def _run_offline_disk(disk_number):
    from os import remove
    if disk_number is None:
        return

    def _create_disk_part_script(disk_number):
        with open('tmp_diskpart', 'w') as fd:
            fd.write("select disk {}\n".format(str(disk_number)))
            fd.write("offline disk")

    _create_disk_part_script(disk_number)
    cmd = ['diskpart.exe', '/s', 'tmp_diskpart']
    error_prefix = "diskpart failed with error:"
    run(cmd, error_prefix)
    remove('tmp_diskpart')


def _run_remove_partition_access_path(disk_number, access_path):
    cmd = ['powershell', '-c', 'Remove-PartitionAccessPath', '-DiskNumber', str(disk_number), '-PartitionNumber 2',
           '-AccessPath', lib.pad_text(access_path)]
    error_prefix = "Remove-PartitionAccessPath failed with error:"
    run(cmd, error_prefix)


def _run_move_cluster_volume_offline(vol_name):
    cmd = ['powershell', '-c', 'Stop-ClusterResource', '-Name', lib.pad_text(str(vol_name)),
           '-Cluster', lib.pad_text(config['FSRoleName'])]
    error_prefix = "Stop-ClusterResource failed with error:"
    run(cmd, error_prefix)


def _run_move_volume_from_smb_cluster(vol_name):
    cmd = ['powershell', '-c', 'Move-ClusterResource', '-Name', lib.pad_text(str(vol_name)),
           '-Group "Cluster Group"']
    error_prefix = "Move-ClusterResource failed with error:"
    run(cmd, error_prefix)


def _run_remove_vol_from_cluster(vol_name):
    # for some wierd way -Confirm:$False isn't working here but -Force does
    cmd = ['powershell', '-c', 'Remove-ClusterResource', '-Name', lib.pad_text(str(vol_name)),
           '-Cluster', lib.pad_text(config['FSRoleName']), '-Force']
    error_prefix = "Remove-ClusterResource failed with error:"
    run(cmd, error_prefix)


def _get_cluster_vols():
    cmd = ['powershell', '-c', 'Get-ClusterResource', '-Cluster', lib.pad_text(config['FSRoleName']),
           '|', 'where OwnerGroup -eq', lib.pad_text(config['FSRoleName']), '|', 'Select-Object', '-ExpandProperty Name']
    error_prefix = "Get-ClusterResource failed with error:"
    return run(cmd, error_prefix)
