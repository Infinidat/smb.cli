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


def approve_danger_op(message, arguments):
    if arguments['--yes'] is False:
        print_yellow("You are going to perform: {}".format(message))
        print_yellow("This Operations is considered dangerous!")
        proceed = _input("Would you like to proceed [y/N]").lower() in ('y', 'yes', 'Y', 'YES')
        if not proceed:
            exit()
    return

def exit_if_vol_not_mapped(volume):
    ''' receives an infinisdk volume type and checks if mapped'''

    def _is_vol_mapped(volume_serial, timeout=3):
        from infi.storagemodel import get_storage_model
        from time import sleep
        storagemodel = get_storage_model()
        multipath = storagemodel.get_native_multipath()
        for n in range(1, timeout + 1):
            storagemodel.rescan_and_wait_for(timeout_in_seconds=3)
            mapped_vols = multipath.get_all_multipath_block_devices()
            for vol in mapped_vols:
                if str(vol.get_scsi_serial_number()) == volume.get_serial():
                    return True
            sleep(1)
        return False

    if not _is_vol_mapped(volume.get_serial()):
        print_red("Windows couldn't gain access to volume {} which was just mapped".format(volume.get_name()))
        exit()

def initiate_store(store_name):
    crdentials_store = SMBCrdentialsStore("all_iboxes")
    return crdentials_store.get_credentials(store_name)

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

def connect():
    '''tries to connect using credintal store'''
    config = config_get(silent=True)
    store = initiate_store(config['IboxAddress'])
    ibox = infinisdk.InfiniBox(str(config['IboxAddress']),
                               auth=(store.get_username(), store.get_password()))
    response = ibox.login()
    if response.status_code == 200:
        return ibox
    else:
        print "Couldn't connect with current credentials"
        exit()
