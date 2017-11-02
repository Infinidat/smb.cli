""" smbmgr v{version}
INFINIDAT SMB Cluster and exports manager

Usage:
    smbmgr fs create <size> --name=NAME [--mount=PATH] [--pool=POOL]
    smbmgr fs delete --name --yes
    smbmgr fs attach --name=NAME --pool=POOL_NAME [--mount=PATH]
    smbmgr fs detache
    smbmgr fs query
    smbmgr defaults set
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
from smb.cli.__version__ import __version__

def get_privileges_text():
    return colorama.Fore.RED + "This tool requires administrative privileges." + colorama.Fore.RESET


def commandline_to_docopt(argv):
    import os
    from colorama import init
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
        print colorama.Fore.RED + "Invalid Arguments" + colorama.Fore.RESET
        raise


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
            run_defaults_get()


def run_defaults_get():
    from smb.cli.defaults import defaults_get
    defaults_get()




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
