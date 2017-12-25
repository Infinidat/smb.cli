""" smbmgr v{version}
INFINIDAT SMB Cluster and exports manager

Usage:
    smbmgr fs create <size> --name=NAME [--mount=PATH] [--pool=POOL]
    smbmgr fs delete --name=NAME [--yes]
    smbmgr fs attach --name=NAME [--mount=PATH] [--yes] [--force]
    smbmgr fs detach --name=NAME    [--yes]
    smbmgr fs query [--size_unit=UNIT]
    smbmgr config set <key=value>
    smbmgr config get

Options:
    <size>                      desired volume size (examples: 10GB, 100MB, 1TB)
    --mount=PATH                mount path to the volume. View/change default using "smbmgr config get/set"
    --pool=POOL_NAME            pool to provision/search volume on. View/change default using "smbmgr config get/set"
    --yes                       skip prompt on dangers operations
    --force                     Continue on errors (not recommended !). Only for "fs attach"
    --size_unit=UNIT            Show sizes in specific format. UNIT can be (TB, TiB, GB, GiB, MB, MiB ,etc...)
    --skip

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
    if not arguments['--mount']:
        arguments['--mount'] = config['MountRoot']
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
            run_fs_delete()
        if arguments['attach']:
            run_fs_attach(arguments)
        if arguments['detach']:
            run_fs_detach()
        if arguments['query']:
            run_fs_query(arguments)
    if arguments['config']:
        if arguments['get']:
            run_config_get()
        if arguments['set']:
            run_config_set(arguments)



def run_fs_query(arguments):
    from smb.cli.fs import fs_query
    fs_query(arguments['--size_unit'])

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


def run_fs_create(arguments):
    from smb.cli.fs import fs_create
    fs_create(arguments['--name'],arguments['--mount'], arguments['--pool'], arguments['<size>'])


def run_fs_attach(arguments):
    from smb.cli.fs import fs_attach
    config = config_get(silent=True)
    lib.approve_danger_op("Adding volume {} to Cluster {}".format(arguments['--name'], config['Cluster']), arguments)
    fs_attach(arguments['--name'], arguments['--mount'], arguments['--force'])


# Need more validations to all CLI commands
# volume name isn't duplicate
# Cluster exists and host is part of cluster
#
#- create volume
#- map volume
#- verify mapping
#- add to Cluster
#- export
#
#
#create_volume_on_infinibox
#vol_map
#vol_to_mountpoint.ps1  get mapped vol and mkfs + map + adds to Cluster
#
