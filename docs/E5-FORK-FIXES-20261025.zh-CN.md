# E5 fork 修复说明

本次 E5 profile 修复针对已记录的实机现象，构建时由
`openwrt/build-profile-tf.py` 应用。

## 已确认并固化

- `device/openwrt_device_common` 更新到包含开机锁定回放和 USB 管理链路修复的
  `d6a19c1b1a6176800ec8f9a599c203ec12e86803`。
- E5 LTE 能力列表加入 B28（700 MHz），NR 仍从基带能力查询，不强行写入不支持的
  n28。默认保存的稳定锁定为 LTE B1+B41、NR n41+n78；频段页面仍可显示和选择
  基带实际报告的 n28。
- USB NCM DHCP 修复改为匹配真实的 `dhcp.usb_host` 保留项，并删除网关、DNS 和
  classless-route 选项。这样电脑继续使用自己的 Wi-Fi 默认路由，E5 仍保留管理地址。
- OpenClash 官方 APK 和可选 arm64 mihomo core 作为显式构建输入放入刷机包，首次启动
  后由目标机的 `apk` 安装依赖；构建过程不会偷偷从网络下载或执行目标机安装脚本。

## 验证边界

Windows 主机没有 Docker/WSL，无法在本机执行完整的 Linux TF 构建链；实际刷机包会以
fork 提交号和输入哈希标记，并在刷机前执行离线包完整性检查。B28/n28 的长期驻网和
OpenClash 代理效果仍需在目标 E5 上验证，不能把离线构建检查当成移动网络验证。
