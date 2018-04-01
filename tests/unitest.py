import unittest
from smb.cli.config import validate_key_val
from smb.cli.smb_log import SmbCliExited


class TestValidateKeyVal(unittest.TestCase):
    def test_chars_limits(self):
        tests_pass = ['asdqwezxc', 'asd123-12_', '123qs4----', '1','AQC31', 'a', 'asd_A1']
        tests_fail = ['!@#%@%^', 'asdasdasdasdasd6', 'asdzxcasdqweasdqwe', 'ASQWe$!asdq', 'qa()aq','q!', 'b\\', 'a.qer.q-.com']
        for test in tests_pass:
            validate_key_val('FSRoleName', test)
            validate_key_val('PoolName', test)
            validate_key_val('Cluster', test)
        for test in tests_fail:
            self.assertRaises(SmbCliExited, validate_key_val, 'FSRoleName', test)
            self.assertRaises(SmbCliExited, validate_key_val, 'Cluster', test)
        tests_fail_pool = ['!@#%@%^', 'aasdqweasdsdasdasdasdasd6aasdqweasdsdasdasdasdasd6','ASQWe$!asdq', 'qa()aq','q!', 'b\\', 'a.qer.q-.com']
        for test in tests_fail_pool:
            self.assertRaises(SmbCliExited, validate_key_val, 'PoolName', test)

    def test_ibox_address(self):
        tests_pass = ['1.1.1.2', '172.16.31.100', '255.255.255.1', '192.113.5.1','a.com', 'asd.qwe.123.com', 'www.blablabla.toto.woha.int.org']
        tests_fail = ['!@#%@%^', 'a,',' a.qer.q-&.com', '261.1.3.4', '256.1.78.123', '.1.1.1.1', '1.6.7.254.', 'asd.#.com', 'qsv', 'qwe.*', 'aaa.int!']
        for test in tests_pass:
            validate_key_val('IboxAddress', test)
        for test in tests_fail:
            self.assertRaises(SmbCliExited, validate_key_val, 'IboxAddress', test)

    def test_drive_letter(self):
        tests_pass = ['X:\\','D:\\', 'E:\\', 'y:\\' ]
        tests_fail = ['ab', '12', 'DA:\\', 'X::', 'a', 'ZZ:', 'x:', 'z:']
        for test in tests_pass:
            validate_key_val('MountRoot', test)
            validate_key_val('TempDriveLetter', test)
        for test in tests_fail:
            self.assertRaises(SmbCliExited, validate_key_val, 'MountRoot', test)
            self.assertRaises(SmbCliExited, validate_key_val, 'TempDriveLetter', test)
