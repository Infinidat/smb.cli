""" smbmgr v{version}
INFINIDAT SMB Cluster and exports manager

Usage:
    smbmgr fs create <size> --name=NAME [--mount=PATH] [--pool=POOL]
    smbmgr fs delete --name --yes
    smbmgr fs attach --name=NAME --pool=POOL_NAME [--mount=PATH]
    smbmgr fs detache
    smbmgr fs query
    smbmgr defaults set <key=value>
    smbmgr defaults get

Options:
    <size>                      desired volume size (examples: 10gb, 100mb, 1tb)
    --mount=PATH                mount path to the volume. View/change default using "smbmgr defaults get/set"
    --pool=POOL_NAME            pool to provision/search volume on. View/change default using "smbmgr defaults get/set"

{privileges_text}
"""

import sys
import docopt
from smb.cli import lib
from smb.cli.defaults import defaults_get, defaults_set
from smb.cli.__version__ import __version__


def commandline_to_docopt(argv):
    import os
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
    import warnings
    arguments = commandline_to_docopt(argv)
    with warnings.catch_warnings():
        import infinisdk
    arguments_to_functions(arguments)

def _use_default_config_if_needed(arguments):
    '''Set default values from config in case the user didn't put them.
    In our case only pool name and mount path '''
    config = defaults_get(silent=True)
    if not arguments['--pool']:
        arguments['--pool'] = config['PoolName']
    if not arguments['--mount']:
        arguments['--mount'] = config['MountRoot']
    return arguments

def arguments_to_functions(arguments):
    if arguments['fs']:
        arguments = _use_default_config_if_needed(arguments)
        if arguments['create']:
            run_fs_create(arguments)
        if arguments['delete']:
            run_fs_delete()
        if arguments['attach']:
            run_fs_attach()
        if arguments['detache']:
            run_fs_detache()
        if arguments['query']:
            run_fs_query()
    if arguments['defaults']:
        if arguments['get']:
            run_defaults_get()
        if arguments['set']:
            run_defaults_set(arguments)


def run_defaults_get():
    defaults_get()

def run_defaults_set(arguments):
    import colorama
    print "Current Config:",
    config = defaults_get()
    key, value = arguments.get('<key=value>', "").split("=")
    config_case_sensitive = {item.lower():item for item in config.keys()}
    if key.lower() in config_case_sensitive.keys():
        defaults_set(config_case_sensitive[key.lower()] ,value)
        print colorama.Fore.GREEN + "New Config:",
        defaults_get()
        print colorama.Fore.RESET
    else:
        lib.print_red("{} is not valid for your config".format(key))
        exit()

def run_fs_create(arguments):
    from smb.cli.fs import vol_create
    vol_create(arguments['--name'], arguments['--pool'], arguments['<size>'])



# Need more validations to all CLI commands
# pool exists and has enough space
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
#vol_create
#vol_map
#vol_to_mountpoint.ps1  get mapped vol and mkfs + map + adds to Cluster
#
