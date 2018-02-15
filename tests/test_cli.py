import unittest
import smb.cli

class TestCli(unittest.TestCase):
    """docstring for TestCli"""
    # def __init__(self, arg):
        # super(TestCli, self).__init__()
        # self.arg = arg
    def _get_random_size(self):
        import random
        size_unit = random.sample(['MB','MiB','GB', 'GiB', 'TB', 'TiB'], 1)
        if 'M' in size_unit:
            return str(random.randrange(1000, 100000)) + unit_size
        if 'G' in size_unit:
            return str(random.randrange(1, 1000)) + unit_size
        if 'T' in size_unit:
            return str(random.randrange(1, 3)) + unit_size

    def test_fs_create(self):
        sdk = smb.cli.lib.prechecks()
        config = sdk.get_local_config()
        arguments['--pool'] = config['PoolName']
        for i in range(1, 10):
            arguments['--size'] = _get_random_size()
            arguments['--name'] = "fsname_{}".format(i)
            smb.cli.run_fs_create(arguments, sdk)

