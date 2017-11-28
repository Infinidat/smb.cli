""" smbmgr v{version}
INFINIDAT SMB Cluster and exports manager

Usage:
    smbmgr fs create <size> --name=NAME [--mount=PATH] [--pool=POOL]
    smbmgr fs delete --name=NAME [--yes]
    smbmgr fs attach --name=NAME [--yes] [--pool=POOL_NAME] [--mount=PATH]
    smbmgr fs detache [--yes]
    smbmgr fs query
    smbmgr config set <key=value>
    smbmgr config get

Options:
    <size>                      desired volume size (examples: 10gb, 100mb, 1tb)
    --mount=PATH                mount path to the volume. View/change default using "smbmgr config get/set"
    --pool=POOL_NAME            pool to provision/search volume on. View/change default using "smbmgr config get/set"
    --yes                       skip prompt on dangers operations

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
    from lib import precheck
    if not (arguments['query'] or arguments['config']):
        precheck()
    if arguments['fs']:
        arguments = _use_default_config_if_needed(arguments)
        if arguments['create']:
            run_fs_create(arguments)
        if arguments['delete']:
            run_fs_delete()
        if arguments['attach']:
            run_fs_attach(arguments)
        if arguments['detache']:
            run_fs_detache()
        if arguments['query']:
            run_fs_query()
    if arguments['config']:
        if arguments['get']:
            run_config_get()
        if arguments['set']:
            run_config_set(arguments)


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
    from smb.cli.fs import create_volume_on_infinibox, fs_create
    volume = create_volume_on_infinibox(arguments['--name'], arguments['--pool'], arguments['<size>'])
    fs_create(volume)


def run_fs_attach(arguments):
    from smb.cli.fs import _validate_vol, map_vol_to_cluster
    config = config_get(silent=True)
    ibox = lib.connect()
    volume = _validate_vol(ibox, vol_name=arguments['--name'])
    lib.approve_danger_op("Adding volume {} to Cluster {}".format(arguments['--name'], config['Cluster']), arguments)
    map_vol_to_cluster(volume)
    lib.exit_if_vol_not_mapped(volume)


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
