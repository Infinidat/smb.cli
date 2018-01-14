from capacity import *
from smb.cli import lib
from smb.cli.execute_cmd import run
from smb.cli.lib import InfiSdkObjects
config = InfiSdkObjects().get_local_config()

''' Share objects and values returned from get_all_shares_data:
    Disabled = "True" / "False" as strings
    share_name = string containigs
    Softlimit = int
    Usage = int
    path = path to share in lowercase (normcase)
    size = int
    freeonfs
'''

def _print_format(val, val_type):
    def _trim_or_fill(val, lenght):
        if len(val) == lenght:
            return val
        if len(val) > lenght:
            return val[0:(lenght - 3)] + "..."
        if len(val) < lenght:
            return val.ljust(lenght - 1)

    def _val_to_print(val, val_type):
        if val_type in ["fsname", "sharename"]:
            lenght = 15
            return _trim_or_fill(val, lenght)
        if val_type == "path":
            lenght = 25
            return _trim_or_fill(val, lenght)
        else:
            lenght = 12
            return _trim_or_fill(val, lenght)
    return _val_to_print(str(val), val_type)

def print_share_query(shares):
    header = 'FSName         ShareName      Path                     Quota       UsedQuota   FilesystemFree'
    print header
    for share in shares:
        if share['Disabled'] == "True":
            quota = "-"
            usedquota = "-"
        else:
            quota = share['size']
            usedquota = share['Usage']
        line = [_print_format(share['fsname'], 'fsname'),
                _print_format(share['share_name'], 'sharename'),
                _print_format(share['path'], 'path'),
                _print_format(quota, 'quota'),
                _print_format(usedquota, 'usedQuota'),
                _print_format(share['freeonfs'], 'filesystemfree')]
        print " ".join(line)


def _run_share_create(share_name, share_path):
    cmd = ['powershell', '-c', 'New-SmbShare', '-Name', lib.pad_text(share_name),
           '-Path', lib.pad_text(share_path), '-ScopeName', config['FSRoleName'],
           '-ContinuouslyAvailable:$true', '-CachingMode', 'None']
    error_prefix = "New-SmbShare failed with error:"
    run(cmd, error_prefix)


def _run_share_delete(share_name):
    cmd = ['powershell', '-c', 'Remove-SmbShare', '-Name', lib.pad_text(share_name),
                                '-ScopeName', config['FSRoleName'], '-Confirm:$False']
    error_prefix = "Remove-SmbShare failed with error:"
    run(cmd, error_prefix)


def _run_share_query():
    cmd = ['powershell', '-c', 'Get-SmbShare', '-ScopeName', config['FSRoleName'],
           '|', 'Format-Custom', 'Name, Path']
    error_prefix = "Get-SmbShare failed with error:"
    return run(cmd, error_prefix)


def _run_share_quota_get():
    cmd = ['powershell', '-c', 'Get-FSRMQuota', '|', 'Select-Object',
           'Path, Disabled, size, Usage, Softlimit', '|', 'Format-Custom']
    error_prefix = "Get-SmbShare failed with error:"
    return run(cmd, error_prefix)


def _run_share_limit_set_default(share_path):
    # This can be always set over and over from any state
    cmd = ['powershell', '-c', 'New-FSRMQuota', '-Path', lib.pad_text(share_path), '-Size 1KB', '-Disabled']
    error_prefix = "New-FSRMQuota failed with error:"
    run(cmd, error_prefix)


def _run_share_limit_set(share_path, size):
    cmd = ['powershell', '-c', 'Set-FSRMQuota', '-Path', lib.pad_text(share_path), '-Size', size, '-Disabled:$False']
    error_prefix = "Set-FSRMQuota failed with error:"
    run(cmd, error_prefix)


def _run_share_limit_delete(share_path):
    # This can be always set over and over from any state
    cmd = ['powershell', '-c', 'Remove-FSRMQuota', '-Path', lib.pad_text(share_path), '-Confirm:$False']
    error_prefix = "Remove-FSRMQuota failed with error:"


def _get_share_limit_to_dict():
    import re
    from os import path
    shares_quota = []
    output = _run_share_quota_get()
    output = output.replace('class CimInstance', '')
    output = output.replace('\r', '').replace('{', '###').replace('}', '###')
    for share in output.split('###'):
        share_dict = {}
        for entity in share.splitlines():
            regex = re.compile(r'(?P<key>\w+)\ \=\ (?P<val>.+)')
            if re.search(regex, entity):
                d = re.search(regex, entity).groupdict()
                share_dict[d['key']] = d['val']
        if share_dict != {}:
            shares_quota.append(share_dict)
    for share in shares_quota:
        share['path'] = path.normcase(path.realpath(share['Path']))
        share['Usage'] = (int(share['Usage']) / 1024) * KiB
        share['size'] = (int(share['size']) / 1024) * KiB
    return shares_quota


def _share_query_to_dict():
    #  Run Get-SmbShare and pars it to list of dicts contains share name and path
    import re
    from os import path
    shares = []
    output = _run_share_query()
    output = output.replace('class CimInstance#ROOT/Microsoft/Windows/SMB/MSFT_SmbShare', '')
    output = output.replace("\r", "").replace('{', "###").replace('}', "###")
    share_list = output.split("###")
    for string in share_list:
        if 'Name =' in string:
            regex = re.compile(r'Name = (?P<share_name>.+)\n.*Path = (?P<path>.+)\n')
            result = re.search(regex, string).groupdict()
            if '$' in result['share_name']:
                #  Skip Hidden shares
                continue
            if result:
                result['path'] = path.normcase(result['path'])
                shares.append(result)
    return shares

