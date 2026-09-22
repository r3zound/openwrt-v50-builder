# -*- coding: utf-8 -*-
"""快速核对 frpc / passwall2 完整布局,确认中文包是否齐全"""
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

def sudo(cmd, t=120):
    si, so, se = client.exec_command(f'echo "<YOUR_SUDO_PASSWORD>" | sudo -S {cmd}', timeout=t)
    return so.read().decode('utf-8','replace').strip(), se.read().decode('utf-8','replace').strip()

# 检查是否需要重新挂载
out, _ = run('mount | grep backup-openwrt || echo NOT_MOUNTED')
print('mount state:', out)
if 'NOT_MOUNTED' in out:
    print('mounting...')
    out, _ = sudo('mount -o loop -t ext4 /home/lg/openwrt-build/openwrt_V5/openwrt-final.img /mnt/backup-openwrt')
    print('mount:', out)

# 完整列出 frpc / passwall2 / luci-i18n-* 相关文件
for kw in ['frpc', 'passwall', 'luci-i18n']:
    print(f'\n=== {kw} ===')
    out, _ = run(f"find /mnt/backup-openwrt -iname '*{kw}*' -not -path '*/proc/*' 2>/dev/null | sort")
    print(out or '(none)')

# 看 apk 包的列表
print('\n=== apk installed (luci-i18n-*) ===')
out, _ = run("grep -l 'luci-i18n-' /mnt/backup-openwrt/lib/apk/packages/*.list 2>/dev/null | head -20")
print(out or '(none)')

# unmount
out, _ = sudo('sync')
print('\nunmount...')
out, _ = sudo('umount /mnt/backup-openwrt')
print('umount:', out or '(ok)')

client.close()
print('done')