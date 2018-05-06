from capacity import *
from smb.cli import lib, ps_cmd
from smb.cli.fs import _get_all_fs
from smb.cli.smb_log import get_logger, log, log_n_raise
from logging import DEBUG, INFO, WARNING, ERROR
logger = get_logger()

class Share(object):
    def __init__(self, sharename=None, sharepath=None, disabled=None, usage=None, size=None, freeonfs=None, fs=None):
        self.name = sharename
        self.path = sharepath
        self.disabled = disabled
        self.usage = usage
        self.size = size
        self.freeonfs = freeonfs
        self.fs = fs

    def __eq__(self, other):
        return isinstance(other, Share) and self.path == other.get_path()

    def get_path(self):
        return self.path

    def get_name(self):
        return self.name

    def is_limited(self):
        if self.disabled == "True":
            return False
        if self.disabled == "False":
            return True
        return

    def get_usage(self):
        return self.usage

    def get_size(self):
        return self.size

    def get_free_space(self):
        return self.freeonfs

    def get_fs(self):
        return self.fs


def _print_format(val, val_type):
    def _trim_or_fill(val, lenght):
        if len(val) == lenght:
            return val + " "
        if len(val) > lenght:
            return val[0:(lenght - 3)] + "... "
        if len(val) < lenght:
            return val.ljust(lenght + 1)

    def _val_to_print(val, val_type):
        if val_type in ["fsname", "sharename"]:
            lenght = 15
        elif val_type == "path":
            lenght = 25
        else:
            lenght = 12
        return _trim_or_fill(val, lenght)
    return _val_to_print(str(val), val_type)


def print_share_query(shares, units, detailed=False):
    header = 'ShareName       FSName          Path                      Quota        UsedQuota    FilesystemFree'
    log(logger, header, level=INFO, raw=True)
    for share in shares:
        filesystemfree = share.get_free_space()
        quota = share.get_size()
        usedquota = share.get_usage()
        if units:
            quota = str(quota / units) + " " + str(units)[2:]
            usedquota = str(usedquota / units) + " " + str(units)[2:]
            filesystemfree = str(share.get_free_space() / units) + " " + str(units)[2:]
        if None in [quota, share.get_free_space(), usedquota]:
            fsname = "**INVALID**"
        else:
            fsname = share.fs['fsname']
        if share.is_limited() is False:
            quota = "-"
            usedquota = "-"
        if detailed:
            line = ["{}: {}".format('sharename', share.get_name()),
                    "{}: {}".format('fsname', fsname),
                    "{}: {}".format('path', share.get_path()),
                    "{}: {}".format('quota', quota),
                    "{}: {}".format('usedQuota', usedquota),
                    "{}: {}".format('filesystemfree', filesystemfree)]
        else:
            line = [_print_format(share.get_name(), 'sharename'),
                    _print_format(fsname, 'fsname'),
                    _print_format(share.get_path(), 'path'),
                    _print_format(quota, 'quota'),
                    _print_format(usedquota, 'usedQuota'),
                    _print_format(filesystemfree, 'filesystemfree')]
        log(logger, line)
        print "".join(line)


def _get_share_limit_to_dict():
    import re
    from os import path
    shares_quota = []
    output = ps_cmd._run_share_quota_get()
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
        share['Usage'] = (int(share['Usage'])) * byte
        share['size'] = (int(share['size'])) * byte
    log(logger, "share sizes are {}".format(shares_quota))
    return shares_quota


def _share_query_to_share_instance():
    #  Run Get-SmbShare and pars it to list of dicts contains share name and path
    import re
    from os import path
    shares = []
    output = ps_cmd._run_share_query()
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
                share = Share(result['share_name'], path.normcase(result['path']))
                shares.append(share)
    return shares


def get_all_shares_data():
    shares = []
    shares_only = _share_query_to_share_instance()
    quotas = _get_share_limit_to_dict()
    for share in shares_only:
        for quota in quotas:
            if share.get_path() == quota['path']:
                shares.append(Share(share.get_name(), share.get_path(), disabled=quota['Disabled'],
                                    usage=quota['Usage'], size=quota['size'],
                                    freeonfs=(lib.get_path_free_size(share.get_path())['avail'])))
                break
    for share in shares_only:
        if share not in shares:
            shares.append(share)
    return shares


def join_fs_and_share(filesystems, shares):
    share_list = []
    for filesystem in filesystems:
        for share in shares:
            if lib.is_path_part_of_path(filesystem['mount'], share.get_path()):
                share.fs = filesystem
                share_list.append(share)
    return share_list


def find_share_from_list_of_shares(share_list, share_name=None, share_path=None):
    '''Given share list and share name or share path, returns the relevant share
    '''
    for share in share_list:
        if share.get_name() == share_name or share.get_path() == share_path:
            return share

def exit_if_share_doesnt_exist(share_name):
    shares = get_all_shares_data()
    share = find_share_from_list_of_shares(shares, share_name=share_name)
    if share is None:
        log_n_raise(logger, "{} Doesn't Exist.".format(share_name))
    return share

