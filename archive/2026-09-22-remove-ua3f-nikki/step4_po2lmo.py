# -*- coding: utf-8 -*-
"""用 po2lmo 直接生成 frpc 的中文 .lmo,注入镜像"""
import sys, os, time, hashlib, paramiko
sys.stdout.reconfigure(encoding='utf-8')

HOST='<YOUR_BUILD_SERVER_IP>'; PORT=22; USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username'); PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>'); SUDO='<YOUR_SUDO_PASSWORD>'
OPENWRT_DIR='/home/lg/openwrt-build/openwrt_V5'
FINAL_IMG=f'{OPENWRT_DIR}/openwrt-final.img'
MOUNT_POINT='/mnt/backup-openwrt'
PO2LMO=f'{OPENWRT_DIR}/staging_dir/hostpkg/bin/po2lmo'
PO_FILE=f'{OPENWRT_DIR}/feeds/luci/applications/luci-app-frpc/po/zh_Hans/frpc.po'
LOCAL_OUTPUT=r'D:\OneDrive\User\Network\CPE\V50\OpenWRT虚机资源等1个文件\OpenWRT虚机资源\openwrt-V50-frpc-noa3f-nikki-20260922.img'

client=paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USER, PASS, timeout=30)

def run(cmd, t=60):
    if 'sudo' in cmd and 'echo' not in cmd.split('sudo')[0][-30:]:
        cmd = cmd.replace('sudo', f'echo "{SUDO}" | sudo -S', 1)
    si, so, se = client.exec_command(cmd, timeout=t)
    return so.read().decode('utf-8','replace').strip(), se.read().decode('utf-8','replace').strip()

def sudo(cmd, t=120):
    si, so, se = client.exec_command(f'echo "{SUDO}" | sudo -S {cmd}', timeout=t)
    return so.read().decode('utf-8','replace').strip(), se.read().decode('utf-8','replace').strip()

def section(t):
    print('\n' + '='*60); print(t); print('='*60)

# ========== 1) 验证 po 文件和 po2lmo 工具存在 ==========
section('[1] 验证文件')
for label, p in [('po2lmo', PO2LMO), ('frpc.po', PO_FILE)]:
    out, _ = run(f'test -e {p} && echo OK || echo MISSING')
    print(f'  {label}: {out}')
out, _ = run(f'wc -l {PO_FILE}')
print(f'  po 文件行数: {out}')

# ========== 2) 生成 .lmo (两个名字都生成) ==========
section('[2] 用 po2lmo 生成 .lmo')
# 用临时目录
TMP = '/tmp/frpc_lmo'
out, _ = sudo(f'rm -rf {TMP} && mkdir -p {TMP}')
print('清理 tmp:', out or '(ok)')

# zh_Hans.lmo (OpenWrt 25.x 新风格)
out, _ = run(f'{PO2LMO} {PO_FILE} {TMP}/frpc.zh_Hans.lmo && ls -l {TMP}/')
print('生成 zh_Hans.lmo:', out)

# 验证 zh-cn 兼容性:把语言代码串替换
# po2lmo 不直接接受别名,所以复制文件作为 zh-cn
out, _ = run(f'cp {TMP}/frpc.zh_Hans.lmo {TMP}/frpc.zh-cn.lmo && ls -l {TMP}/')
print('同时准备 zh-cn.lmo:', out)

# ========== 3) 挂载镜像 ==========
section('[3] 挂载 openwrt-final.img')
out, _ = run('mount | grep backup-openwrt || echo NOT_MOUNTED')
print('mount state:', out)
if 'NOT_MOUNTED' in out:
    out, _ = sudo(f'mount -o loop -t ext4 {FINAL_IMG} {MOUNT_POINT}')
    print('mount:', out or '(ok)')

# ========== 4) 注入 ==========
section('[4] 注入 .lmo 到镜像')
I18N_DIR = f'{MOUNT_POINT}/usr/lib/lua/luci/i18n'
out, _ = run(f'test -d {I18N_DIR} && echo DIR_OK || echo DIR_MISSING')
print('i18n dir:', out)

# 复制
for fname in ['frpc.zh_Hans.lmo', 'frpc.zh-cn.lmo']:
    out, _ = sudo(f'cp {TMP}/{fname} {I18N_DIR}/{fname}')
    print(f'cp {fname}:', out or '(ok)')

# 验证
out, _ = sudo(f'ls -la {I18N_DIR}/frpc.*.lmo')
print('注入后:')
print(out)

# 顺便修 lib/apk/packages 索引(可选)
out, _ = run(f'test -e {MOUNT_POINT}/lib/apk/packages/luci-i18n-passwall2-zh-cn.list && echo PASSWALL2_I18N_LIST_EXISTS || echo NONE')
print('passwall2 i18n list:', out)

# ========== 5) 卸载 ==========
section('[5] 卸载')
out, _ = sudo('sync'); print('sync:', out or '(ok)')
out, _ = sudo(f'umount {MOUNT_POINT}'); print('umount:', out or '(ok)')
out, _ = sudo('sync && losetup -D 2>/dev/null'); print('losetup:', out or '(ok)')

# ========== 6) 重新下载 ==========
section('[6] 重新下载到本地')
print(f'远程: {FINAL_IMG}')
print(f'本地: {LOCAL_OUTPUT}')

if os.path.exists(LOCAL_OUTPUT):
    print(f'删除本地旧文件: {LOCAL_OUTPUT}')
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
print('\n下载完成')

# SHA256 校验
print('计算 SHA256...')
h = hashlib.sha256()
with open(LOCAL_OUTPUT, 'rb') as f:
    while True:
        chunk = f.read(8 * 1024 * 1024)
        if not chunk: break
        h.update(chunk)
local_sha = h.hexdigest()

out, _ = run(f'sha256sum {FINAL_IMG} | awk "{{print \\$1}}"')
remote_sha = out
print(f'  本地: {local_sha}')
print(f'  远程: {remote_sha}')
print('  ' + ('SHA256 一致' if local_sha == remote_sha else 'SHA256 不一致!'))

client.close()
print('\nDONE')