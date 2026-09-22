# OpenWrt 固件构建教程 — ZTE MU3351/V50 (ARMv8)

> 本教程详细介绍了如何为 ZTE MU3351/V50 设备构建 OpenWrt 固件，采用模板注入法，避免从零编译的复杂性和网络问题。

---

## 一、概述

### 1.1 目标设备

| 项目 | 说明 |
|------|------|
| 设备型号 | ZTE MU3351 / V50 |
| 架构 | ARMv8 (armsr/armv8) |
| 运行方式 | Android 底层 Linux 虚拟机运行 OpenWrt |
| OpenWrt 版本 | 25.12.5 |
| 内核版本 | 6.12.94 |

### 1.2 构建方法：模板注入法

**为什么不用从零编译？**

1. 第三方包（PassWall2、UA3F、Zapret2 等）需要额外的 feeds 源，且源地址不固定
2. `/opt/zapret2` 是手动安装的，不在任何包管理器中
3. ZTE 定制脚本（rc.local、init.d/）是自定义的，编译不会包含
4. 编译耗时长（数小时），且容易出现并行构建错误

**模板注入法**：以备份镜像为基底，只编译需要的新包，解压后复制到镜像中。

---

## 二、环境要求

### 2.1 编译服务器

| 项目 | 要求 |
|------|------|
| 系统 | Ubuntu 22.04+（推荐 24.04/26.04 LTS） |
| 内存 | ≥ 8GB（推荐 16GB+） |
| 磁盘 | ≥ 50GB 可用空间 |
| CPU | 多核（用于加速编译） |
| 网络 | 需访问 GitHub（codeload.github.com）和 GNU 镜像 |

### 2.2 依赖安装

```bash
sudo apt update
sudo apt install -y build-essential clang flex bison gperf gawk \
    git wget unzip rsync subversion gettext \
    libncurses-dev libssl-dev zlib1g-dev \
    python3 python3-setuptools python3-pyelftools \
    xxd zstd
pip3 install setuptools pyelftools
```

> **注意**：Ubuntu 26.04 没有 `python3-distutils` 包，用 `python3-setuptools` 替代。
> **注意**：`python33-pyelftools` 是错误包名，正确为 `python3-pyelftools`。
> **注意**：必须安装 `zstd`，OpenWrt 25.x 的 APK 包使用 zstd 压缩。

### 2.3 关键路径

| 路径 | 说明 |
|------|------|
| `<BUILD_DIR>/openwrt_V5/` | OpenWrt 源码和编译产物 |
| `<BUILD_DIR>/openwrt_V5/openwrt-backup-XXXXXX.img` | 模板镜像（1GB ext4） |
| `<BUILD_DIR>/openwrt_V5/openwrt-final.img` | 最终输出镜像 |
| `/mnt/backup-openwrt` | 镜像挂载点 |

> 将 `<BUILD_DIR>` 替换为你的实际构建目录路径。

---

## 三、模板镜像结构

### 3.1 镜像格式

- **文件系统**：ext4（挂载时必须用 `mount -t ext4`）
- **大小**：1024 MB（固定，不可改变）
- **分区表**：无（原始文件系统镜像，非 GPT/MBR 分区镜像）
- **卷标**：rootfs
- **块大小**：4096 字节

### 3.2 模板包含的关键组件

#### 核心系统
- base-files, busybox, procd, uci, apk-tools, fstools
- dropbear（SSH）, dnsmasq-full（DNS/DHCP）, firewall4（nftables）

#### LuCI Web 界面
- luci-base, luci-mod-admin-full, uhttpd, rpcd-mod-luci
- **主题**：luci-theme-aurora, luci-theme-bootstrap
- **汉化**：luci-i18n-*-zh-cn 全部中文包
- **应用**：luci-app-firewall, luci-app-passwall2, luci-app-nikki 等

#### 代理/反审查
- PassWall2 + passwall2-server
- UA3F（UA 伪装）
- nikki + hiddify-core（Hiddify 面板）
- mihomo-alpha（Clash 内核）
- Zapret2（反 DPI，位于 /opt/zapret2/）

#### 网络工具
- curl, ipset, ip-full, tcping
- iptables-mod-tproxy, kmod-ipt-tproxy

#### 文件系统
- resize2fs（首次开机自动扩容稀疏文件）
- e2fsprogs, coreutils-*, gzip, unzip

### 3.3 ZTE 定制 rc.local 脚本

模板镜像的 `/etc/rc.local` 包含以下关键定制：

```bash
# 1. 设备型号伪装
echo "ZTE MU3351 / V50" > /tmp/sysinfo/model

# 2. 固定 br-lan MAC 地址（避免虚拟机重启 MAC 变化）
ip link set br-lan address 02:00:00:00:88:01

# 3. IPv6 模式切换（passthrough vs managed）
# 读取 /proc/cmdline 中 owrt_ipv6_passthrough 参数

# 4. 自动扩容（稀疏文件首次开机扩展）
resize2fs /dev/vda
```

### 3.4 自定义服务

