import unittest
import tempfile
from pathlib import Path
from src.backup import BackupManager

class TestConfigBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mgr = BackupManager(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_backup_and_deduplication(self):
        cfg_v1 = "hostname rtr-01\ninterface GigabitEthernet0/0\n ip address 10.0.0.1 255.255.255.0\n"
        saved, msg = self.mgr.backup_device("rtr-01", cfg_v1)
        self.assertTrue(saved)


        saved2, msg2 = self.mgr.backup_device("rtr-01", cfg_v1)
        self.assertFalse(saved2)
        self.assertIn("unchanged", msg2)

    def test_diff_generation(self):
        cfg_v1 = "hostname rtr-01\nservice password-encryption\n"
        cfg_v2 = "hostname rtr-01\nno service password-encryption\n"

        self.mgr.backup_device("rtr-01", cfg_v1)
        self.mgr.backup_device("rtr-01", cfg_v2)

        diff = self.mgr.compare_backups("rtr-01", 0, 1)
        self.assertIn("-service password-encryption", diff)
        self.assertIn("+no service password-encryption", diff)

    def test_rotation(self):
        for i in range(7):
            cfg = f"hostname rtr-01\n! version {i}\n"
            self.mgr.backup_device("rtr-01", cfg)

        self.assertEqual(len(self.mgr.index["rtr-01"]), 7)
        deleted = self.mgr.rotate_backups("rtr-01", keep_last=3)
        self.assertEqual(deleted, 4)
        self.assertEqual(len(self.mgr.index["rtr-01"]), 3)

if __name__ == "__main__":
    unittest.main()