def _share_create_prechecks(share_name, share_path, create_path, sdk):
    from os import path, makedirs
    existing_shares = _share_query_to_share_instance()
    MAX_PATH_LENTH = 120  # max share char because we are parsing output this might be a problem
    vaild_fs = False
    full_path = path.normcase(share_path)
    filesystems = _get_all_fs(sdk)
    for filesystem in filesystems:
        if lib.is_path_part_of_path(full_path, filesystem['mount']):
            fs_path = filesystem['mount']
            vaild_fs = True
            if lib.is_disk_in_cluster(filesystem['winid']) is False:
                log_n_raise(logger, "{} isn't part of the SMB Cluster".format(full_path))
    if vaild_fs is False:
        log_n_raise(logger, "{} share path, does NOT reside on the cluster".format(full_path))
    if fs_path == full_path:
        log_n_raise(logger, "Can't create share on filesystem ROOT (example: G:\<fs_name> is invalid).", level=WARNING)
    for share in existing_shares:
        if share.get_name() == share_name:
            log_n_raise(logger, "Share Name Conflict ! {} Share Name Exists".format(share_name))
        if path.realpath(share.get_path()) == full_path:
            log_n_raise(logger, "'{}' is Already Shared, Lucky You ?!".format(share_path), level=WARNING)
    if len(full_path) > MAX_PATH_LENTH:
        log_n_raise(logger, "Path length is to long. path length of {} characters is currently supported".
                            format(MAX_PATH_LENTH), level=WARNING)
    if not path.exists(full_path):
        log(logger, "Path: {} doesn't exist.".format(full_path), level=INFO, color="yellow")
        if not create_path:
            log(logger, "Would you like to create it ?", level=INFO, color="yellow")
            lib.approve_operation()
        log(logger, "Creating {}".format(full_path), level=INFO, color="yellow")
        makedirs(full_path)
    return full_path


def _share_limit_prechecks_and_set(share_name, size, sdk):
    from smb.cli.__version__ import __version__
    shares_data = get_all_shares_data()
    filesystems_data = _get_all_fs(sdk)
    shares = join_fs_and_share(filesystems_data, shares_data)
    shares_paths = [share.get_path() for share in shares]
    share = find_share_from_list_of_shares(shares, share_name=share_name)
    fs_size = share.get_fs()['sizes']['size']
    if size >= fs_size:
        log_n_raise(logger, "No use in limiting share to {} when Filesystem size is {}".format(size, fs_size), level=WARNING)
    if share.is_limited():
        log(logger, "{} is Already Size Limited, Changing Size to {}".format(share_name, size), level=INFO)
        ps_cmd._run_share_limit_set(share.get_path(), size)
        return
    if share.get_path() in shares_paths:
        for s in shares:
            if lib.is_path_part_of_path(s.get_path(), share.get_path()):
                if s.is_limited():
                    log(logger, "Recursive Size Limit is NOT Supported in {}".format(__version__), level=WARNING, color="yellow")
                    log(logger, "New Limit {} Conflicts with {}".format(share.get_path(), s.get_path()),
                        level=WARNING, color="yellow")
                    return
    ps_cmd._run_share_limit_set(share.get_path(), size)


def share_create(share_name, share_path, mkdir, size, sdk):
    if share_path[-1] in ["'", '"']:
        # This if fixes Dir path ends with ticks " e.g. "c:\dir\" without it "\path\" will not work.
        share_path = share_path[0:-1]
    _share_create_prechecks(share_name, share_path, mkdir, sdk)
    ps_cmd._run_share_create(share_name, share_path)
    log(logger, "'{}' Share Created".format(share_name), level=INFO, color="green")
    ps_cmd._run_create_share_limit_default(share_path)
    if size == 0:
        return
    share_limit(share_path, size)


def share_limit(share_name, size, sdk):
    _share_limit_prechecks_and_set(share_name, size, sdk)
    log(logger, "{} limited to {}".format(share_name, size), level=INFO, color="green")


def share_unlimit(share_name):
    share = exit_if_share_doesnt_exist(share_name)
    if share.is_limited() is False:
        log_n_raise(logger, "{} doesn't have a limit on it.".format(share['share_name']), level=WARNING)
    ps_cmd._run_share_limit_set_default(share.get_path())
    log(logger, "{} Size Limit Removed".format(share.get_name()), level=INFO, color="green")


def share_query(units, sdk, detailed):
    if units:
        units = lib._validate_size(units)
    shares_data = get_all_shares_data()
    filesystems_data = _get_all_fs(sdk)
    shares = join_fs_and_share(filesystems_data, shares_data)
    if len(shares) == 0:
        log(logger, "No Share Are Defined", level=INFO)
        return
    print_share_query(shares, units, detailed)


def share_delete(share_name):
    share = exit_if_share_doesnt_exist(share_name)
    ps_cmd._run_share_limit_delete(share.get_path())
    ps_cmd._run_share_delete(share_name)
    log(logger, "{} Share Deleted".format(share_name), level=INFO, color="green")
