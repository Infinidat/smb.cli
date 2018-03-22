import unittest
import outputs
from smb.cli import ps_cmd
from infi.execute import execute_assert_success, execute
share_names = ['share1', 'share 2', 'long_share_3_and    more']
fs_names = ['fs1', 'fs2', 'fs3']

class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # make sure we are on the Active Node to start with
        cmd = ['smbmgr', 'fs', 'query']
        result = execute(cmd)
        if outputs.not_active_node in result.get_stdout():
            ps_cmd._perform_cluster_failover()

    @classmethod
    def tearDownClass(cls):
        for fs in fs_names + ['fs_test_for_shares']:
            try:
                cmd = ['smbmgr', 'fs', 'delete', '--name={}'.format(fs), '--yes']
                execute(cmd)
            except:
                pass

    def _get_random_size(self):
        import random
        size_unit = random.sample(['MB', 'MiB', 'GB', 'GiB', 'TB', 'TiB'], 1)[0]
        if 'M' in size_unit:
            return str(random.randrange(1000, 100000)) + size_unit
        if 'G' in size_unit:
            return str(random.randrange(1, 1000)) + size_unit
        if 'T' in size_unit:
            return str(1) + size_unit

    def test_fs_query(self):
        cmd = ['smbmgr', 'fs', 'query']
        result = execute(cmd)
        self.assertIn(outputs.fs_query_header, result.get_stdout())
        ps_cmd._perform_cluster_failover()
        result = execute_assert_success(cmd)
        result_out = result.get_stdout()
        self.assertNotIn(outputs.fs_query_header, result_out)
        self.assertEqual(outputs.not_active_node, result_out)
        ps_cmd._perform_cluster_failover()

    def test_01_fs_create(self):
        for fs in fs_names:
            # size = self._get_random_size()
            size = "1GB"
            cmd = ['smbmgr', 'fs', 'create', '--name={}'.format(fs), '--size={}'.format(size)]
            result = execute_assert_success(cmd).get_stdout()
            if outputs.fs_delete in result:
                raise
        cmd = ['smbmgr', 'fs', 'query']
        result_out = execute_assert_success(cmd).get_stdout()
        for fs in fs_names:
            self.assertIn('{}'.format(fs), result_out)

    def test_02_fs_delete(self):
        for fs in fs_names:
            cmd = ['smbmgr', 'fs', 'delete', '--name={}'.format(fs), '--yes']
            result = execute_assert_success(cmd)
            self.assertIn(outputs.fs_delete.format('{}'.format(fs)), result.get_stdout())

    def test_03_fs_detach_attach(self):
        cmd = ['smbmgr', 'fs', 'create', '--name=detachable_fs', '--size={}'.format(self._get_random_size())]
        execute_assert_success(cmd)
        cmd = ['smbmgr', 'fs', 'detach', '--name=detachable_fs', '--yes']
        execute_assert_success(cmd)
        cmd = ['smbmgr', 'fs', 'attach', '--name=detachable_fs', '--yes']
        execute_assert_success(cmd)
        cmd = ['smbmgr', 'fs', 'delete', '--name=detachable_fs', '--yes']
        execute_assert_success(cmd)

    def test_04_share_create(self):
        cmd = ['smbmgr', 'fs', 'create', '--name=fs_test_for_shares', '--size=1GB']
        result = execute(cmd)
        for share in share_names:
            cmd = ['smbmgr', 'share', 'create', '--name={}'.format(share),
                   '--path=g:\\fs_test_for_shares\\{}'.format(share), '--mkdir']
            result = execute(cmd).get_stdout()
            self.assertIn(outputs.share_created.format(share), result)

    def test_05_share_query(self):
        cmd = ['smbmgr', 'share', 'query']
        result = execute_assert_success(cmd).get_stdout()
        self.assertIn(outputs.share_query_header, result)
        self.assertIn('share1', result)
        self.assertIn('share 2', result)
        self.assertIn('long_share_3...', result)

    def test_06_share_resize(self):
        for share in share_names:
            cmd = ['smbmgr', 'share', 'resize', '--name={}'.format(share),
                   '--size={}'.format(self._get_random_size()), '--yes']
            result = execute(cmd).get_stdout()
            if (outputs.bad_share_resize in result) or (outputs.share_limited in result):
                pass
            else:
                # Test Failed
                self.assertTrue(False)

    def test_07_share_delete(self):
        for share in share_names:
            cmd = ['smbmgr', 'share', 'delete', '--name={}'.format(share), '--yes']
            result = execute(cmd).get_stdout()
            self.assertIn(outputs.share_deleted.format(share), result)
        cmd = ['smbmgr', 'fs', 'delete', '--name=fs_test_for_shares', '--yes']
        execute(cmd)

    def test_08_share_query(self):
        cmd = ['smbmgr', 'share', 'query']
        result = execute_assert_success(cmd).get_stdout()
        self.assertIn(outputs.no_shares, result)
