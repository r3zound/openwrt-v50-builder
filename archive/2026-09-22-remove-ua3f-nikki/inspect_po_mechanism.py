# -*- coding: utf-8 -*-
"""深入看 luci-app-frpc / passwall2 / luci.mk 关于 i18n 的处理"""
import sys, paramiko
sys.stdout.reconfigure(encoding='utf-8')
HOST='<YOUR_BUILD_SERVER_IP>'; USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username'); PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>')
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS, timeout=10)

def run(cmd, t=60):
    if 'sudo' in cmd and 'echo' not in cmd.split('sudo')[0][-30:]:
        cmd = cmd.replace('sudo', f'echo "<YOUR_SUDO_PASSWORD>" | sudo -S', 1)
    si, so, se = client.exec_command(cmd, timeout=t)
    return so.read().decode('utf-8','replace').strip(), se.read().decode('utf-8','replace').strip()

print('=== 1) luci-app-frpc Makefile ===')
out, _ = run('cat /home/lg/openwrt-build/openwrt_V5/feeds/luci/applications/luci-app-frpc/Makefile')
print(out)

print('\n=== 2) po/zh_Hans/frpc.po (前 30 行) ===')
out, _ = run('head -30 /home/lg/openwrt-build/openwrt_V5/feeds/luci/applications/luci-app-frpc/po/zh_Hans/frpc.po 2>&1')
print(out)

print('\n=== 3) luci.mk (查找 LUCI_LANG / po2lmo) ===')
out, _ = run('grep -n -E "LUCI_LANG|po2lmo|zh-cn|zh_Hans|LUCI_PACKAGE_LANG" /home/lg/openwrt-build/openwrt_V5/feeds/luci/luci.mk 2>&1 | head -30')
print(out)

print('\n=== 4) feeds/luci/modules/ ===')
out, _ = run('ls /home/lg/openwrt-build/openwrt_V5/feeds/luci/modules/ 2>&1 | head -20')
print(out)

print('\n=== 5) po2lmo 工具路径 ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5 -name "po2lmo*" 2>/dev/null | head -5')
print(out or '(not found)')

print('\n=== 6) 整个 feeds/luci/applications 里有多少 po/zh_Hans ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds/luci -path "*/po/zh_Hans*" 2>/dev/null | head -20')
print(out)

print('\n=== 7) luci-app-passwall2 完整结构 ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds -path "*luci-app-passwall2*" -type d 2>/dev/null')
print(out)
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds -path "*luci-app-passwall2*" 2>/dev/null | head -30')
print('files:', out)

print('\n=== 8) feeds index packages 下与 i18n 相关 ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds -name Makefile | xargs grep -l "i18n" 2>/dev/null | head -10')
print(out or '(none)')

print('\n=== 9) OpenWrt 25.x LUCI_LANG 查找 ===')
out, _ = run('grep -rn "LUCI_LANG" /home/lg/openwrt-build/openwrt_V5/feeds/luci/ 2>/dev/null | head -10')
print(out or '(none)')

print('\n=== 10) bin/packages 看现有 i18n 包 ===')
out, _ = run('ls /home/lg/openwrt-build/openwrt_V5/bin/packages/aarch64_generic/luci/ 2>/dev/null | grep -i "i18n\\|zh-cn" | head -20')
print(out or '(none)')

client.close()