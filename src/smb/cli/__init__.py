""" smbmgr v{version}
INFINIDAT SMB Cluster, exports and quotas manager

Usage:
    smbmgr fs create --size=SIZE --name=FSNAME [--pool=POOL_NAME]
    smbmgr fs delete --name=FSNAME [--yes]
    smbmgr fs attach --name=FSNAME [--yes] [--force]
    smbmgr fs detach --name=FSNAME [--yes]
    smbmgr fs query [--size_unit=UNIT] [-d]
    smbmgr share create --name=SHARENAME --path=PATH [--mkdir] [--size=SIZE]
    smbmgr share delete --name=SHARENAME [--yes]
    smbmgr share resize --size=SIZE --name=SHARENAME [--yes]
    smbmgr share query [--size_unit=UNIT] [-d]
    smbmgr config set <key=value>
    smbmgr config get

Options:
    --size=SIZE                 Desired size in capacity units (examples: 10GB, 100MB, 1TB)
    --pool=POOL_NAME            Pool to provision/search vol on. Use "smbmgr config get/set" to View/Modify
    --size_unit=UNIT            Show sizes in specific format rounded down. UNIT can be (TB, TiB, GB, GiB, etc...)
    --mkdir                     Create share dir if doesn't exist
    --force                     Continue on errors (not recommended !). Only for "fs attach"
    --yes                       Skip confirmation on dangers operations
    -d --detailed               Print names without truncating them

Note:
    For removing share quota limit use --size=0
    Example:
    smbmgr share resize --size=0 --name=my_smb_share

{privileges_text}
"""
import traceback
from smb.cli.smb_log import get_logger, log, log_n_exit
from logging import DEBUG, INFO, WARNING, ERROR
logger = get_logger()
try:
    log(logger, "Importing module")
    import sys
    import docopt
    from smb.cli import lib
    from smb.cli.config import config_get, config_set
    from smb.cli.__version__ import __version__
    sdk = lib.InfiSdkObjects()
    config = sdk.get_local_config()
except KeyboardInterrupt:
    log(logger, "Keyboard break recived, exiting")
    exit()

def commandline_to_docopt(argv):
    global output_stream
    lib._init_colorama()
    output_stream = sys.stdout
    doc = __doc__
    try:
        return docopt.docopt(doc.format(version=__version__,
                                        privileges_text=lib.get_privileges_text()).strip(),
                                        version=__version__, help=True, argv=argv)
    except docopt.DocoptExit as e:
        log(logger, e, level=INFO, raw=True)
        log_n_exit(logger, "Invalid Arguments")


def in_cli(argv=sys.argv[1:]):
    try:
        arguments = commandline_to_docopt(argv)
        arguments_to_functions(arguments)
    except KeyboardInterrupt:
        log(logger, "Keyboard break recived, exiting")
        exit()


def _use_default_config_if_needed(arguments):
    '''Set default values from config in case the user didn't put them.
    In our case only pool name and mount path '''
    config = config_get(silent=True)
    if not arguments['--pool']:
        arguments['--pool'] = config['PoolName']
    return arguments


def arguments_to_functions(arguments):
    from lib import PreChecks
    log(logger, "Arguments received from user:{}".format(arguments))
    if not arguments['config']:
        PreChecks()
    try:
        if arguments['fs']:
            arguments = _use_default_config_if_needed(arguments)
            if arguments['create']:
                run_fs_create(arguments, sdk)
            if arguments['delete']:
                run_fs_delete(arguments, sdk)
            if arguments['attach']:
                run_fs_attach(arguments, sdk)
            if arguments['detach']:
                run_fs_detach(arguments, sdk)
            if arguments['query']:
                run_fs_query(arguments, sdk)
        if arguments['share']:
            if arguments['create']:
                run_share_create(arguments, sdk)
            if arguments['query']:
                run_share_query(arguments, sdk)
            if arguments['resize']:
                run_share_resize(arguments)
            if arguments['delete']:
                run_share_delete(arguments)
        if arguments['config']:
            if arguments['get']:
                run_config_get()
            if arguments['set']:
                run_config_set(arguments, sdk)
    except KeyboardInterrupt:
        log(logger, "Keyboard break recived, exiting")
        exit()
    except Exception as e:
        log(logger, traceback.format_exc())
        message = '''{} \n(This is Unusual)
Please collect the Logs from "{}" and contact Infinidat Support'''
        log_n_exit(logger, message.format(e, logger.handlers[0].baseFilename))

def run_fs_query(arguments, sdk):
    from smb.cli.fs import fs_query
    fs_query(arguments['--size_unit'], sdk, arguments['--detailed'])


def run_fs_create(arguments, sdk):
    from smb.cli.fs import fs_create
    size = lib._validate_size(arguments['--size'], roundup=True)
    fs_create(arguments['--name'], arguments['--pool'], size, sdk)


def run_fs_attach(arguments, sdk):
    from smb.cli.fs import fs_attach
    config = config_get(silent=True)
    lib.approve_danger_op("Adding volume {} to Cluster {}".format(arguments['--name'], config['Cluster']), arguments)
    log(logger, "calling {}")
    fs_attach(arguments['--name'], sdk, arguments['--force'])


def run_fs_detach(arguments, sdk):
    from smb.cli.fs import fs_detach
    lib.approve_danger_op("Detaching Filesystem {} from Cluster {}".format(arguments['--name'], config['Cluster']), arguments)
    fs_detach(arguments['--name'], sdk)


def run_fs_delete(arguments, sdk):
    from smb.cli.fs import fs_delete
    lib.approve_danger_op("Deleting Filesystem {} completely. NO WAY BACK!".format(arguments['--name']), arguments)
    fs_delete(arguments['--name'], sdk)


def run_share_query(arguments, sdk):
    from smb.cli.share import share_query
    share_query(arguments['--size_unit'], sdk, arguments['--detailed'])


def run_share_create(arguments, sdk):
    from smb.cli.share import share_create
    size = lib._validate_size(arguments['--size'], roundup=True)
    share_create(arguments['--name'], arguments['--path'], arguments['--mkdir'], size, sdk)


def run_share_resize(arguments):
    from smb.cli.share import share_limit, share_unlimit
    size = lib._validate_size(arguments['--size'], roundup=True)
    if size != 0:
        lib.approve_danger_op("Size limiting to share {}".format(arguments['--name']), arguments)
        share_limit(arguments['--name'], size)
        exit()
    share_unlimit(arguments['--name'])


def run_share_delete(arguments):
    from smb.cli.share import share_delete
    lib.approve_danger_op("Completely DELETE share {}".format(arguments['--name']), arguments)
    share_delete(arguments['--name'])


def run_config_get():
    config_get()


def run_config_set(arguments, sdk):
    import colorama
    log(logger, "Current Config:", raw=True)
    config = config_get()
    if config is None:
        exit()
    key, value = arguments.get('<key=value>', "").split("=")
    config_case_sensitive = {item.lower(): item for item in config.keys()}
    if key.lower() in config_case_sensitive.keys():
        config_set(config_case_sensitive[key.lower()], value, sdk)
        log(logger, "New Config:", level=INFO)
        config_get()
    else:
        log(logger,"{} is not valid for your config".format(key), color="red", raw=True)
        exit()
