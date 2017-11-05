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
    --mount=PATH                mount path [default: XXXX]
    --pool=POOL_NAME            pool to provision on default is taken from XXX

{privileges_text}
"""

import sys
import docopt
import colorama
from smb.cli.defaults import defaults_get
from smb.cli.__version__ import __version__

def get_privileges_text():
    return colorama.Fore.RED + "This tool requires administrative privileges." + colorama.Fore.RESET


def raise_invalid_argument():
    from colorama import init
    print colorama.Fore.RED + "Invalid Arguments" + colorama.Fore.RESET
    raise

def commandline_to_docopt(argv):
    import os
    global output_stream
    if 'TERM' not in os.environ:
        init()
    output_stream = sys.stdout
    doc = __doc__
    try:
        return docopt.docopt(doc.format(version=__version__,
                                        privileges_text=get_privileges_text()).strip(),
                                        version=__version__, help=True, argv=argv)
    except docopt.DocoptExit as e:
        raise_invalid_argument()


def in_cli(argv=sys.argv[1:]):
    import warnings
    arguments = commandline_to_docopt(argv)
    with warnings.catch_warnings():
        import infinisdk
    arguments_to_functions(arguments)


def arguments_to_functions(arguments):
    if arguments['fs']:
        if arguments['create']:
            run_fs_create()
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
    from smb.cli.defaults import defaults_set
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
        colorama.Fore.RED + "{} is not valid for your config".format(key) + colorama.Fore.RESET
        exit()


#- create volume
#- map volume
#- verify mapping
#- add to Cluster
#- export
#
#
#vol_create
#vol_map
#vol_to_mount.ps1 point get mapped vol and mkfs + map + adds to Cluster
#
