import unittest
import outputs
import smb.cli
from smb.cli import commandline_to_docopt, share
from smb.cli.ibox_connect import InfiSdkObjects
from smb.cli.smb_log import SmbCliExited

class TestInit(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestInit, self).__init__(*args, **kwargs)
        self.sdk = InfiSdkObjects()
        self.config = smb.cli.config.config_get(silent=True)
        all_fs = smb.cli.fs._get_all_fs(self.sdk)
        fs_names = [fs['fsname'] for fs in all_fs]
        if 'base_fs' not in fs_names:
            arguments = commandline_to_docopt(['fs', 'create', '--size', '1GB',
                                               '--name=base_fs', '--pool={}'.format(self.config['PoolName'])])
            smb.cli.run_fs_create(arguments, self.sdk)

    @classmethod
    def tearDownClass(cls):
        pass
        # arguments = commandline_to_docopt(['fs', 'delete', '--name=base_fs', '--yes'])
        # smb.cli.run_fs_delete(arguments, InfiSdkObjects())

    def test_share_prechecks(self):
        self.assertRaisesRegexp(SmbCliExited, outputs.share_root_error,
                                share._share_create_prechecks, "koko", "g:\\base_fs", False, self.sdk)
        self.assertRaisesRegexp(SmbCliExited, outputs.share_not_part_of_cluster,
                                share._share_create_prechecks, "koko", "g:\\not_on_cluster\\asd", False, self.sdk)
        self.assertRaisesRegexp(SmbCliExited, outputs.share_not_part_of_cluster,
                                share._share_create_prechecks, "koko", "D:\\base_fs\\asd", False, self.sdk)
        all_shares = smb.cli.share.get_all_shares_data()
        shares_names = [s.get_name() for s in all_shares]
        if 'unitest_share' not in shares_names:
            arguments = commandline_to_docopt(['share', 'create', '--name=unitest_share',
                                               '--path=g:\\base_fs\\unitest_share', '--mkdir'])
            smb.cli.run_share_create(arguments, self.sdk)
        self.assertRaisesRegexp(SmbCliExited, outputs.share_name_conflict,
                                share._share_create_prechecks, "unitest_share", "g:\\base_fs\\asd", False, self.sdk)
        long_share_name = "g:\\base_fs\\asdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdas" \
        "asdqaaqaqqqweqweqweqweqweqweqwesdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdqaaqaqqqw"
        self.assertRaisesRegexp(SmbCliExited, outputs.share_name_too_long,
                                share._share_create_prechecks, "bla", long_share_name, False, self.sdk)
