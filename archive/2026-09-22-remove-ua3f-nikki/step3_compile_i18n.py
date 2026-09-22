# -*- coding: utf-8 -*-
"""补 luci-i18n-frpc-zh-cn:编译 → 注入镜像 → 重新下载"""
import sys, os, time, hashlib, paramiko
sys.stdout.reconfigure(encoding='utf-8')

HOST='<YOUR_BUILD_SERVER_IP>'; PORT=22; USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username'); PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>'); SUDO='<YOUR_SUDO_PASSWORD>'
OPENWRT_DIR='/home/lg/openwrt-build/openwrt_V5'
FINAL_IMG=f'{OPENWRT_DIR}/openwrt-final.img'
MOUNT_POINT='/mnt/backup-openwrt'
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

# ========== 1) 找 luci-i18n-frpc-zh-cn 源码 ==========
section('[1] 找 luci-i18n-frpc-zh-cn 源码位置')
out, _ = run(f"find {OPENWRT_DIR}/feeds -maxdepth 6 -type d -name 'luci-i18n-frpc*' 2>/dev/null")
print('luci-i18n-frpc 源码目录:', out or '(not found in feeds)')
out, _ = run(f"find {OPENWRT_DIR}/feeds -name 'Makefile' -path '*luci-app-frpc*' 2>/dev/null")
print('luci-app-frpc Makefile:', out or '(not found)')

# ========== 2) 在 .config 加 CONFIG_PACKAGE_luci-i18n-frpc-zh-cn ==========
section('[2] 配置 .config')
out, _ = run(f'grep -E "^CONFIG_PACKAGE_luci-i18n-frpc-zh-cn" {OPENWRT_DIR}/.config 2>/dev/null || echo NOT_SET')
print('当前 .config:', out)
if 'NOT_SET' in out or '=n' in out:
    out, _ = run(f"sed -i 's/^# CONFIG_PACKAGE_luci-i18n-frpc-zh-cn is not set/CONFIG_PACKAGE_luci-i18n-frpc-zh-cn=y/' {OPENWRT_DIR}/.config 2>/dev/null")
    out, _ = run(f"grep -q '^CONFIG_PACKAGE_luci-i18n-frpc-zh-cn=y' {OPENWRT_DIR}/.config || echo 'CONFIG_PACKAGE_luci-i18n-frpc-zh-cn=y' >> {OPENWRT_DIR}/.config")
    out, _ = run(f"grep 'luci-i18n-frpc-zh-cn' {OPENWRT_DIR}/.config")
    print('更新后 .config:', out)

# make defconfig 让依赖生效
print('运行 make defconfig ...')
si, so, se = client.exec_command(f'cd {OPENWRT_DIR} && make defconfig 2>&1', timeout=120)
out = so.read().decode('utf-8','replace').strip()
err = se.read().decode('utf-8','replace').strip()
print('defconfig OUT:', out[-500:] if len(out) > 500 else out)
print('defconfig ERR:', err[-500:] if len(err) > 500 else err)

# 再次确认
out, _ = run(f"grep 'luci-i18n-frpc-zh-cn' {OPENWRT_DIR}/.config")
print('defconfig 后 .config:', out)

# ========== 3) 编译 luci-i18n-frpc-zh-cn (单线程) ==========
section('[3] 编译 luci-i18n-frpc-zh-cn')
print('make package/luci-i18n-frpc-zh-cn/compile V=s -j1 ...')
si, so, se = client.exec_command(f'cd {OPENWRT_DIR} && make package/luci-i18n-frpc-zh-cn/compile V=s -j1 2>&1', timeout=600)
out = ''
start = time.time()
while time.time() - start < 600:
    if so.channel.recv_ready():
        chunk = so.channel.recv(8192).decode('utf-8','replace')
        out += chunk
        # 仅显示关键行
        for line in chunk.split('\n'):
            if any(k in line for k in ['error', 'Error', 'ERROR', 'make', 'Building', 'Packaging']):
                print('  >', line.strip()[:200])
    if so.channel.exit_status_ready():
        break
    time.sleep(0.5)
err = se.read().decode('utf-8','replace').strip()
print('编译完成(exit=%d)' % so.channel.exit_status)
# 取最后 30 行
print('OUT tail:')
print('\n'.join(out.splitlines()[-30:]))

# ========== 4) 找 APK 产物 ==========
section('[4] 找 APK 产物')
out, _ = run(f"find {OPENWRT_DIR}/bin/ -name '*luci-i18n-frpc*.apk' 2>/dev/null")
print('APK 产物:', out or '(NOT FOUND)')

if not out:
    print('尝试从 build_dir 找 .lmo 文件...')
    out, _ = run(f"find {OPENWRT_DIR}/build_dir -name 'frpc.zh-cn.lmo' 2>/dev/null")
    print('build_dir 查找:', out or '(NOT FOUND)')
    out, _ = run(f"find {OPENWRT_DIR}/build_dir -path '*luci-i18n-frpc*' -name '*.lmo' 2>/dev/null")
    print('build_dir *.lmo:', out or '(NOT FOUND)')
    print('!!! 编译未生成 luci-i18n-frpc-zh-cn APK,需要排查 feeds 或包名')
    sys.exit(1)

apk_path = out.splitlines()[0]
print(f'将用 APK: {apk_path}')

# ========== 5) 挂载镜像 ==========
section('[5] 挂载 openwrt-final.img')
out, _ = run('mount | grep backup-openwrt || echo NOT_MOUNTED')
print('mount state:', out)
if 'NOT_MOUNTED' in out:
    out, _ = sudo(f'mount -o loop -t ext4 {FINAL_IMG} {MOUNT_POINT}')
    print('mount:', out or '(ok)')
else:
    print('已经挂载')

# ========== 6) 解压并注入 ==========
section('[6] 解压 APK 并注入镜像')
out, _ = sudo(f'rm -rf /tmp/frpc_i18n_extract && mkdir -p /tmp/frpc_i18n_extract')
out, _ = sudo(f'tar --zstd -xf {apk_path} -C /tmp/frpc_i18n_extract')
print('解压:', out or '(ok)')

# 看解压出来的内容
out, _ = sudo(f'find /tmp/frpc_i18n_extract -type f 2>/dev/null | sort')
print('APK 内文件:', out or '(empty)')

# 复制到镜像
out, _ = sudo(f'cp -rv /tmp/frpc_i18n_extract/* {MOUNT_POINT}/ 2>&1 | tail -10')
print('复制:', out or '(ok)')

# 检查是否到位
out, _ = run(f"find {MOUNT_POINT} -name 'frpc.zh-cn.lmo' 2>/dev/null")
print('注入后 frpc.zh-cn.lmo:', out or '(NOT FOUND!)')

# 同时清理 luci-app-frpc 残留 (如果编译 i18n 时带出了 luci-app-frpc 修改)
# 检查是否 APK 里有 lib/apk/packages/luci-i18n-frpc-zh-cn.list
out, _ = run(f"find {MOUNT_POINT}/lib/apk/packages -name 'luci-i18n-frpc-zh-cn*' 2>/dev/null")
print('lib/apk/packages 标记:', out or '(无,正常 — 由运行时 apk 工具扫描)')

# ========== 7) 卸载 ==========
section('[7] 卸载')
out, _ = sudo('sync'); print('sync:', out or '(ok)')
out, _ = sudo(f'umount {MOUNT_POINT}'); print('umount:', out or '(ok)')
out, _ = sudo('sync && losetup -D 2>/dev/null'); print('losetup:', out or '(ok)')

# ========== 8) 重新下载 ==========
section('[8] 重新下载到本地')
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