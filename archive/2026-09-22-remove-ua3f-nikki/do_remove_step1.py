"""
移除 ua3f + nikki (+ hiddify 支撑) 的固件构建脚本
基础镜像：本地 openwrt-V50-frpc-20260822.img 上传到服务器
保留：frpc + passwall2 (+server) + 各自中文包 + 全部其他组件
"""
import paramiko
import os
import sys
import time

HOST = '<YOUR_BUILD_SERVER_IP>'
PORT = 22
USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username')
PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>')
SUDO = '<YOUR_SUDO_PASSWORD>'

OPENWRT_DIR = '/home/lg/openwrt-build/openwrt_V5'
ORIG_BACKUP = f'{OPENWRT_DIR}/openwrt-backup-20260813-235659.img'  # 原模板(不动)
BASE_FRPC = f'{OPENWRT_DIR}/openwrt-base-frpc-20260822.img'          # 新基础(上传的 frpc 镜像)
FINAL_IMG = f'{OPENWRT_DIR}/openwrt-final.img'                       # 真正编辑的目标
MOUNT_POINT = '/mnt/backup-openwrt'

LOCAL_FRPC = r'D:\OneDrive\User\Network\CPE\V50\OpenWRT虚机资源等1个文件\OpenWRT虚机资源\openwrt-V50-frpc-20260822.img'
LOCAL_OUTPUT = r'D:\OneDrive\User\Network\CPE\V50\OpenWRT虚机资源等1个文件\OpenWRT虚机资源\openwrt-V50-frpc-noa3f-nikki-20260922.img'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USER, PASS, timeout=30)


def run(cmd, t=60):
    """普通用户命令;含 sudo 时自动 -S 传密码"""
    if 'sudo' in cmd and 'echo' not in cmd.split('sudo')[0][-30:]:
        cmd = cmd.replace('sudo', f'echo "{SUDO}" | sudo -S', 1)
    si, so, se = client.exec_command(cmd, timeout=t)
    out = so.read().decode('utf-8', 'replace').strip()
    err = se.read().decode('utf-8', 'replace').strip()
    return out, err


def sudo(cmd, t=120):
    """显式 sudo,自动 -S"""
    full = f'echo "{SUDO}" | sudo -S {cmd}'
    si, so, se = client.exec_command(full, timeout=t)
    out = so.read().decode('utf-8', 'replace').strip()
    err = se.read().decode('utf-8', 'replace').strip()
    return out, err


# ====================== 0) 安全检查:先卸载 ======================
print('=== [0] 卸载当前挂载 ===')
out, _ = sudo(f'umount {MOUNT_POINT} 2>&1 || true')
print('umount:', out or '(无输出)')
out, _ = sudo('sync && losetup -D 2>&1 || true')
print('sync + losetup -D:', out or '(无输出)')
out, _ = run(f'ls {MOUNT_POINT} 2>&1 | head -3')
print('挂载点状态:', out)

# ====================== 1) 上传本地 frpc 镜像 ======================
print('\n=== [1] 上传本地 frpc 镜像到服务器 ===')
print(f'  本地: {LOCAL_FRPC}')
print(f'  远程: {BASE_FRPC}')
print(f'  大小: {os.path.getsize(LOCAL_FRPC)/1024/1024:.1f} MB')

sftp = client.open_sftp()

state = {'last_pct': -1}
def progress(transferred, total):
    pct = int(transferred * 100 / total)
    if pct != state['last_pct'] and pct % 5 == 0:
        state['last_pct'] = pct
        mb_x = transferred / (1024 * 1024)
        mb_t = total / (1024 * 1024)
        print(f'\r  上传 {pct}% ({mb_x:.1f}/{mb_t:.1f} MB)', end='', flush=True)

sftp.put(LOCAL_FRPC, BASE_FRPC, callback=progress)
print('\n  ✅ 上传完成')

# 校验 SHA256
print('\n=== 验证上传完整性 (SHA256) ===')
out, _ = run(f'sha256sum {BASE_FRPC} | awk "{{print \\$1}}"')
remote_sha = out
# 算本地 SHA
import hashlib
h = hashlib.sha256()
with open(LOCAL_FRPC, 'rb') as f:
    while True:
        chunk = f.read(8 * 1024 * 1024)
        if not chunk:
            break
        h.update(chunk)
local_sha = h.hexdigest()
print(f'  本地: {local_sha}')
print(f'  远程: {remote_sha}')
if local_sha == remote_sha:
    print('  ✅ SHA256 一致')
else:
    print('  ❌ SHA256 不一致!中止')
    sys.exit(1)

sftp.close()

# ====================== 2) cp frpc 镜像 -> final ======================
print('\n=== [2] cp BASE_FRPC -> FINAL_IMG ===')
out, _ = run(f'cp {BASE_FRPC} {FINAL_IMG} && echo COPY_OK')
print('  ', out)

# ====================== 3) mount ext4 ======================
print('\n=== [3] mount ext4 ===')
out, err = sudo(f'mount -o loop -t ext4 {FINAL_IMG} {MOUNT_POINT}')
print('  OUT:', out or '(无)')
print('  ERR:', err or '(无)')

