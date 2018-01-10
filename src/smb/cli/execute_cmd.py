import sys
from smb.cli import lib
from infi.execute import execute_assert_success

def run(cmd, error_prefix):
    try:
        result = execute_assert_success(cmd)
        return result.get_stdout()
    except:
        error = sys.exc_info()[1]
        lib.print_red("{} {}".format(error_prefix, error))
        exit()