def _merge_share_dicts(d1, d2):
    ''' Marge 2 share dicts and remove duplicate value: Path if exist
    '''
    d = d1.copy()
    d.update(d2)
    if 'Path' in d:
        d.pop('Path')
    return d

def get_all_shares_data():
    shares_list = []
    shares = _share_query_to_dict()
    quotas = _get_share_limit_to_dict()
    for share in shares:
        for quota in quotas:
            if share['path'] == quota['path']:
                shares_list.append(_merge_share_dicts(share, quota))
                break
    return shares_list


def join_fs_and_share(filesystems, shares):
    share_list = []
    for filesystem in filesystems:
        for share in shares:
            if filesystem['mount'] in share['path']:
                share_list.append(_merge_share_dicts(filesystem, share))
    return share_list


def share_query(arguments):
    from smb.cli.fs import _get_all_fs
    shares_data = get_all_shares_data()
    filesystems_data = _get_all_fs()
    shares = join_fs_and_share(filesystems_data, shares_data)
    for share in shares:
        share['freeonfs'] = lib.get_path_free_size(share['path'])['avail'] * KiB
    if len(shares) == 0:
        print "No Share Are Defined"
        exit()
    print_share_query(shares)

def _share_create_prechecks(share_name, share_path):
    from os import path
    from smb.cli.fs import _get_all_fs
    existing_shares = get_all_shares_data()
    MAX_PATH_LENTH = 120  # max share char because we are parsing output this might be a problem
    vaild_fs = False
    full_path = path.normcase(path.realpath(share_path))
    if not path.exists(full_path):
        lib.print_yellow("Path: {} doesn't exist".format(full_path))
        exit()
    if len(full_path) > MAX_PATH_LENTH:
        lib.print_yellow("Path length is to long. path length of {} characters is currently supported")
        exit()
    for share in existing_shares:
        if share['share_name'] == share_name:
            lib.print_yellow("Share Name Conflict ! {} Share Name Exists".format(share_name))
            exit()
        if path.realpath(share['path']) == full_path:
            lib.print_yellow("'{}' is Already Shared, Lucky You ?!".format(share_path))
            exit()
    filesystems = _get_all_fs()
    for filesystem in filesystems:
        if filesystem['mount'] in full_path:
            vaild_fs = True
            if lib.is_disk_in_cluster(filesystem['winid']) is False:
                lib.print_yellow("{} isn't part of the SMB Cluster".format(full_path))
                exit()
    if vaild_fs is False:
        lib.print_yellow("{} is NOT a valid share path".format(full_path))
        exit()
    return full_path


def find_share_from_list_of_shares(share_list, share_name=None, share_path=None):
    '''Given share list and  share name or share path, returns the relevant share
    '''
    if share_name:
        for share in share_list:
            if share['share_name'] == share_name:
                return share
    if share_path:
        for share in share_list:
            if share['Path'] == share_path:
                return share


def _share_limit_prechecks_and_set(share_name, size):
    from smb.cli.__version__ import __version__
    # TODO: check max vol size and make sure limit isn't bigger then it (GregT)
    shares = get_all_shares_data()
    shares_paths = [share['path'] for share in shares]
    share = find_share_from_list_of_shares(shares, share_name=share_name)
    if share['Disabled'] == "False":
        print "{} is Already Size Limited, Changing Size to {}".format(share_name, size)
        _run_share_limit_set(share['path'], size)
        exit()
    if share['path'] in shares_paths:
        for s in shares:
            if s['path'] in share['path'] or share['path'] in s['path']:
                if s['Disabled'] == "False":
                    lib.print_yellow("Recursive Size Limit is NOT Supported in {}".format(__version__))
                    lib.print_yellow("New Limit {} Conflicts with {}".format(share['path'], s['path']))
                    exit()
    _run_share_limit_set(share['path'], size)


def share_create(share_name, share_path, size_str):
    if size_str:
        size = lib._validate_size(size_str, roundup=True)
    if share_path[-1] in ["'", '"']:
        # Fix Dir path ends with \ e.g. "c:\dir\" didn't work. \" removed last "
        share_path = share_path[0:-1]
    _share_create_prechecks(share_name, share_path)
    _run_share_create(share_name, share_path)
    lib.print_green("'{}' Share Created".format(share_name))
    if size_str is None:
        _run_share_limit_set_default(share_path)
        exit()
    share_limit(share_path, size)


def share_limit(share_name, size):
    size = lib._validate_size(size_str, roundup=True)
    _share_limit_prechecks_and_set(share_name, size)
    lib.print_green("{} limited to {}".format(share_name, size))


def share_unlimit(share_name):
    shares = get_all_shares_data()  # Slow everything down maybe can removed.
    share = find_share_from_list_of_shares(shares, share_name=share_name)
    if shares['Disabled'] == "True":
        lib.print_yellow("{} doesn't have a limit on it.".format(share['share_name']))
        exit()
    _run_share_limit_set_default(share['path'])
    lib.print_green("{} size limit removed".format(share['share_name']))


def share_delete(share_name):
    shares = get_all_shares_data()
    share = find_share_from_list_of_shares(shares, share_name)
    if share is None:
        lib.print_yellow("{} Doesn't exist. Can't delete it... ".format(share_name))
    _run_share_limit_delete(share['path'])
    _run_share_delete(share_name)
    lib.print_green("{} Deleted".format(share_name))
