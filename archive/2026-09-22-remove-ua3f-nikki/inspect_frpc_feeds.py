# -*- coding: utf-8 -*-
"""排查 luci-app-frpc / luci-i18n-frpc 结构"""
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

print('=== 1) luci-app-frpc 完整结构 ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds/luci/applications/luci-app-frpc -type f 2>/dev/null | head -30')
print(out or '(none)')

print('\n=== 2) 有 po/ 或 translations/ 吗? ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds/luci/applications/luci-app-frpc -type d \( -name po -o -name translations -o -name locale -o -name i18n \) 2>/dev/null')
print(out or '(none)')

print('\n=== 3) feeds 里有 luci-i18n-frpc 吗(任意路径)? ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds -iname "*i18n*frpc*" 2>/dev/null')
print(out or '(none)')

print('\n=== 4) feeds 中所有 i18n 包名 (找规律) ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5/feeds -name Makefile -path "*i18n*" 2>/dev/null | head -20')
print(out or '(none)')

print('\n=== 5) feeds.conf.default ===')
out, _ = run('cat /home/lg/openwrt-build/openwrt_V5/feeds.conf.default')
print(out)

print('\n=== 6) feeds 索引:已安装哪些 luci 包 ===')
out, _ = run('ls /home/lg/openwrt-build/openwrt_V5/feeds/luci/')
print(out)

print('\n=== 7) frpc package 在 package/ 还是 feeds/? ===')
out, _ = run('find /home/lg/openwrt-build/openwrt_V5 -name Makefile -path "*frpc*" 2>/dev/null')
print(out or '(none)')

print('\n=== 8) luci-app-passwall2 的 po/ 看看对比 ===')
out, _ = run('ls /home/lg/openwrt-build/openwrt_V5/feeds/luci/applications/luci-app-passwall2/po/ 2>/dev/null | head -10')
print('passwall2 po/:', out or '(none)')
out, _ = run('ls /home/lg/openwrt-build/openwrt_V5/feeds/luci/applications/luci-app-passwall2/po/zh-cn/ 2>/dev/null | head -3')
print('passwall2 po/zh-cn/:', out or '(none)')

client.close()