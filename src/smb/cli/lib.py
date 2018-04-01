import sys
import colorama
from os import path, pardir
from smb.cli.config import config_get
from infi.execute import execute_assert_success, execute
from smb.cli.smb_log import get_logger, log, log_n_raise
from logging import INFO, WARNING
from smb import PROJECTROOT
logger = get_logger()

def prechecks():
    from smb.cli.ibox_connect import InfiSdkObjects
    log(logger, "Running Prechecks...", level=INFO)
    sdk = InfiSdkObjects()
    sdk.get_ibox()
    is_cluster_online()
    am_I_master()
    return sdk

def am_I_master():
    from platform import node
    config = config_get(silent=True)
    cmd = execute_assert_success(['powershell', '-c', 'Get-ClusterGroup', '-name', config['FSRoleName'], '|', 'Select-Object',
                            '-ExpandProperty', 'OwnerNode', '|', 'Select-Object', '-ExpandProperty', 'name'])
    if cmd.get_stdout().strip() == node():
        return True
    else:
        log_n_raise(logger, "The Node you are running on is NOT the Active Cluster Node")

def is_cluster_online():
    config = config_get(silent=True)
    cmd = execute_assert_success(['powershell', '-c', 'Get-ClusterGroup', '-name', config['FSRoleName'], '|', 'Select-Object',
                            '-ExpandProperty', 'state'])
    if cmd.get_stdout().strip() != 'Online':
        log_n_raise(logger, "Cluster group {} NOT in Online state !! state is: {}".format(config['FSRoleName'], cmd.get_stdout().strip()))


def exit_if_vol_not_mapped(volume):
    ''' receives an infinisdk volume type and checks if mapped'''
    def _is_vol_mapped(volume_serial, timeout=3):
        from time import sleep
        for n in range(0, timeout):
            execute_assert_success(['powershell', '-c', 'Update-HostStorageCache'])
            try:
                execute_assert_success(['powershell', '-c', 'Get-Disk', '-SerialNumber', str(volume_serial)])
                return True
            except:
                sleep(1)
                continue
        return False

    def _rescan():
        ''' From what I saw on 90% of the times the volume just apear on both nodes
        If it doesn't we'll rescan
        '''
        HPT_BIN_FILE = 'infinihost.exe'
        # to do need to think if we'd like to scan on remote and verify
        hpt_bin = path.realpath(path.join(PROJECTROOT, pardir, 'Host Power Tools', 'bin', HPT_BIN_FILE))
        execute([hpt_bin, 'rescan'])

    if not _is_vol_mapped(volume.get_serial()):
        _rescan()
        if not _is_vol_mapped(volume.get_serial()):
            log_n_raise(logger, "Windows couldn't gain access to volume {} which was just mapped".format(volume.get_name()))


def _validate_size(size_str, roundup=False):
    import capacity
    from capacity import byte
    if size_str == '0' or size_str is None:
        return 0
    try:
        size = capacity.from_string(size_str)
    except ValueError:
        log_n_raise(logger, "{} is an invalid capacity ! Please try one of the following:\n".format(size_str) +
                         "<number> KB, KiB, MB, MiB, GB, GiB, TB, TiB... ", level=WARNING)
    if size == capacity.Capacity(0):
        return 0
    if roundup:
        if (size / byte) / 512.0 != int((size / byte) / 512.0):
            size = ((int((size / byte) / 512) + 1) * 512) * byte
    return size


def is_path_part_of_path(path_a, path_b):
    '''understands if 2 path have parent children relationship '''
    def is_a_parant_of_b(a, b):
        if path.normpath(a) == path.normpath(b):
            return True
        elif len(b) <= len(a):
            return False
        return is_a_parant_of_b(a, path.dirname(b))

    if is_a_parant_of_b(path_a, path_b) or is_a_parant_of_b(path_b, path_a):
        return True
    else:
        return False


def count_shares_on_fs(fs_path, shares_paths):
    count = 0
    for share in shares_paths:
        if is_path_part_of_path(share, fs_path):
            count += 1
    return count


def get_path_free_size(full_path):
    ''' inspired by:
    http://code.activestate.com/recipes/577972-disk-usage/
    '''
    import ctypes
    from capacity import byte
    size = {}
    _, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
    space = ctypes.windll.kernel32.GetDiskFreeSpaceExA
    result = space(str(full_path), ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
    if result == 0:
        return
    used = total.value - free.value
    size['size'] = total.value * byte
    size['used'] = used * byte
    size['avail'] = free.value * byte
    log(logger, "sizes are {}".format(size))
    return size


def is_disk_in_cluster(disk_win_id):
    is_disk_in_cluster_script = path.realpath(path.join(PROJECTROOT, 'src', 'smb', 'cli', 'powershell',
                                                        'DiskToClusterDiskResource.ps1'))
    output = execute(['powershell', '-c', '$Disk =' 'Get-Disk', '-Number', str(disk_win_id), ';',
                      '.', pad_text(is_disk_in_cluster_script), '-Disk', '$Disk'])
    if 'MSCluster' in output.get_stdout():
        return True
    else:
        return False


def pad_text(path):
    return "'{}'".format(path)


def is_volume_mapped_to_cluster(volume, sdk):
    cluster = sdk.get_cluster()
    try:
        cluster.get_lun(volume)
    except:
        error = sys.exc_info()[1]
        return False
    return True


def get_privileges_text():
    return "This tool requires administrative privileges."


def cluster_remove_ms_volume_and_wait(volume_name):
    from time import sleep
    from smb.cli import ps_cmd
    ps_cmd._run_remove_vol_from_cluster(volume_name)
    timeout = 10
    for i in range(timeout):
        vols_in_cluster = ps_cmd._get_cluster_vols().splitlines()
        if volume_name in vols_in_cluster:
            sleep(1)
        else:
            sleep(2)
            return


def _init_colorama():
    import os
    from colorama import init
    global output_stream
    if 'TERM' not in os.environ:
        init()


def print_green(text):
    print colorama.Fore.LIGHTGREEN_EX + colorama.Back.BLACK + text + colorama.Fore.RESET + colorama.Back.RESET


def print_yellow(text):
    print colorama.Fore.LIGHTYELLOW_EX + colorama.Back.BLACK + text + colorama.Fore.RESET + colorama.Back.RESET


def print_red(text):
    print colorama.Fore.LIGHTRED_EX + colorama.Back.BLACK + text + colorama.Fore.RESET + colorama.Back.RESET


def approve_operation():
    if sys.version_info > (3, 0):
        _input = input
    else:
        _input = raw_input

    proceed = _input("Choose yes or no [y/N] ").lower() in ('y', 'yes')
    if not proceed:
        log_n_raise(logger, "user didn't confirm operation")


def approve_danger_op(message, arguments):
    if arguments['--yes'] is False:
        full_massage = "This Operations is considered dangerous!\nPlease Confirm: {}".format(message)
        log(logger, full_massage, level=WARNING, color="yellow")
        approve_operation()
