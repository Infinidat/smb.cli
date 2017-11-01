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

{privileges_text}


"""

# This piece of code is a modified version of powertools.cli __init__.py
import os
import sys
import docopt
from smb.cli.__version__ import __version__

def get_privileges_text():
    import colorama
    return colorama.Fore.RED + "This tool requires administrative privileges." + colorama.Fore.RESET


def shorten_docopt_exit_string(e):
    # shorten the usage lines printed by DocoptExit to include only lines that are relevant to the command
    # get all the command words in argv (ignore flags and the executable)
    argv = [word for word in sys.argv[1:] if not word.startswith('-') and word in __doc__]
    argv_len = len(argv)
    if argv_len == 0:
        return
    short_usage_lines = [line for line in e.usage.split("\n")
                         if line.split()[1:argv_len + 1] == argv]
    if len(short_usage_lines) > 0:
        # 'code' is inherited from SystemExit and it's what's printed to the screen
        # it may contain a message, and it contains the usage that we want to replace
        e.code = e.code[:e.code.find("Usage:\n")] + "Usage:\n" + "\n".join(short_usage_lines)


def parse_commandline_arguments(argv):
    from colorama import init
    global output_stream
    if 'TERM' not in os.environ:
        init()
    output_stream = sys.stdout
    doc = __doc__
    try:
        return docopt.docopt(doc.format(version=__version__,
                                        privileges_text=get_privileges_text(),
                                        prefix='nt').strip(),
                                        version=__version__, help=True, argv=argv)
    except docopt.DocoptExit as e:
        shorten_docopt_exit_string(e)
        raise


def in_cli(argv=sys.argv[1:]):
    arguments = parse_commandline_arguments(argv)
    # we import the engine script here because it contains many imports and may take time to load,
    # but we want the docopt check to run first, as fast as possible
    from .engine import run_command
    from infi.vendata.powertools.utils.broken_pipe import silence_broken_pipe_on_stdout_and_stderr
    import warnings
    with warnings.catch_warnings():
        import infinisdk  # noqa
    silence_broken_pipe_on_stdout_and_stderr()
    return run_command(arguments)


def pre_uninstall():
    from os import path
    from shutil import rmtree
    from infi.vendata.powertools import PROJECTROOT
    try:
        conf_dir = path.join(PROJECTROOT, 'conf')
        if path.exists(conf_dir):
            rmtree(conf_dir, ignore_errors=True)
    finally:
        return 0


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
