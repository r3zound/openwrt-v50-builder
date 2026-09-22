# -*- coding: utf-8 -*-
"""移除 ua3f+nikki+hiddify 的第二步:cp+mount+delete+verify+unmount+download.
不输出 emoji,避免 Windows GBK 控制台崩.
"""
import sys, os, time, hashlib
import paramiko

# force stdout/stderr to utf-8 on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

HOST = '<YOUR_BUILD_SERVER_IP>'
PORT = 22
USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username')
PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>')
SUDO = '<YOUR_SUDO_PASSWORD>'

OPENWRT_DIR = '/home/lg/openwrt-build/openwrt_V5'
ORIG_BACKUP = f'{OPENWRT_DIR}/openwrt-backup-20260813-235659.img'
BASE_FRPC = f'{OPENWRT_DIR}/openwrt-base-frpc-20260822.img'
FINAL_IMG = f'{OPENWRT_DIR}/openwrt-final.img'
MOUNT_POINT = '/mnt/backup-openwrt'
LOCAL_OUTPUT = r'D:\OneDrive\User\Network\CPE\V50\OpenWRT虚机资源等1个文件\OpenWRT虚机资源\openwrt-V50-frpc-noa3f-nikki-20260922.img'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USER, PASS, timeout=30)


def run(cmd, t=60):
    if 'sudo' in cmd and 'echo' not in cmd.split('sudo')[0][-30:]:
        cmd = cmd.replace('sudo', f'echo "{SUDO}" | sudo -S', 1)
    si, so, se = client.exec_command(cmd, timeout=t)
    out = so.read().decode('utf-8', 'replace').strip()
    err = se.read().decode('utf-8', 'replace').strip()
    return out, err


def sudo(cmd, t=120):
    full = f'echo "{SUDO}" | sudo -S {cmd}'
    si, so, se = client.exec_command(full, timeout=t)
    out = so.read().decode('utf-8', 'replace').strip()
    err = se.read().decode('utf-8', 'replace').strip()
    return out, err


def section(title):
    print('\n' + '=' * 60)
    print(title)
    print('=' * 60)


# ====================== 1) cp BASE_FRPC -> FINAL_IMG ======================
section('[1] cp BASE_FRPC -> FINAL_IMG')
out, _ = run(f'cp {BASE_FRPC} {FINAL_IMG} && echo COPY_OK')
print(out)

# ====================== 2) mount ext4 ======================
section('[2] mount ext4')
out, err = sudo(f'mount -o loop -t ext4 {FINAL_IMG} {MOUNT_POINT}')
print('OUT:', out or '(empty)')
print('ERR:', err or '(empty)')
out, _ = run(f'ls {MOUNT_POINT} 2>&1 | head -3')
print('MOUNT CHECK:', out)

# ====================== 3) 列出待删除文件 ======================
section('[3] 列出 ua3f / nikki / hiddify 文件')
keywords = ['ua3f', 'nikki', 'hiddify']
all_to_delete = []
for kw in keywords:
    out, _ = run(
        f"find {MOUNT_POINT} -iname '*{kw}*' -not -path '*/proc/*' 2>/dev/null"
    )
    files = [l for l in out.splitlines() if l.strip()]
    print(f'  -- {kw}: {len(files)} 个')
    for f in files:
        print(f'    {f}')
    all_to_delete.extend(files)

all_to_delete = sorted(set(all_to_delete))
print(f'\n待删总计: {len(all_to_delete)} 个文件/链接')

# ====================== 4) 删除 ======================
section('[4] 删除')
delete_failures = []
for f in all_to_delete:
    out, err = sudo(f'rm -rf "{f}"')
    if err and 'No such file' not in err and 'cannot remove' not in err:
        delete_failures.append((f, err))
if delete_failures:
    print(f'  失败 {len(delete_failures)} 个:')
    for f, e in delete_failures[:5]:
        print(f'    {f}: {e}')
else:
    print('  全部成功')

# ====================== 5) 验证残留 ======================
section('[5] 验证残留 (应为 0)')
for kw in keywords:
    out, _ = run(f"find {MOUNT_POINT} -iname '*{kw}*' -not -path '*/proc/*' 2>/dev/null")
    files = [l for l in out.splitlines() if l.strip()]
    print(f'  {kw} 残留: {len(files)} 个')

