---
name: "openwrt-firmware-builder"
description: "Build OpenWrt firmware for ZTE MU3351/V50 (ARMv8) using template injection on remote Ubuntu server. Invoke when user asks to build/compile OpenWrt firmware, add packages to firmware image, or modify OpenWrt rootfs."
---

# OpenWrt 固件构建技能 — ZTE MU3351/V50 模板注入法

## 服务器信息

```
SSH: <YOUR_BUILD_SERVER_IP> 端口 22
账号: `<YOUR_USER>`
密码: `<YOUR_PASSWORD>`
sudo 密码: `<YOUR_PASSWORD>`
```

## 关键路径

| 路径 | 说明 |
|------|------|
| `/home/lg/openwrt-build/openwrt_V5/` | OpenWrt 25.12.5 源码树（已下载、已配置、可编译） |
| `/home/lg/openwrt-build/openwrt_V5/openwrt-backup-20260813-235659.img` | 模板镜像（1GB ext4，292个包，含 LuCI/PassWall2/Zapret2 等） |
| `/home/lg/openwrt-build/openwrt_V5/openwrt-final.img` | 最终输出镜像 |
| `/mnt/backup-openwrt` | 镜像挂载点 |

## 连接方式

所有操作通过 SSH 远程执行。推荐用 Python paramiko：

```python
import paramiko

HOST = "<YOUR_BUILD_SERVER_IP>"
PORT = 22
USER = "<YOUR_USER>"
PASS = "<YOUR_SUDO_PASSWORD>"
SUDO_PASS = "<YOUR_SUDO_PASSWORD>"
OPENWRT_DIR = "/home/lg/openwrt-build/openwrt_V5"
TEMPLATE_IMG = f"{OPENWRT_DIR}/openwrt-backup-20260813-235659.img"
FINAL_IMG = f"{OPENWRT_DIR}/openwrt-final.img"
MOUNT_POINT = "/mnt/backup-openwrt"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=300):
    """执行远程命令，自动处理 sudo"""
    if "sudo" in cmd:
        cmd = cmd.replace("sudo", f'echo "{SUDO_PASS}" | sudo -S', 1)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err
```

## 构建方法：模板注入法

**核心思路**：以备份的 ext4 镜像为基底，只编译需要的新包，解压后复制到镜像中。不做从零全量编译。

原因：
1. 第三方包（PassWall2、UA3F、Zapret2）的 feeds 源不固定
2. `/opt/zapret2` 是手动安装的，不在包管理器中
3. ZTE 定制脚本（rc.local、init.d/）是自定义的
4. 全量编译耗时数小时且容易出错

## 完整构建流程（7步）

### 步骤1：复制模板镜像

```bash
cp /home/lg/openwrt-build/openwrt_V5/openwrt-backup-20260813-235659.img \
   /home/lg/openwrt-build/openwrt_V5/openwrt-final.img
```

### 步骤2：编译需要的包（单线程！）

```bash
cd /home/lg/openwrt-build/openwrt_V5

# 在 .config 中启用需要的包（如果尚未启用）
# 方法1: 直接编辑 .config 加 CONFIG_PACKAGE_xxx=y 然后 make defconfig
# 方法2: 用 make menuconfig 交互选择

# 编译（必须单线程 -j1，并行会导致竞态错误）
make package/<包名>/compile V=s -j1
```

### 步骤3：查找编译产物

```bash
# APK 包位于 bin/packages/ 下，按架构和 feed 分类
find /home/lg/openwrt-build/openwrt_V5/bin/ -name "*.apk" | grep <包名>
```

### 步骤4：挂载镜像（必须用 ext4！）

```bash
echo "$SUDO_PASS" | sudo -S mount -o loop -t ext4 \
    /home/lg/openwrt-build/openwrt_V5/openwrt-final.img \
    /mnt/backup-openwrt
```

### 步骤5：解压 APK 并注入文件