| 服务 | 路径 | 说明 |
|------|------|------|
| zapret2 | /etc/init.d/zapret2 | 反 DPI 启动脚本 |
| passwall2 | /etc/init.d/passwall2 | 代理服务 |
| ua3f | /etc/init.d/ua3f | UA 伪装 |
| nikki | /etc/init.d/nikki | Hiddify 面板 |
| owrt-runtime-network | /etc/init.d/owrt-runtime-network | Android VM 运行时网络 |

---

## 四、构建流程

### 4.1 步骤一：下载 OpenWrt 源码

```bash
cd <BUILD_DIR>

# 用 codeload tarball 下载（比 git clone 更稳定）
wget https://codeload.github.com/openwrt/openwrt/tar.gz/refs/tags/v25.12.5 -O openwrt-25.12.5.tar.gz
tar xzf openwrt-25.12.5.tar.gz
mv openwrt-25.12.5 openwrt_V5
rm openwrt-25.12.5.tar.gz
cd openwrt_V5
```

> **注意**：`git clone https://github.com/openwrt/openwrt.git` 经常因网络超时失败。用 `codeload.github.com` 的 tarball 下载更稳定。

### 4.2 步骤二：更新 feeds

```bash
./scripts/feeds update -a
./scripts/feeds install -a
```

> **注意**：feeds 更新时如果 GNU 镜像返回 502，多重试几次即可。

### 4.3 步骤三：配置编译目标

```bash
# 设置目标：armsr/armv8
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
CONFIG_PACKAGE_luci-app-frpc=y
CONFIG_PACKAGE_frpc=y
EOF

make defconfig
```

> **注意**：不要在 .config 中写 shell 语法（如 `if false then`），会报语法错误。
> 用 `make defconfig` 自动解析依赖关系。

### 4.4 步骤四：编译需要的包（单线程）

```bash
# 只编译需要的包，不要全量编译
make package/frpc/compile V=s -j1
make package/luci-app-frpc/compile V=s -j1
```

> **注意**：并行编译（`make -j$(nproc)`）会导致 grub2-efi-arm 等包的竞态条件。
> 用 `make -j1 V=s` 单线程编译，虽然慢但不会出错。

### 4.5 步骤五：查找编译产物

```bash
# APK 包位于 bin/packages/ 下，按架构和 feed 分类
find bin/ -name "*.apk" | grep -i frp | sort
# 示例输出：
# bin/packages/aarch64_generic/packages/frpc-0.66.0-r1.apk
# bin/packages/aarch64_generic/luci/luci-app-frpc-*.apk
```

> **APK 文件格式**：OpenWrt 25.x 使用 APKv3 格式（文件头 `ADBd`），非 gzip tar。
> 解压方法：`tar --zstd -xf xxx.apk`（需要 zstd 支持）

### 4.6 步骤六：复制模板并注入包

```bash
# 1. 复制模板镜像
cp <BUILD_DIR>/openwrt_V5/openwrt-backup-XXXXXX.img \
   <BUILD_DIR>/openwrt_V5/openwrt-final.img

# 2. 挂载镜像（必须用 ext4）
sudo mount -o loop -t ext4 openwrt-final.img /mnt/backup-openwrt

# 3. 解压 APK 包
sudo mkdir -p /tmp/frpc_extract /tmp/luci_extract

sudo tar --zstd -xf bin/packages/aarch64_generic/packages/frpc-*.apk -C /tmp/frpc_extract
sudo tar --zstd -xf bin/packages/aarch64_generic/luci/luci-app-frpc-*.apk -C /tmp/luci_extract

# 4. 复制文件到镜像（排除元数据文件）
sudo cp -v /tmp/frpc_extract/usr/bin/frpc /mnt/backup-openwrt/usr/bin/frpc
sudo chmod +x /mnt/backup-openwrt/usr/bin/frpc

sudo cp -rv /tmp/luci_extract/usr/share/luci/* /mnt/backup-openwrt/usr/share/luci/
sudo cp -rv /tmp/luci_extract/www/* /mnt/backup-openwrt/www/
sudo cp -rv /tmp/luci_extract/etc/* /mnt/backup-openwrt/etc/

# 5. 启用 frpc 服务
sudo ln -sf ../init.d/frpc /mnt/backup-openwrt/etc/rc.d/S99frpc

# 6. 卸载镜像（必须 sync）
sudo sync
sudo umount /mnt/backup-openwrt
sudo sync
sudo losetup -D
```

> **注意**：挂载时必须用 `-t ext4`，用 ext2 会报 "wrong fs type" 错误。
> **注意**：卸载前必须 `sync`，否则数据可能未写入磁盘。

### 4.7 步骤七：下载最终镜像

使用 SFTP 工具（如 paramiko、FileZilla、scp）将服务器上的 `openwrt-final.img` 下载到本地。

```python
# Python + paramiko 示例
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('<SERVER_IP>', port=22, username='<USER>', password='<PASSWORD>')
sftp = client.open_sftp()

# progress callback 用字典包装避免 nonlocal 问题
state = {'last_pct': -1}
def progress(transferred, total):
    pct = int(transferred * 100 / total)
    if pct != state['last_pct'] and pct % 10 == 0:
        state['last_pct'] = pct
        print(f"\r  {pct}% ({transferred/(1024*1024):.1f}/{total/(1024*1024):.1f} MB)", end="")

sftp.get('/remote/path/openwrt-final.img', '/local/path/openwrt-final.img', callback=progress)
client.close()
```