# ====================== 6) 验证保留项 ======================
section('[6] 验证保留项')
keep_checks = {
    'frpc 二进制': f'{MOUNT_POINT}/usr/bin/frpc',
    'frpc init': f'{MOUNT_POINT}/etc/init.d/frpc',
    'frpc config': f'{MOUNT_POINT}/etc/config/frpc',
    'frpc luci view': f'{MOUNT_POINT}/www/luci-static/resources/view/frpc',
    'frpc i18n zh-cn': f'{MOUNT_POINT}/usr/lib/lua/luci/i18n/frpc.zh-cn.lmo',
    'passwall2 init': f'{MOUNT_POINT}/etc/init.d/passwall2',
    'passwall2_server init': f'{MOUNT_POINT}/etc/init.d/passwall2_server',
    'passwall2 config': f'{MOUNT_POINT}/etc/config/passwall2',
    'passwall2 i18n zh-cn': f'{MOUNT_POINT}/usr/lib/lua/luci/i18n/passwall2.zh-cn.lmo',
    'passwall2 menu': f'{MOUNT_POINT}/usr/share/luci/menu.d/luci-app-passwall2.json',
    'passwall2 acl': f'{MOUNT_POINT}/usr/share/rpcd/acl.d/luci-app-passwall2.json',
    'ZTE 型号 rc.local': f'{MOUNT_POINT}/etc/rc.local',
    'resize2fs': f'{MOUNT_POINT}/usr/sbin/resize2fs',
    'zapret2 nfq2': f'{MOUNT_POINT}/opt/zapret2/nfq2',
}
for name, path in keep_checks.items():
    out, _ = run(f'test -e "{path}" && echo OK || echo MISSING')
    flag = '[OK]' if out == 'OK' else '[MISS]'
    print(f'  {flag} {name}: {path}')

# ZTE 型号验证
out, _ = run(f'grep "ZTE MU3351" {MOUNT_POINT}/etc/rc.local && echo MATCHED || echo NOT_MATCHED')
print(f'  ZTE MU3351 in rc.local: {out}')

# ====================== 7) 卸载 ======================
section('[7] 卸载 (sync + umount + losetup -D)')
out, _ = sudo(f'sync')
print('sync:', out or '(empty)')
out, _ = sudo(f'umount {MOUNT_POINT}')
print('umount:', out or '(empty)')
out, _ = sudo(f'sync')
print('sync:', out or '(empty)')
out, _ = sudo(f'losetup -D 2>&1 | head -3 || true')
print('losetup -D:', out or '(empty)')

# ====================== 8) 下载 ======================
section('[8] 下载到本地')
print(f'  远程: {FINAL_IMG}')
print(f'  本地: {LOCAL_OUTPUT}')

if os.path.exists(LOCAL_OUTPUT):
    print(f'  本地目标已存在,先删: {LOCAL_OUTPUT}')
    os.remove(LOCAL_OUTPUT)

sftp = client.open_sftp()
state = {'last_pct': -1}
def progress(transferred, total):
    pct = int(transferred * 100 / total)
    if pct != state['last_pct'] and pct % 5 == 0:
        state['last_pct'] = pct
        mb_x = transferred / (1024 * 1024)
        mb_t = total / (1024 * 1024)
        print(f'\r  下载 {pct}% ({mb_x:.1f}/{mb_t:.1f} MB)', end='', flush=True)

sftp.get(FINAL_IMG, LOCAL_OUTPUT, callback=progress)
print('\n  下载完成')

# 校验
print('  计算本地 SHA256...')
h = hashlib.sha256()
with open(LOCAL_OUTPUT, 'rb') as f:
    while True:
        chunk = f.read(8 * 1024 * 1024)
        if not chunk:
            break
        h.update(chunk)
local_sha = h.hexdigest()

print('  计算远程 SHA256...')
out, _ = run(f'sha256sum {FINAL_IMG} | awk "{{print \\$1}}"')
remote_sha = out

print(f'  本地: {local_sha}')
print(f'  远程: {remote_sha}')
if local_sha == remote_sha:
    print('  SHA256 一致')
else:
    print('  SHA256 不一致!')

client.close()
print('\nDONE')