```bash
# 创建临时解压目录
echo "$SUDO_PASS" | sudo -S mkdir -p /tmp/extract

# 解压 APK（必须用 --zstd，不是 -z！OpenWrt 25.x 的 APK 是 zstd 压缩）
echo "$SUDO_PASS" | sudo -S tar --zstd -xf <apk文件路径> -C /tmp/extract

# 复制文件到镜像（排除 .PKGINFO 等元数据文件）
echo "$SUDO_PASS" | sudo -S cp -rv /tmp/extract/* /mnt/backup-openwrt/

# 如果有 init 脚本，启用服务
echo "$SUDO_PASS" | sudo -S ln -sf ../init.d/<服务名> /mnt/backup-openwrt/etc/rc.d/S99<服务名>

# 修正设备型号（如果模板中型号不对）
echo "$SUDO_PASS" | sudo -S sed -i 's/ZTE MU5358 (UMS9632)/ZTE MU3351 \/ V50/g' /mnt/backup-openwrt/etc/rc.local
```

### 步骤6：卸载镜像（必须 sync！）

```bash
echo "$SUDO_PASS" | sudo -S sync
echo "$SUDO_PASS" | sudo -S umount /mnt/backup-openwrt
echo "$SUDO_PASS" | sudo -S sync
echo "$SUDO_PASS" | sudo -S losetup -D
```

### 步骤7：下载镜像到本地

```python
sftp = client.open_sftp()

# progress callback 用字典包装避免 nonlocal 问题
state = {'last_pct': -1}
def progress(transferred, total):
    pct = int(transferred * 100 / total)
    if pct != state['last_pct'] and pct % 10 == 0:
        state['last_pct'] = pct
        print(f"\r  {pct}% ({transferred/(1024*1024):.1f}/{total/(1024*1024):.1f} MB)", end="", flush=True)

sftp.get(
    "/home/lg/openwrt-build/openwrt_V5/openwrt-final.img",
    r"D:\local\path\openwrt-final.img",
    callback=progress
)
client.close()
```

## 模板镜像内容（必须保留的组件）

### 核心系统
- base-files, busybox, procd, uci, apk-tools, fstools
- dropbear (SSH), dnsmasq-full (DNS/DHCP), firewall4 (nftables)

### LuCI Web 界面
- luci-base, luci-mod-admin-full, uhttpd, rpcd-mod-luci
- **主题**: luci-theme-aurora, luci-theme-bootstrap
- **汉化**: luci-i18n-*-zh-cn 全部中文包
- **应用**: luci-app-firewall, luci-app-passwall2, luci-app-nikki, luci-app-package-manager

### 代理/反审查
- PassWall2 + passwall2-server
- UA3F（UA 伪装）
- nikki + hiddify-core（Hiddify 面板）
- mihomo-alpha（Clash 内核）
- v2ray-geoip, v2ray-geosite

### Zapret2 反 DPI（手动安装，位于 /opt/）
- /opt/zapret2/nfq2/nfqws2 (317KB 核心二进制)
- /opt/zapret2/lua/zapret-antidpi.lua.gz
- /opt/zapret2/blockcheck2.d/ (TLS/QUIC/HTTP 伪装模式)
- /opt/zapret2/ipset/ (域名与 IP 封锁列表)

### ZTE 定制 rc.local 脚本（必须保留！）

```bash
# 1. 设备型号伪装
echo "ZTE MU3351 / V50" > /tmp/sysinfo/model

# 2. 固定 br-lan MAC 地址（避免 crosvm 重启 MAC 变化）
ip link set br-lan address 02:00:00:00:88:01

# 3. IPv6 模式切换（passthrough vs managed）
# 读取 /proc/cmdline 中 owrt_ipv6_passthrough 参数

# 4. 自动扩容（Android 下的稀疏文件首次开机扩展）
resize2fs /dev/vda
```

### 自定义服务（/etc/init.d/）

| 服务 | 说明 |
|------|------|
| zapret2 | 反 DPI 启动脚本 |
| passwall2 + passwall2_server | 代理服务 |
| ua3f | UA 伪装 |
| nikki | Hiddify 面板 |
| hiddify | 核心支持 |
| owrt-runtime-network | Android VM 运行时网络 |

## 验证清单

挂载镜像后逐项检查：