# ====================== 4) 列出待删除文件 ======================
print('\n=== [4] 列出 ua3f / nikki / hiddify 相关文件 ===')
keywords = ['ua3f', 'nikki', 'hiddify']
all_to_delete = []
for kw in keywords:
    out, _ = run(
        f"find {MOUNT_POINT} -iname '*{kw}*' -not -path '*/proc/*' "
        f"-not -path '*/apk/keys/*' 2>/dev/null"
    )
    files = [l for l in out.splitlines() if l.strip()]
    # 过滤一些不该误删的:
    # - /etc/apk/keys/homeproxy-hiddify.pub 是签名公钥,与 nikki 关联 → 一并删
    # - /etc/nikki、/etc/hiddify 配置目录 → 删
    print(f'\n--- {kw} ({len(files)} files) ---')
    for f in files:
        print(f'  {f}')
    all_to_delete.extend(files)

# 去重
all_to_delete = sorted(set(all_to_delete))
print(f'\n待删总计: {len(all_to_delete)} 个文件/链接')

# ====================== 5) 删除 ======================
print('\n=== [5] 执行删除 ===')
for f in all_to_delete:
    out, err = sudo(f'rm -rf {f}')
    if err and 'No such file' not in err:
        print(f'  ⚠️  {f}: {err}')

# 再用 find 验证 ua3f/nikki/hiddify 全部消失
print('\n=== [6] 验证残留 ===')
for kw in keywords:
    out, _ = run(
        f"find {MOUNT_POINT} -iname '*{kw}*' -not -path '*/proc/*' "
        f"2>/dev/null"
    )
    files = [l for l in out.splitlines() if l.strip()]
    print(f'  {kw} 残留: {len(files)} 个' + (f' → {files[:3]}' if files else ' ✅'))

# 验证 frpc + passwall2 完整保留
print('\n=== [7] 验证保留项 ===')
keep_checks = {
    'frpc': [f'{MOUNT_POINT}/usr/bin/frpc', f'{MOUNT_POINT}/etc/init.d/frpc', f'{MOUNT_POINT}/etc/config/frpc'],
    'passwall2': [
        f'{MOUNT_POINT}/etc/init.d/passwall2',
        f'{MOUNT_POINT}/etc/init.d/passwall2_server',
        f'{MOUNT_POINT}/etc/config/passwall2',
        f'{MOUNT_POINT}/etc/config/passwall2_server',
        f'{MOUNT_POINT}/usr/lib/lua/luci/i18n/passwall2.zh-cn.lmo',
    ],
    'luci-i18n-passwall2-zh-cn': [
        f'{MOUNT_POINT}/usr/lib/lua/luci/i18n/passwall2.zh-cn.lmo',
    ],
}
for name, paths in keep_checks.items():
    ok = 0
    for p in paths:
        out, _ = run(f'test -e {p} && echo OK || echo MISSING')
        if out == 'OK':
            ok += 1
    print(f'  {name}: {ok}/{len(paths)} OK')

# 验证 ZTE 定制未损
print('\n=== [8] 验证 ZTE 定制未损 ===')
zte_checks = [
    f'grep -q "ZTE MU3351" {MOUNT_POINT}/etc/rc.local && echo OK || echo BROKEN',
    f'test -e {MOUNT_POINT}/etc/rc.local && echo OK || echo MISSING',
    f'test -e {MOUNT_POINT}/usr/sbin/resize2fs && echo OK || echo MISSING',
    f'test -d {MOUNT_POINT}/opt/zapret2 && echo OK || echo MISSING',
]
for cmd in zte_checks:
    out, _ = run(cmd)
    print(f'  {cmd[:80]}: {out}')

# ====================== 6) 卸载 ======================
print('\n=== [9] 卸载镜像 (sync + umount + losetup -D) ===')
out, _ = sudo(f'sync')
print('  sync:', out or '(无)')
out, _ = sudo(f'umount {MOUNT_POINT}')
print('  umount:', out or '(无)')
out, _ = sudo(f'sync && losetup -D')
print('  sync + losetup -D:', out or '(无)')

# ====================== 7) 下载到本地 ======================
print('\n=== [10] 下载最终镜像到本地 ===')
print(f'  远程: {FINAL_IMG}')
print(f'  本地: {LOCAL_OUTPUT}')

sftp = client.open_sftp()
state2 = {'last_pct': -1}
def progress2(transferred, total):
    pct = int(transferred * 100 / total)
    if pct != state2['last_pct'] and pct % 5 == 0:
        state2['last_pct'] = pct
        mb_x = transferred / (1024 * 1024)
        mb_t = total / (1024 * 1024)
        print(f'\r  下载 {pct}% ({mb_x:.1f}/{mb_t:.1f} MB)', end='', flush=True)

sftp.get(FINAL_IMG, LOCAL_OUTPUT, callback=progress2)
print('\n  ✅ 下载完成')

# 校验
out, _ = run(f'sha256sum {FINAL_IMG} | awk "{{print \\$1}}"')
remote_sha_final = out
h2 = hashlib.sha256()
with open(LOCAL_OUTPUT, 'rb') as f:
    while True:
        chunk = f.read(8 * 1024 * 1024)
        if not chunk:
            break
        h2.update(chunk)
local_sha_final = h2.hexdigest()
print(f'  本地 SHA256: {local_sha_final}')
print(f'  远程 SHA256: {remote_sha_final}')
print('  ' + ('✅ 一致' if local_sha_final == remote_sha_final else '❌ 不一致'))

client.close()
print('\n=== ✅ 全部完成 ===')
print(f'最终镜像: {LOCAL_OUTPUT}')