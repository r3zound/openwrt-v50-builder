import paramiko
HOST = '<YOUR_BUILD_SERVER_IP>'
PORT = 22
USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username')
PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>')
SUDO = '<YOUR_SUDO_PASSWORD>'
OPENWRT_DIR = '/home/lg/openwrt-build/openwrt_V5'
TEMPLATE_IMG = f'{OPENWRT_DIR}/openwrt-backup-20260813-235659.img'
FINAL_IMG = f'{OPENWRT_DIR}/openwrt-final.img'
MOUNT_POINT = '/mnt/backup-openwrt'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)


def run(cmd, t=60):
    if 'sudo' in cmd:
        cmd = cmd.replace('sudo', f'echo "{SUDO}" | sudo -S', 1)
    si, so, se = client.exec_command(cmd, timeout=t)
    out = so.read().decode('utf-8', 'replace').strip()
    err = se.read().decode('utf-8', 'replace').strip()
    return out, err


def sudo_run(cmd, t=120):
    full = f'echo "{SUDO}" | sudo -S {cmd}'
    si, so, se = client.exec_command(full, timeout=t)
    out = so.read().decode('utf-8', 'replace').strip()
    err = se.read().decode('utf-8', 'replace').strip()
    return out, err


print('=== 1) 检查模板 ===')
out, _ = run(f'ls -lh {TEMPLATE_IMG}')
print(out)

print('\n=== 2) 检查是否已挂载 ===')
out, _ = run('mount | grep backup-openwrt || echo NOT_MOUNTED')
print(out)

print('\n=== 3) cp backup -> final ===')
out, err = run(f'cp {TEMPLATE_IMG} {FINAL_IMG} && echo COPY_OK')
print(out, err)

print('\n=== 4) mount ext4 ===')
out, err = sudo_run(f'mount -o loop -t ext4 {FINAL_IMG} {MOUNT_POINT}')
print('OUT:', out)
print('ERR:', err)

print('\n=== 5) 列出 ua3f / nikki / hiddify / mihomo 相关文件 ===')
keywords = ['ua3f', 'nikki', 'hiddify', 'mihomo']
for kw in keywords:
    print(f'\n--- {kw} ---')
    out, _ = run(
        f"find {MOUNT_POINT} -iname '*{kw}*' -not -path '*/proc/*' "
        f"2>/dev/null | head -50"
    )
    print(out if out else '(none)')

print('\n=== 6) 列出 frpc / passwall2 完整文件 (作为保留对比) ===')
for kw in ['frpc', 'passwall2']:
    print(f'\n--- {kw} ---')
    out, _ = run(
        f"find {MOUNT_POINT} -iname '*{kw}*' -not -path '*/proc/*' "
        f"2>/dev/null | head -30"
    )
    print(out if out else '(none)')

print('\n=== 7) 检查 init.d 目录 ===')
out, _ = run(f'ls {MOUNT_POINT}/etc/init.d/ | sort')
print(out)

print('\n=== 8) 检查 LuCI 菜单 ===')
out, _ = run(f'ls {MOUNT_POINT}/usr/share/luci/menu.d/ 2>/dev/null | sort')
print(out)

print('\n=== 9) 检查 LuCI ACL ===')
out, _ = run(f'ls {MOUNT_POINT}/usr/share/rpcd/acl.d/ 2>/dev/null | sort')
print(out)

client.close()
print('\n=== DONE (镜像仍挂载, 待后续处理) ===')