> **注意**：paramiko 的 `nonlocal` 在某些 Python 版本中不工作，用字典变量替代。

---

## 五、验证清单

编译完成后，挂载镜像逐项检查：

```bash
sudo mount -o loop -t ext4 openwrt-final.img /mnt/backup-openwrt

# 1. frpc 二进制（应为 ELF 64-bit ARM aarch64）
sudo file /mnt/backup-openwrt/usr/bin/frpc

# 2. frpc init 脚本
sudo ls -la /mnt/backup-openwrt/etc/init.d/frpc

# 3. frpc UCI 配置
sudo cat /mnt/backup-openwrt/etc/config/frpc

# 4. LuCI frpc 界面文件
sudo ls /mnt/backup-openwrt/www/luci-static/resources/view/frpc.js

# 5. LuCI frpc 菜单
sudo cat /mnt/backup-openwrt/usr/share/luci/menu.d/luci-app-frpc.json

# 6. 设备型号
sudo grep "ZTE" /mnt/backup-openwrt/etc/rc.local

# 7. 原始组件完整性
sudo ls /mnt/backup-openwrt/opt/zapret2/nfq2/          # Zapret2
sudo ls /mnt/backup-openwrt/etc/init.d/passwall2        # PassWall2
sudo ls /mnt/backup-openwrt/etc/init.d/ua3f             # UA3F
sudo ls /mnt/backup-openwrt/etc/init.d/nikki            # nikki
sudo ls /mnt/backup-openwrt/www/luci-static/aurora/     # aurora 主题
sudo ls /mnt/backup-openwrt/www/luci-static/bootstrap/  # bootstrap 主题
sudo ls /mnt/backup-openwrt/usr/sbin/resize2fs          # resize2fs

sudo umount /mnt/backup-openwrt
```

---

## 六、常见错误与解决方案

| 错误 | 原因 | 解决 |
|------|------|------|
| `fatal: 无法访问 github.com` | GitHub 连接被墙 | 用 `codeload.github.com` tarball 下载 |
| `E: 软件包 python3-distutils 没有候选` | Ubuntu 26.04 无此包 | 改用 `python3-setuptools` |
| `E: 无法定位 python33-pyelftools` | 包名拼写错误 | 正确为 `python3-pyelftools` |
| `make Error 2 (package_compile)` | 并行构建竞态 | 用 `make -j1 V=s` 单线程 |
| `mount: wrong fs type` | 用 ext2 挂载 ext4 | 用 `mount -t ext4` |
| `tar: not in gzip format`（APK） | APKv3 用 zstd 压缩 | 用 `tar --zstd -xf` |
| `nonlocal: no binding`（paramiko） | Python 闭包问题 | 用字典变量替代 nonlocal |
| GNU 镜像 502 | 临时网络问题 | 多重试几次 |
| frpc 二进制只有 1.7KB | 是 shell 脚本包装 | 从 build_dir 找 ELF 二进制 |

---

## 七、新增包快速注入流程

当需要向模板添加新的 OpenWrt 包时：

```bash
# 1. 编译包
cd <BUILD_DIR>/openwrt_V5
make package/<包名>/compile V=s -j1

# 2. 找到 APK 产物
find bin/ -name "*.apk" | grep <包名>

# 3. 复制模板
cp openwrt-backup-XXXXXX.img openwrt-final.img

# 4. 挂载
sudo mount -o loop -t ext4 openwrt-final.img /mnt/backup-openwrt

# 5. 解压 APK 并注入
sudo tar --zstd -xf <apk-path> -C /tmp/extract
sudo cp -rv /tmp/extract/* /mnt/backup-openwrt/

# 6. 卸载
sudo sync && sudo umount /mnt/backup-openwrt && sudo sync
```

---

## 八、注意事项

1. **不要改变镜像大小**：固定 1024MB，与 Android 虚拟机的磁盘配置匹配。
2. **不要改变文件系统**：ext4，挂载和卸载都用 `ext4` 类型。
3. **保留 ZTE 定制脚本**：rc.local 和 init.d/ 中的自定义服务是设备正常运行的关键。
4. **设备型号**：必须是 `ZTE MU3351 / V50`，不能写错。
5. **MAC 地址**：br-lan 必须固定为 `02:00:00:00:88:01`。
6. **resize2fs**：必须保留，首次开机自动扩容稀疏文件。
7. **编译用单线程**：`make -j1 V=s`，避免并行竞态。
8. **APK 解压**：用 `tar --zstd -xf`，不是 `tar xzf`。
9. **卸载前 sync**：`sudo sync` 确保所有数据写入磁盘。
10. **sudo 认证**：非交互式用 `echo "密码" | sudo -S`。

---

*本教程基于 OpenWrt 25.12.5 + ZTE MU3351/V50 模板镜像，采用模板注入法构建。*