```bash
# 1. 新注入的包二进制（应为 ELF 64-bit ARM aarch64，非 shell 脚本）
file /mnt/backup-openwrt/usr/bin/<二进制名>

# 2. init 脚本
ls -la /mnt/backup-openwrt/etc/init.d/<服务名>

# 3. LuCI 界面文件
ls /mnt/backup-openwrt/www/luci-static/resources/view/<应用名>.js
cat /mnt/backup-openwrt/usr/share/luci/menu.d/luci-app-<应用名>.json
ls /mnt/backup-openwrt/usr/share/rpcd/acl.d/luci-app-<应用名>.json

# 4. 设备型号
grep "ZTE" /mnt/backup-openwrt/etc/rc.local

# 5. 原始组件完整性
ls /mnt/backup-openwrt/opt/zapret2/nfq2/          # Zapret2
ls /mnt/backup-openwrt/etc/init.d/passwall2        # PassWall2
ls /mnt/backup-openwrt/etc/init.d/ua3f             # UA3F
ls /mnt/backup-openwrt/etc/init.d/nikki           # nikki
ls /mnt/backup-openwrt/www/luci-static/aurora/     # aurora 主题
ls /mnt/backup-openwrt/www/luci-static/bootstrap/  # bootstrap 主题
ls /mnt/backup-openwrt/usr/sbin/resize2fs         # resize2fs
```

## 必须遵守的规则（10 条铁律）

1. **镜像大小固定 1024MB** — 与 Android 虚拟机的磁盘配置匹配，不可改变
2. **文件系统必须 ext4** — 挂载用 `mount -t ext4`，不能用 ext2
3. **编译必须单线程** — `make -j1 V=s`，并行会导致 grub2-efi-arm 等包竞态错误
4. **APK 解压用 zstd** — `tar --zstd -xf`，不是 `tar xzf`（APKv3 格式）
5. **卸载前必须 sync** — `sudo sync` 确保数据写入磁盘
6. **sudo 用 -S 传密码** — `echo "$SUDO_PASS" | sudo -S <cmd>`，非交互式
7. **源码下载用 codeload** — 不用 `git clone`（GitHub 连接不稳定）
8. **设备型号必须是 ZTE MU3351 / V50** — 不能写错（影响设备识别）
9. **br-lan MAC 固定 02:00:00:00:88:01** — 避免 crosvm 重启 MAC 变化
10. **不要全量编译** — 只 `make package/xxx/compile` 编译需要的包

## 常见错误速查表

| 错误 | 原因 | 解决 |
|------|------|------|
| `git clone` 超时 | GitHub 连接不稳定 | 用 `wget https://codeload.github.com/openwrt/openwrt/tar.gz/refs/tags/v25.12.5` |
| `E: 软件包 python3-distutils 没有候选` | Ubuntu 26.04 无此包 | 用 `python3-setuptools` 替代 |
| `E: 无法定位 python33-pyelftools` | 包名拼写错误 | 正确为 `python3-pyelftools` |
| `make Error 2 (package_compile)` | 并行构建竞态 | 用 `make -j1 V=s` 单线程 |
| `mount: wrong fs type` | 用 ext2 挂载 ext4 | 用 `mount -t ext4` |
| `tar: not in gzip format` (APK) | APKv3 用 zstd 压缩 | 用 `tar --zstd -xf` |
| `nonlocal: no binding` (paramiko) | Python 闭包问题 | 用字典变量替代 nonlocal |
| GNU 镜像 502 | 临时网络问题 | 多重试几次 |
| frpc 二进制只有 1.7KB | 是 shell 脚本包装 | 从 `build_dir` 找 ELF 二进制 |
| `sudo: A terminal is required` | sudo 需要终端 | 用 `echo "密码" \| sudo -S` |
| `losetup` 设备泄漏 | 未清理 loop 设备 | 卸载后执行 `sudo losetup -D` |

## 完整 Python 构建脚本模板

