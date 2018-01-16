""" smbmgr v{version}
INFINIDAT SMB Cluster and exports manager

Usage:
    smbmgr fs create <size> --name=FSNAME [--pool=POOL_NAME]
    smbmgr fs delete --name=FSNAME [--yes]
    smbmgr fs attach --name=FSNAME [--yes] [--force]
    smbmgr fs detach --name=FSNAME [--yes]
    smbmgr fs query [--size_unit=UNIT]
    smbmgr share create --name=SHARENAME --path=PATH [--size=SIZE]
    smbmgr share delete --name=SHARENAME [--yes]
    smbmgr share resize <size> --name=SHARENAME [--yes]
    smbmgr share query
    smbmgr config set <key=value>
    smbmgr config get

Options:
    size                        Desired size in capacity units (examples: 10GB, 100MB, 1TB)
    --pool=POOL_NAME            Pool to provision/search vol on. Use "smbmgr config get/set" to View/Modify
    --size_unit=UNIT            Show sizes in specific format. UNIT can be (TB, TiB, GB, GiB, MB, MiB ,etc...)
    --force                     Continue on errors (not recommended !). Only for "fs attach"
    --yes                       Skip confirmation on dangers operations

Note:
    For removing share quota limit use 0 as size
    e.g.
    smbmgr share resize 0 --name=my_smb_share

{privileges_text}
"""

import sys
import docopt
from smb.cli import lib
from smb.cli.config import config_get, config_set
from smb.cli.__version__ import __version__


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
        lib.raise_invalid_argument()


def in_cli(argv=sys.argv[1:]):
    arguments = commandline_to_docopt(argv)
    arguments_to_functions(arguments)


def _use_default_config_if_needed(arguments):
    '''Set default values from config in case the user didn't put them.
    In our case only pool name and mount path '''
    config = config_get(silent=True)
    if not arguments['--pool']:
        arguments['--pool'] = config['PoolName']
    return arguments


def arguments_to_functions(arguments):
    from lib import PreChecks
    if not (arguments['query'] or arguments['config']):
        PreChecks()
    if arguments['fs']:
        arguments = _use_default_config_if_needed(arguments)
        if arguments['create']:
            run_fs_create(arguments)
        if arguments['delete']:
            run_fs_delete(arguments)
        if arguments['attach']:
            run_fs_attach(arguments)
        if arguments['detach']:
            run_fs_detach(arguments)
        if arguments['query']:
            run_fs_query(arguments)
    if arguments['share']:
        if arguments['create']:
            run_share_create(arguments)
        if arguments['query']:
            run_share_query(arguments)
        if arguments['resize']:
            run_share_resize(arguments)
        if arguments['delete']:
            run_share_delete(arguments)
    if arguments['config']:
        if arguments['get']:
            run_config_get()
        if arguments['set']:
            run_config_set(arguments)


def run_fs_query(arguments):
    from smb.cli.fs import fs_query
    fs_query(arguments['--size_unit'])


def run_fs_create(arguments):
    from smb.cli.fs import fs_create
    size = lib._validate_size(arguments['<size>'])
    fs_create(arguments['--name'], arguments['--pool'], size)


def run_fs_attach(arguments):
    from smb.cli.fs import fs_attach
    config = config_get(silent=True)
    lib.approve_danger_op("Adding volume {} to Cluster {}".format(arguments['--name'], config['Cluster']), arguments)
    fs_attach(arguments['--name'], arguments['--force'])

def run_share_query(arguments):
    from smb.cli.share import share_query
    share_query(arguments['--size_unit'])


def run_share_create(arguments):
    from smb.cli.share import share_create
    size = lib._validate_size(arguments['--size'])
    share_create(arguments['--name'], arguments['--path'], size)


def run_share_resize(arguments):
    from smb.cli.share import share_limit, share_unlimit
    lib.approve_danger_op("Size limiting to share {}".format(arguments['--name']), arguments)
    size = lib._validate_size(arguments['<size>'])
    if size != 0:
        share_limit(arguments['--name'], size)
        exit()
    share_unlimit(arguments['--name'])


def run_share_delete(arguments):
    from smb.cli.share import share_delete
    lib.approve_danger_op("Completely DELETE share {}".format(arguments['--name']), arguments)
    share_delete(arguments['--name'])


def run_config_get():
    config_get()


def run_config_set(arguments):
    import colorama
    print "Current Config:",
    config = config_get()
    if config is None:
        exit()
    key, value = arguments.get('<key=value>', "").split("=")
    config_case_sensitive = {item.lower(): item for item in config.keys()}
    if key.lower() in config_case_sensitive.keys():
        config_set(config_case_sensitive[key.lower()], value)
        print colorama.Fore.GREEN + "New Config:",
        config_get()
        print colorama.Fore.RESET
    else:
        lib.print_red("{} is not valid for your config".format(key))
        exit()
