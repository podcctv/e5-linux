#!/usr/bin/env python3
"""Offline checks for the E5 profile overlay and optional OpenClash staging."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TOP = Path(__file__).resolve().parents[2]
OVERLAY = TOP / 'openwrt/profile-overlays/e5'


def load_builder():
    spec = importlib.util.spec_from_file_location('build_profile_tf', TOP / 'openwrt/build-profile-tf.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class E5Profile(unittest.TestCase):
    def test_b28_and_safe_default_lock_are_explicit(self):
        modem = (OVERLAY / 'etc/config/unisoc_modem').read_text()
        self.assertIn("lte_supported_bands '1,3,5,8,28,34,38,39,40,41'", modem)
        lock = (OVERLAY / 'usr/libexec/unisoc-modem/lock-control').read_text()
        self.assertIn("AUTO_WORK_MODE = cfg('auto_work_mode', '152'", lock)
        self.assertIn("ENDC_MODES = {'5g4g', 'nsa', 'auto-nsa', '4g-nsa', 'sa-nsa'}", lock)
        self.assertEqual((OVERLAY / 'etc/unisoc-modem/lock-state.d/sim0/lte').read_text().strip(), '1,41')
        self.assertEqual((OVERLAY / 'etc/unisoc-modem/lock-state.d/sim0/nr').read_text().strip(), '41,78')
        self.assertNotIn('n28', (OVERLAY / 'etc/unisoc-modem/lock-state.d/sim0/nr').read_text())

    def test_usb_fix_targets_the_actual_reservation(self):
        script = (OVERLAY / 'etc/uci-defaults/98-e5-usb-host-no-default-route').read_text()
        self.assertIn('dhcp.usb_host', script)
        self.assertIn('121', script)
        self.assertNotIn('dhcp.usbhost', script)

    def test_openclash_staging_records_hashes(self):
        builder = load_builder()
        apk = TOP.parents[0] / 'e5-openwrt-flash-25.12.5-mainline-20261018-hotfix-v4-openclash' / 'files' / 'missing.apk'
        # The full build test supplies real artifacts; this test only checks
        # that the builder rejects a missing explicit input.
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                builder.stage_openclash(Path(directory), apk, None)


if __name__ == '__main__':
    unittest.main()