```python
import paramiko
import os
import time

# ==================== 配置 ====================
HOST = "<YOUR_BUILD_SERVER_IP>"
PORT = 22
USER = "<YOUR_USER>"
PASS = "<YOUR_SUDO_PASSWORD>"
SUDO_PASS = "<YOUR_SUDO_PASSWORD>"
OPENWRT_DIR = "/home/lg/openwrt-build/openwrt_V5"
TEMPLATE_IMG = f"{OPENWRT_DIR}/openwrt-backup-20260813-235659.img"
FINAL_IMG = f"{OPENWRT_DIR}/openwrt-final.img"
MOUNT_POINT = "/mnt/backup-openwrt"

# 要注入的包列表（在 .config 中已有 CONFIG_PACKAGE_xxx=y）
PACKAGES_TO_COMPILE = [
    "frpc",
    "luci-app-frpc",
]

# ==================== 工具函数 ====================
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=300):
    """执行远程命令，自动处理 sudo"""
    if "sudo" in cmd:
        cmd = cmd.replace("sudo", f'echo "{SUDO_PASS}" | sudo -S', 1)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def run_long(cmd, timeout=3600):
    """执行长时间命令，用 invoke_shell"""
    shell = client.invoke_shell()
    shell.send(cmd + '\n')
    time.sleep(2)
    output = ""
    start = time.time()
    while time.time() - start < timeout:
        if shell.recv_ready():
            data = shell.recv(4096).decode('utf-8', errors='replace')
            output += data
            if "Error" in data or "error" in data:
                print(f"  ⚠️  {data.strip()}")
        if shell.exit_status_ready():
            break
        time.sleep(1)
    shell.close()
    return output

# ==================== 构建流程 ====================

# 步骤1: 编译包
for pkg in PACKAGES_TO_COMPILE:
    print(f"[编译] {pkg}...")
    out = run_long(f"cd {OPENWRT_DIR} && make package/{pkg}/compile V=s -j1", timeout=600)
    print(f"  ✅ {pkg} 编译完成")

# 步骤2: 查找 APK 产物
out, _ = run(f"find {OPENWRT_DIR}/bin/ -name '*.apk' | sort")
print(f"\nAPK 产物:\n{out}")

# 步骤3: 复制模板镜像
print("\n[复制模板镜像...]")
run(f"cp {TEMPLATE_IMG} {FINAL_IMG}")
print("  ✅ 模板已复制")

# 步骤4: 挂载镜像
print("[挂载镜像...]")
run(f'echo "{SUDO_PASS}" | sudo -S mkdir -p {MOUNT_POINT}')
run(f'echo "{SUDO_PASS}" | sudo -S mount -o loop -t ext4 {FINAL_IMG} {MOUNT_POINT}')
out, _ = run(f'ls {MOUNT_POINT}/')
print(f"  ✅ 已挂载: {out[:50]}...")

# 步骤5: 解压 APK 并注入
print("[注入包文件...]")
run(f'echo "{SUDO_PASS}" | sudo -S rm -rf /tmp/extract && sudo mkdir -p /tmp/extract')

for pkg in PACKAGES_TO_COMPILE:
    out, _ = run(f"find {OPENWRT_DIR}/bin/ -name '{pkg}*.apk' | head -1")
    if not out:
        # 尝试从 build_dir 找二进制
        print(f"  ⚠️  {pkg} APK 未找到，检查 build_dir...")
        continue
    
    apk_path = out.split('\n')[0]
    print(f"  解压: {apk_path}")
    run(f'echo "{SUDO_PASS}" | sudo -S tar --zstd -xf {apk_path} -C /tmp/extract')

# 复制文件到镜像（排除元数据）
run(f'echo "{SUDO_PASS}" | sudo -S cp -rv /tmp/extract/usr/* {MOUNT_POINT}/usr/ 2>/dev/null')
run(f'echo "{SUDO_PASS}" | sudo -S cp -rv /tmp/extract/etc/* {MOUNT_POINT}/etc/ 2>/dev/null')
run(f'echo "{SUDO_PASS}" | sudo -S cp -rv /tmp/extract/www/* {MOUNT_POINT}/www/ 2>/dev/null')
run(f'echo "{SUDO_PASS}" | sudo -S cp -rv /tmp/extract/opt/* {MOUNT_POINT}/opt/ 2>/dev/null')
print("  ✅ 文件注入完成")

# 启用服务
for pkg in PACKAGES_TO_COMPILE:
    # 检查是否有 init 脚本
    out, _ = run(f'ls {MOUNT_POINT}/etc/init.d/{pkg} 2>/dev/null')
    if out:
        run(f'echo "{SUDO_PASS}" | sudo -S ln -sf ../init.d/{pkg} {MOUNT_POINT}/etc/rc.d/S99{pkg}')
        print(f"  ✅ 服务 {pkg} 已启用")

# 修正设备型号
run(f'echo "{SUDO_PASS}" | sudo -S sed -i \'s/ZTE MU5358 (UMS9632)/ZTE MU3351 \\/ V50/g\' {MOUNT_POINT}/etc/rc.local')
print("  ✅ 设备型号已修正")

# 步骤6: 卸载镜像
print("[卸载镜像...]")
run(f'echo "{SUDO_PASS}" | sudo -S sync')
run(f'echo "{SUDO_PASS}" | sudo -S umount {MOUNT_POINT}')
run(f'echo "{SUDO_PASS}" | sudo -S sync')
run(f'echo "{SUDO_PASS}" | sudo -S losetup -D')
print("  ✅ 镜像已卸载")

# 步骤7: 下载到本地
print("[下载镜像到本地...]")
sftp = client.open_sftp()
LOCAL_PATH = r"D:\output\openwrt-final.img"

state = {'last_pct': -1}
def progress(transferred, total):
    pct = int(transferred * 100 / total)
    if pct != state['last_pct'] and pct % 10 == 0:
        state['last_pct'] = pct
        print(f"\r  {pct}% ({transferred/(1024*1024):.1f}/{total/(1024*1024):.1f} MB)", end="", flush=True)

sftp.get(FINAL_IMG, LOCAL_PATH, callback=progress)
print(f"\n  ✅ 下载完成: {LOCAL_PATH}")

client.close()
print("\n✅ 全部完成！")
```

