import sys
from capacity import *
from smb.cli import lib
from infi.execute import execute_assert_success, execute
from smb.cli.lib import InfiSdkObjects
config = InfiSdkObjects().get_local_config()

def run(cmd, error_prefix):
    try:
        result = execute_assert_success(cmd)
        return result.get_stdout()
    except:
        error = sys.exc_info()[1]
        lib.print_red("{} {}".format(error_prefix, error))
        exit()


def _run_share_create(share_name, share_path):
    cmd = ['powershell', '-c', 'New-SmbShare', '-Name', lib.pad_text(share_name),
           '-Path', lib.pad_text(share_path), '-ScopeName', config['FSRoleName'],
           '-ContinuouslyAvailable:$true', '-CachingMode', 'None']
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


def _run_get_winid_by_serial(luid):
    '''logical unit id (luid) is also the infinibox volume serial
    '''
    cmd_output = execute(['powershell', '-c', 'Get-Disk', '-SerialNumber',
                          str(luid), '|', 'Select-Object -ExpandProperty number']).get_stdout()
    try:
        return int(cmd_output)
    except:
        return


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

def _run_move_cluster_volume_offline(vol_name):
    cmd = ['powershell', '-c', '"', 'Stop-ClusterResource', '-Name', lib.pad_text(str(vol_name)),
           '-Cluster', lib.pad_text(config['FSRoleName']), '-Confirm:$False', '"']
    error_prefix = "Stop-ClusterResource failed with error:"
    run(cmd, error_prefix)


def _run_reomve_vol_from_cluster(vol_name):
    cmd = ['powershell', '-c', '"', 'Remove-ClusterResource', '-Name', lib.pad_text(str(vol_name)),
           '-Cluster', config['FSRoleName'], '-Confirm:$False', '"']
    error_prefix = "Remove-ClusterResource failed with error:"
    run(cmd, error_prefix)

