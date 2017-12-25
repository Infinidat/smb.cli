import sys
import infinisdk
import colorama
from infi.credentials_store import CLICredentialsStore
from smb.cli.config import config_get

if sys.version_info > (3, 0):
    _input = input
else:
    _input = raw_input


class SMBCrdentialsStore(CLICredentialsStore):
    def _get_file_folder(self):
        return ".smb.credentials_store"

    def authenticate(self, key, credentilas):
        return True

    def ask_credentials_prompt(self, key):
        print 'Connecting to InfiniBox ' + str(key)


def initiate_store(store_name):
    crdentials_store = SMBCrdentialsStore("all_iboxes")
    return crdentials_store.get_credentials(store_name)


class PreChecks(object):
    def __init__(self):
        print "Running Prechecks..."
        InfiSdkObjects().get_ibox()
        self.is_cluster_online()
        self.am_I_master()

    def am_I_master(self):
        from infi.execute import execute_assert_success
        from platform import node
        config = config_get(silent=True)
        cmd = execute_assert_success(['powershell', '-c', 'Get-ClusterGroup', '-name', config['FSRoleName'], '|', 'Select-Object',
                                '-ExpandProperty', 'OwnerNode', '|', 'Select-Object', '-ExpandProperty', 'name'])
        if cmd.get_stdout().strip() == node():
            return True
        else:
            print_red("The Node you are running on is NOT the Active Cluster Node")
            exit()

    def is_cluster_online(self):
        from infi.execute import execute_assert_success
        config = config_get(silent=True)
        cmd = execute_assert_success(['powershell', '-c', 'Get-ClusterGroup', '-name', config['FSRoleName'], '|', 'Select-Object',
                                '-ExpandProperty', 'state'])
        if cmd.get_stdout().strip() != 'Online':
            print_red("Cluster group {} NOT in Online state !! state is: {}".format(config['FSRoleName'], cmd.get_stdout().strip()))
            exit()


def exit_if_vol_not_mapped(volume):
    ''' receives an infinisdk volume type and checks if mapped'''
    def _is_vol_mapped(volume_serial, timeout=3):
        from time import sleep
        from infi.execute import execute_assert_success
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
        from os import path, pardir
        from infi.execute import execute
        from smb import PROJECTROOT
        HPT_BIN_FILE = 'infinihost.exe'
        # to do need to think if we'd like to scan on remote and verify
        hpt_bin = path.realpath(path.join(PROJECTROOT, pardir, 'Host Power Tools', 'bin', HPT_BIN_FILE))
        execute([hpt_bin, 'rescan'])

    if not _is_vol_mapped(volume.get_serial()):
        _rescan()
        if not _is_vol_mapped(volume.get_serial()):
            print_red("Windows couldn't gain access to volume {} which was just mapped".format(volume.get_name()))
            exit()

def is_volume_mapped_to_cluster(volume):
    config = config_get(silent=True)
    ibox = volume.get_system()
    cluster = ibox.host_clusters.choose(name=config['Cluster'])
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
        print_yellow("You are going to perform: {}".format(message))
        print_yellow("This Operations is considered dangerous!")
        proceed = _input("Would you like to proceed [y/N] ").lower() in ('y', 'yes', 'Y', 'YES')
        if not proceed:
            exit()
    return

class InfiSdkObjects(object):
    def __init__(self):
        self.config = config_get(silent=True)

    def get_local_config(self):
        return self.config

    def get_cluster(self):
        ibox = self.get_ibox()
        cluster = ibox.host_clusters.choose(name=self.config['Cluster'])
        return cluster

    def get_ibox(self):
        '''tries to connect using credintal store'''
        store = initiate_store(self.config['IboxAddress'])
        ibox = infinisdk.InfiniBox(str(self.config['IboxAddress']),
                                   auth=(store.get_username(), store.get_password()))
        response = ibox.login()
        if response.status_code == 200:
            return ibox
        else:
            print_red("Couldn't connect to InfiniBox with current credentials")
            exit()
