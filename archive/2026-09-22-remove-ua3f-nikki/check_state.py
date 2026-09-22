"""检查服务器状态,确认上传是否完成"""
import paramiko
HOST = '<YOUR_BUILD_SERVER_IP>'
USER = os.environ.get('OPENWRT_BUILD_USER', 'your_username')
PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_SSH_PASSWORD>')
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS, timeout=10)

for cmd in [
    'ls -lh /home/lg/openwrt-build/openwrt_V5/openwrt-base-frpc-20260822.img 2>&1',
    'ls -lh /home/lg/openwrt-build/openwrt_V5/openwrt-final.img 2>&1',
    'mount | grep backup-openwrt || echo NOT_MOUNTED',
    'ls /mnt/backup-openwrt/ 2>&1 | head -5',
]:
    si, so, se = client.exec_command(cmd, timeout=15)
    print(f'>>> {cmd}')
    print(so.read().decode('utf-8', 'replace').strip())
    print()

client.close()