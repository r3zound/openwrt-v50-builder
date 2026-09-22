import paramiko
HOST = '<YOUR_BUILD_SERVER_IP>'
USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username')
PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS, timeout=10)

cmd = "ls -lh /home/lg/openwrt-build/openwrt_V5/ 2>&1 | head -40"
si, so, se = client.exec_command(cmd, timeout=15)
print('=== 目录 ===')
print(so.read().decode('utf-8', 'replace').strip())
print(se.read().decode('utf-8', 'replace').strip())

cmd = "find /home/lg/openwrt-build -maxdepth 4 -name 'openwrt-V50-frpc*' 2>/dev/null"
si, so, se = client.exec_command(cmd, timeout=15)
print('\n=== 找 frpc 镜像 ===')
print(so.read().decode('utf-8', 'replace').strip())

# 还要确认镜像是否还挂载着
cmd = "mount | grep backup-openwrt || echo NOT_MOUNTED"
si, so, se = client.exec_command(cmd, timeout=15)
print('\n=== 当前挂载状态 ===')
print(so.read().decode('utf-8', 'replace').strip())

client.close()