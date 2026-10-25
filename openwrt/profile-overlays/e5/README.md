# E5 profile overlay

This overlay is applied by `build-profile-tf.py` after the shared OpenWrt
network staging pass.

- LTE B28 (700 MHz) is in the E5 capability list and LuCI profile.
- NR is still queried from the modem capability response. The initial saved
  lock is the device-tested B1+B41 / n41+n78 profile; n28 is not forced when
  the baseband does not advertise it.
- The USB host DHCP reservation is corrected at `dhcp.usb_host`, and route,
  DNS, and classless-route options are removed from that reservation only.
- OpenClash artifacts are optional build inputs and are installed by `apk`
  after first boot. The APK and core are never silently downloaded during a
  build.
