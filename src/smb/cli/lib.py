import sys
import infinisdk
import colorama
from os import path, pardir
from infi.credentials_store import CLICredentialsStore
from smb.cli.config import config_get
from infi.execute import execute_assert_success, execute
from smb.cli.smb_log import get_logger, log, log_n_exit
from logging import DEBUG, INFO, WARNING, ERROR
logger = get_logger()
from smb import PROJECTROOT


if sys.version_info > (3, 0):
    _input = input
else:
    _input = raw_input


class SMBCrdentialsStore(CLICredentialsStore):
    def _get_file_folder(self):
        return ".smb.credentials_store"

    def authenticate(self, key, credentials):
        import infinisdk
        from infinisdk.core.exceptions import APICommandFailed
        if credentials is None:
            return False
        config = config_get(silent=True)
        try:
            ibox = infinisdk.InfiniBox(config['IboxAddress'], auth=(credentials.get_username(), credentials.get_password()))
            ibox.login()
            return True
        except APICommandFailed:
            return False

    def ask_credentials_prompt(self, key):
        print 'Connecting to InfiniBox ' + str(key)


def initiate_store(store_name):
    crdentials_store = SMBCrdentialsStore("all_iboxes")
    return crdentials_store.get_credentials(store_name)


class PreChecks(object):
    def __init__(self):
        log(logger, "Running Prechecks...", level=INFO)
        InfiSdkObjects().get_ibox()
        self.is_cluster_online()
        self.am_I_master()

    def am_I_master(self):
        from platform import node
        config = config_get(silent=True)
        cmd = execute_assert_success(['powershell', '-c', 'Get-ClusterGroup', '-name', config['FSRoleName'], '|', 'Select-Object',
                                '-ExpandProperty', 'OwnerNode', '|', 'Select-Object', '-ExpandProperty', 'name'])
        if cmd.get_stdout().strip() == node():
            return True
        else:
            log_n_exit(logger, "The Node you are running on is NOT the Active Cluster Node")

    def is_cluster_online(self):
        config = config_get(silent=True)
        cmd = execute_assert_success(['powershell', '-c', 'Get-ClusterGroup', '-name', config['FSRoleName'], '|', 'Select-Object',
                                '-ExpandProperty', 'state'])
        if cmd.get_stdout().strip() != 'Online':
            log_n_exit(logger, "Cluster group {} NOT in Online state !! state is: {}".format(config['FSRoleName'], cmd.get_stdout().strip()))


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
            log_n_exit(logger, "Windows couldn't gain access to volume {} which was just mapped".format(volume.get_name()))


def _validate_size(size_str, roundup=False):
    import capacity
    from capacity import byte
    if size_str == '0' or size_str is None:
        return 0
    try:
        size = capacity.from_string(size_str)
        if size == capacity.Capacity(0):
            return 0
        if roundup:
            if (size / byte) / 512.0 != int((size / byte) / 512.0):
                size = ((int((size / byte) / 512) + 1) * 512) * byte
    except ValueError:
        log(logger, "{} is an invalid capacity ! Please try one of the following:\n".format(size_str) +
                         "<number> KB, KiB, MB, MiB, GB, GiB, TB, TiB... ", level=INFO, color="yellow")
        exit()
    return size


def get_path_free_size(full_path):
    ''' inspired by:
    http://code.activestate.com/recipes/577972-disk-usage/
    '''
    import ctypes
    import sys
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
    is_disk_in_cluster_script = path.realpath(path.join(PROJECTROOT, pardir, 'SMB-Cluster', 'src', 'DiskToClusterDiskResource.ps1'))
    output = execute(['powershell', '-c', '$Disk =' 'Get-Disk', '-Number', str(disk_win_id), ';',
                      '.', pad_text(is_disk_in_cluster_script), '-Disk', '$Disk'])
    if 'MSCluster' in output.get_stdout():
        return True
    else:
        return False


def pad_text(path):
    return "{}{}{}".format("'", path, "'")


def is_volume_mapped_to_cluster(volume, sdk):
    cluster = sdk.get_cluster()
    try:
        cluster.get_lun(volume)
    except:
        error = sys.exc_info()[1]
        return False
    return True


def get_privileges_text():
    return colorama.Fore.RED + "This tool requires administrative privileges." + colorama.Fore.RESET


def raise_invalid_argument():
    print colorama.Fore.RED + "Invalid Arguments" + colorama.Fore.RESET
    raise


def wait_for_ms_volume_removal(volume_name):
    from time import sleep
    from smb.cli import ps_cmd
    ps_cmd._run_remove_vol_from_cluster(volume_name)
    timeout = 10
    for i in range(10):
        vols_in_cluster = ps_cmd._check_if_vol_in_cluster(volume_name).splitlines()
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
    print colorama.Fore.GREEN + text + colorama.Fore.RESET


def print_yellow(text):
    print colorama.Fore.YELLOW + text + colorama.Fore.RESET


def print_red(text):
    print colorama.Fore.RED + text + colorama.Fore.RESET


def approve_danger_op(message, arguments):
    if arguments['--yes'] is False:
        full_massage = "This Operations is considered dangerous!\n Please Confirm {}".format(message)
        log(logger, full_massage, level=WARNING, color="yellow")
        proceed = _input("Would you like to proceed [y/N] ").lower() in ('y', 'yes', 'Y', 'YES')
        if not proceed:
            log(logger, "user didn't confirm danger op")
            exit()
    return


class InfiSdkObjects(object):
    def __init__(self):
        self.config = config_get(silent=True)
        self.ibox = self.ibox_login()

    def get_ibox(self):
        return self.ibox

    def get_local_config(self):
        return self.config

    def get_cluster(self):
        cluster = self.ibox.host_clusters.choose(name=self.config['Cluster'])
        return cluster

    def ibox_login(self):
        '''tries to connect using credintal store'''
        store = initiate_store(self.config['IboxAddress'])
        ibox = infinisdk.InfiniBox(str(self.config['IboxAddress']),
                                   auth=(store.get_username(), store.get_password()))
        response = ibox.login()
        if response.status_code == 200:
            return ibox
        else:
            log_n_exit(logger, "Couldn't connect to InfiniBox with current credentials")