## 从零编译（仅在源码树损坏时使用）

```bash
# 1. 安装依赖
echo "$SUDO_PASS" | sudo -S apt update
echo "$SUDO_PASS" | sudo -S apt install -y build-essential clang flex bison gperf gawk \
    git wget unzip rsync subversion gettext \
    libncurses-dev libssl-dev zlib1g-dev \
    python3 python3-setuptools python3-pyelftools xxd zstd
pip3 install setuptools pyelftools

# 2. 下载源码（用 codeload tarball，不用 git clone）
cd /home/lg/openwrt-build
wget https://codeload.github.com/openwrt/openwrt/tar.gz/refs/tags/v25.12.5 -O openwrt-25.12.5.tar.gz
tar xzf openwrt-25.12.5.tar.gz
mv openwrt-25.12.5 openwrt_V5
rm openwrt-25.12.5.tar.gz
cd openwrt_V5

# 3. 更新 feeds
./scripts/feeds update -a
./scripts/feeds install -a

# 4. 配置目标
cat > .config << 'EOF'
CONFIG_TARGET_armsr=y
CONFIG_TARGET_armsr_armv8=y
CONFIG_TARGET_armsr_armv8_DEVICE_generic=y
CONFIG_PACKAGE_base-files=y
CONFIG_PACKAGE_busybox=y
CONFIG_PACKAGE_dropbear=y
CONFIG_PACKAGE_dnsmasq=y
CONFIG_PACKAGE_firewall4=y
CONFIG_PACKAGE_luci=y
EOF
make defconfig

# 5. 编译（单线程！）
make -j1 V=s
```

## 依赖安装注意事项

- Ubuntu 26.04 没有 `python3-distutils` → 用 `python3-setuptools` 替代
- `python33-pyelftools` 是错误包名 → 正确为 `python3-pyelftools`
- 必须安装 `zstd` → OpenWrt 25.x APK 包用 zstd 压缩
- `pip3 install setuptools pyelftools` → 确保 Python 工具链完整
