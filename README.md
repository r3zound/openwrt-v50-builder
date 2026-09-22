# openwrt-v50-builder

> **本项目用于：构建可在 ZTE MU3351 / V50 等中兴系 CPE 设备内置的 Android 虚拟机（crosvm）中运行的 OpenWrt 固件包。**
>
> Build customized OpenWrt firmware images for ZTE MU3351 / V50 and similar ZTE CPE devices' Android-VM (crosvm) runtime.

针对运行在 **ZTE 中兴 CPE（MU3351 / V50 及同系列）内置 Android 虚拟机** 中的 OpenWrt 25.12.5 固件构建工具。通过 GitHub Actions 从上游 OpenWrt 源码编译，输出 ext4 rootfs 并发布到 GitHub Releases，可直接刷入设备的 VM 磁盘。

---

> ## 🚀 在线定制固件(免 PAT)
>
> 👉 **<https://r3zound.github.io/openwrt-v50-builder/>**
>
> 勾选插件 → 一键复制 inputs 到剪贴板 → 跳到 GitHub Actions 页面点 **Run workflow** 即可触发构建。
> 整个流程**完全不需要 GitHub token**,GitHub 用你自己的登录态校验权限。
> 详细使用流程见下方 [「图形化定制」](#4-图形化定制可选) 章节。

---

## 设备背景 / Target hardware

本项目输出的固件用于**以下部署场景**：

- **物理设备**：ZTE MU3351 / V50 系列 CPE（家用路由器/4G CPE）
- **运行环境**：设备内部 Android 系统，通过 `crosvm` 启动一个 Linux 客户机
- **客户机系统**：OpenWrt 25.12.5（ARMv8，用户态基于 musl libc + APK 包管理）
- **镜像格式**：1 GB ext4，无分区表；首次启动由 `resize2fs /dev/vda` 自动扩容稀疏文件

| 项目 | 值 / Value |
|------|-----------|
| 设备型号 | ZTE MU3351 / V50 |
| CPU 架构 | ARMv8 (`armsr/armv8`, aarch64) |
| 内核版本 | Linux 6.12.94 |
| OpenWrt 版本 | 25.12.5 |
| 镜像大小 | 1024 MB（固定，sparse ext4） |
| 包管理器 | APK (apkoviv3, zstd 压缩) |

---

## 项目用途 / What this project does

1. **拉取上游 OpenWrt 源码**（v25.12.5 默认，可换 tag）
2. **应用默认编译配方**（`config/default.config`，从你的设备镜像里摘取）
3. **允许手动加入/移除软件包**（workflow_dispatch inputs）
4. **从源码完整编译**（`make -j1 V=s`，约 2-4 小时）
5. **输出 ext4 rootfs + .gz + SHA256SUMS**，发布到 GitHub Release

⚠️ **说明**：CI 输出的 rootfs **不是开箱即用的 V50 镜像**。要变成可烧录的 1GB V50 镜像，需要额外注入 `rc.local`（型号伪装 + br-lan MAC 固定 + resize2fs）等 ZTE 定制（详见下方"已知缺口"章节）。

---

## 快速上手 / Quick start

### 1. 在 GitHub 网页触发一次构建

前往 https://github.com/r3zound/openwrt-v50-builder/actions → "build-v50-firmware" → **Run workflow**。

可用输入参数：

| Input | 类型 | 默认 | 说明 |
|-------|------|------|------|
| `release_tag` | string | `nightly-<UTC时间戳>` | 自定义 release 标签，如 `v1.2.0` |
| `openwrt_version` | string | `v25.12.5` | 上游 OpenWrt tag |
| `add_packages` | string | 空 | 空格分隔的**包名后缀**（无 `CONFIG_PACKAGE_` 前缀），例：`luci-app-aria2 luci-app-dockerman` |
| `remove_packages` | string | 空 | 同上，从默认 config 中禁用，例：`luci-app-nikki luci-app-ua3f` |
| `prerelease` | choice | `true` | 是否标记为预发布 |

### 2. 自动 schedule

每周一 **02:00 UTC** 自动跑一次（cron `0 2 * * 1`），不需要手动干预。

### 3. 下载产物

构建完成后在 https://github.com/r3zound/openwrt-v50-builder/releases 下载：

- `openwrt-final.img.gz` — 压缩的 rootfs（推荐烧录用）

### 4. 图形化定制（可选）

打开 [`docs/builder.html`](docs/builder.html)（推荐 GitHub Pages 启用后从 `https://r3zound.github.io/openwrt-v50-builder/builder.html` 访问）：

**功能概览**：

- **5 大分类 · 78 个常用包**：代理（PassWall2/Nikki/OpenClash/HomeProxy/SSR-Plus/Mihomo/Momo/v2rayA/Fchomo/NeKoBox/Daed/HiJpass/UA3F/luci-xray）/ LuCI 应用（27 项）/ 主题（12 项）/ 系统工具（17 项，htop/curl/nano/wget/git 默认启用）/ 自定义
- **零认证流程** —— **完全不需要 GitHub PAT**。前端只负责生成 inputs 并复制到剪贴板，自动打开 GitHub Actions 页面，用户在自己登录态下点 Run workflow 即可
- **中文包自动同步** —— 勾选任何 `luci-app-*` 会自动追加 `luci-i18n-<name>-zh-cn`（基于内置白名单映射表），不需要单独选 i18n 包
- **每分类全选/全不选** 一键操作
- **表单自动持久化**（localStorage）—— 刷新页面不丢选项
- **最近 5 个 Releases 列表** —— 通过 GitHub **公开 API** 自动拉取，无需 token

**使用流程**：

1. 在仓库与目标卡片确认 `owner/repo/workflow`（默认已填好本仓库）
2. 勾选要添加的插件（按分类、可全选、可用自定义 textarea 追加任意包名）
3. 在 Release 选项卡点动版本/tag（可选）
4. 点击 **📋 复制 inputs 并打开 GitHub** → 自动复制 inputs 到剪贴板 + 打开 GitHub Actions 页面
6. 在打开的页面点 `Run workflow`，把每个字段粘贴进去即可

整个流程**不接触任何 token** —— GitHub 用你自己的登录态校验权限。如果浏览器拦截弹窗，可手动点 **🔗 仅打开 GitHub Actions** 跳转。

---

## 快速上手 / Quick start

### 1. 在 GitHub 网页触发一次构建
- `openwrt-final.img` — 原始 rootfs（用于检查）
- `SHA256SUMS` — 校验和

---

## 仓库结构 / Repository layout

```
.
├── README.md               # 本文件 / this file
├── AGENTS.md               # AI 协作规则
├── LICENSE                 # MIT 许可证
├── docs/                  # 长期文档（中文为主）+ GitHub Pages 源
│   ├── index.html         #  Pages 落地页（指向 builder.html）
│   ├── builder.html       # 图形化固件定制页（纯前端）
│   ├── SKILL.md           # 构建 skill 完整说明
│   ├── OpenWrt固件构建指南.md
│   └── OpenWrt固件构建教程_脱敏版.md
├── tools/                 # 可复用脚本（脱敏，用环境变量驱动）
│   ├── inject.sh          # 本地后处理：注入 ZTE 定制
│   └── gzip_image.py      # 压缩工具（argparse）
├── archive/               # 一次性脚本，按日期归档
│   └── 2026-09-22-remove-ua3f-nikki/
├── config/
│   └── default.config     # ★ 默认 OpenWrt 编译配方（287KB, 239 个包）
├── credentials/           # 本地留底（git-ignored，绝不提交）
└── .github/workflows/
    └── build.yml          # ★ GitHub Actions CI 流程
```

`credentials/` 目录被 `.gitignore` 排除，只在本地保存未脱敏的原文件。

---

## 编译配方 / Default config

`config/default.config` 是从构建服务器 `/home/lg/openwrt-build/openwrt_V5/.config` 摘取的 OpenWrt 编译配置：

- **大小**：295 KB
- **已启用包**：243 个（`CONFIG_PACKAGE_*=y`）
- **目标**：`armsr/armv8 DEVICE_generic`
- **额外 feeds**：[`config/feeds.conf`](config/feeds.conf) 加了 `passwall2` + `theme_aurora` 两个第三方源
- **可选未启用包**：~4500 个（commented `CONFIG_PACKAGE_* is not set`）

基础包来自 OpenWrt 主仓库 + 标准 feeds；本项目额外启用了：
- [`luci-theme-aurora`](https://github.com/eamonxg/luci-theme-aurora)（来自 `theme_aurora` feed）
- `luci-app-passwall2`（来自 `passwall2` feed）
- `luci-i18n-frpc-zh-cn`、`luci-i18n-passwall2-zh-cn` 中文包

其它第三方包（UA3F、nikki、hiddify-core、mihomo-alpha、Zapret2）**仍需** workflow_dispatch `add_packages` 加上对应名字，或在 `config/default.config` 末尾追加 `CONFIG_PACKAGE_xxx=y`。

### 关键组件概览

- **核心系统**：`base-files`, `busybox`, `procd`, `uci`, `dropbear`, `dnsmasq-full`, `firewall4`
- **LuCI 界面**：`luci-mod-admin-full` + **`luci-theme-aurora`** + `luci-theme-bootstrap` + `luci-light` 主题
- **网络/IPv6**：`odhcp6c`, `odhcpd-ipv6only`, `luci-proto-ipv6`, `luci-proto-ppp`, `ppp-mod-pppoe`
- **LuCI 应用**：`luci-app-firewall`, `luci-app-frpc`, **`luci-app-passwall2`**, `luci-app-package-manager`, `luci-app-attendedsysupgrade`
- **路由数据**：`v2ray-geoip`, `v2ray-geosite`
- **中文 i18n**：`luci-i18n-frpc-zh-cn`, `luci-i18n-passwall2-zh-cn`（其它包的 zh-cn 仍需 `add_packages`）

---

## 内置插件索引 / Bundled package index

按类目整理 `config/default.config` 中所有 243 个启用包（实际清单会随 OpenWrt 版本漂移，以仓库中的 `config/default.config` 为准）：

### 核心 / Core (11)
`base-files`, `busybox`, `procd`, `uci`, `dropbear`, `firewall4`, `fstools`, `rpcd`, `ubox`, `ubus`, `uhttpd`

### LuCI 基础 / LuCI base (12)
`luci-base`, `luci`, `luci-compat`, `luci-lib-base`, `luci-lib-ip`, `luci-lib-jsonc`, `luci-lib-nixio`, `luci-lib-uqr`, `luci-light`, `luci-lua-runtime`, `luci-ssl`, `cgi-io`

### LuCI 模块 / LuCI modules (4)
`luci-mod-admin-full`, `luci-mod-network`, `luci-mod-status`, `luci-mod-system`

### LuCI 协议 / LuCI protocols (2)
`luci-proto-ipv6`, `luci-proto-ppp`

### LuCI 应用 / LuCI apps (4)
`luci-app-attendedsysupgrade`, `luci-app-firewall`, `luci-app-frpc`, `luci-app-package-manager`

### LuCI 主题 / LuCI themes (2)
`luci-theme-aurora`, `luci-theme-bootstrap`

### 通用库 / Libraries (36)
`libc`, `libgcc`, `libpthread`, `librt`, `liblua`, `libubus`, `libuci`, `libubox`, `libblobmsg-json`, `libjson-c`, `libjson-script`, `libnl-tiny`, `libmnl`, `libnftnl`, `libiwinfo`, `libiwinfo-data`, `libuclient`, `libustream-mbedtls`, `libcurl`, `libmbedtls`, `libnghttp2`, `liblucihttp`, `liblucihttp-lua`, `liblucihttp-ucode`, `libuuid`, `libblkid`, `libcomerr`, `libe2p`, `libext2fs`, `libf2fs`, `libss`, `libsmartcols`, `libyaml`, `libucode`, `libudebug`

### 文件系统 / Filesystem (2)
`blkid`, `e2fsprogs`（**注意**：resize2fs 在 OpenWrt 25.x 拆到 `e2fsprogs` 包内，未单列）

### 防火墙 / Firewall (1)
`nftables-json`

### HTTP (1)
`curl`

### 系统工具 / System (1)
`logd`

### 网络与 PPP (3)
`odhcp6c`, `odhcpd-ipv6only`, `ppp`, `ppp-mod-pppoe`, `kmod-ppp`, `kmod-pppoe`, `kmod-pppox`, `kmod-slhc`

### 路由数据 / Routing data (2)
`v2ray-geoip`, `v2ray-geosite`（**无配套 client**）

### 杂项工具 / Misc utilities (60+)
`apk-tools` (as `apk-mbedtls`), `coreutils`, `coreutils-base64/nohup/sleep/sort/timeout`, `ca-bundle`, `fwtool`, `getrandom`, `grub2-efi-arm`, `gzip`, `jansson`, `jshn`, `jsonfilter`, `lua`, `lyaml`, `mkf2fs`, `mtd`, `netifd`, `openwrt-keyring`, `owut`, `partx-utils`, `procd-seccomp`, `procd-ujail`, `px5g-mbedtls`, `rpcd-mod-file/iwinfo/luci/rpcsys/rrdns/ucode`, `u-boot-qemu_armv8`, `uclient-fetch`, `ucode`, `ucode-mod-fs/html/log/lua/math/ubus/uci/uclient/uloop`, `uhttpd-mod-ubus`, `unzip`, `urandom-seed`, `urngd`, `usign`, `yq`, `zlib`, `dnsmasq`, `frpc`, `knot-resolver_dnstap`, `TAR_BZIP2/GZIP/POSIX_ACL/XATTR/XZ/ZSTD`, `attendedsysupgrade-common`

### 内核模块 / Kernel modules (96)
96 个 `kmod-*` 包，包括：网络 PHY (`kmod-phy-*`, `kmod-mii`, `kmod-libphy`, `kmod-mdio-*`)、网卡驱动 (`kmod-stmmac-core`, `kmod-bcmgenet`, `kmod-mvneta`, `kmod-mvpp2`, `kmod-fsl-*`, `kmod-dwmac-*`, `kmod-atlantic`, `kmod-e1000e`, `kmod-vmxnet3`, `kmod-amazon-ena`, `kmod-octeontx2-net`, `kmod-renesas-net-avb`)、加密 (`kmod-crypto-*`)、防火墙 (`kmod-nf-*`, `kmod-nft-*`)、字符集 (`kmod-nls-*`)、RTC (`kmod-rtc-rx8025`, `kmod-pps`, `kmod-ptp`)、I²C/GPIO (`kmod-i2c-*`, `kmod-gpio-pca953x`)、看门狗 (`kmod-wdt-sp805`)、MACsec (`kmod-macsec`)、PPPoE (`kmod-pppoe`)、SFPMODEM (`kmod-sfp`) 等。

> 想看完整 96 个 kmod-* 清单？看 [`config/default.config`](config/default.config) 用 `grep '^CONFIG_PACKAGE_kmod-'` 过滤。

---

## CI 工作流 / Workflow

`.github/workflows/build.yml` 完成 15 步：

1. **Checkout** 仓库
2. **Show disk + memory**（诊断）
3. **Install build dependencies**（apt 装齐 build-essential + clang + zstd 等）
4. **Cache `openwrt/dl/`**（跨 build 复用下载）
5. **Download OpenWrt source**（codeload.github.com）
6. **Apply config + 用户输入**：复制 `config/default.config` → `openwrt/.config`，追加/移除用户指定的包，`make defconfig` 解析依赖
7. **Update + install feeds**
8. **Build**（`make -j1 V=s`，单线程，约 2-4 小时）
9. **Locate output image**（优先 `*ext4*rootfs*`）
10. **Compress** → `openwrt-final.img.gz` + 留一份 `openwrt-final.img`
11. **Generate SHA256SUMS**
12. **Resolve release tag**
13. **Upload artifacts**（即使 release 失败也保留 90 天）
14. **Publish GitHub Release**（含 3 个文件）
15. **Build summary**

---

## 关键命令 / Key commands

本地后处理常用：

```bash
# 挂载 ext4 镜像（CI 输出的 .img）
sudo mount -o loop -t ext4 openwrt-final.img /mnt/template-inject

# 注入 APK 包（注意 zstd 而非 gzip）
sudo tar --zstd -xf bin/packages/aarch64_generic/packages/<pkg>-*.apk -C /tmp/extract
sudo cp -rv /tmp/extract/* /mnt/template-inject/

# 卸载（必须 sync 两次）
sudo sync && sudo umount /mnt/template-inject && sudo sync && sudo losetup -D

# 注入 ZTE 定制（手动写 rc.local / 注入 zapret2）
./tools/inject.sh --template X.img --remove "ua3f nikki hiddify" --output Y.img

# 压缩最终镜像
python3 tools/gzip_image.py --src Y.img --dst Y.img.gz
```

---

## 已知缺口 / Known gaps

CI 输出与开箱即用的 V50 镜像之间还差：

| 项 | 状态 | 弥补办法 |
|----|------|----------|
| `rc.local`（型号/MAC/resize2fs） | ✗ 缺失 | 用 `tools/inject.sh` 注入，或在本地 build 后手动写 |
| `/opt/zapret2/` | ✗ 不在默认 config | 单独下载 zip，从模板镜像抽出注入 |
| 镜像固定 1 GB sparse | ✗ 实际 rootfs 大小 | 用 `truncate` / `dd` 包成 1 GB |
| `passwall2-server` | △ 不确定（看 config） | 触发 build 后看产物确认 |
| 烧录脚本 | ✗ 无 | 需要另外写（fastboot / dd / VM 替换） |

短期建议：CI 跑通后，再用 `tools/inject.sh` 在本地做最后一道加工，把上面这些补齐。

---

## 实际测试产物 / Real-world artifacts

- `openwrt-V50-frpc-noa3f-nikki-20260922.img`（SHA256 `c5f8f807…17f9`）—— 2026-09-22 在构建服务器上手工跑出来的，**移除 ua3f+nikki+hiddify，保留 frpc+passwall2+中文包**。流程详见 [`archive/2026-09-22-remove-ua3f-nikki/`](archive/2026-09-22-remove-ua3f-nikki/)。

---

## 贡献 / Contributing

发现 bug / 想加新功能：

1. Fork → 新分支 → commit → PR
2. PR 标题用 `<scope>: <一句话>` 格式，例：`tools: fix inject.sh 残留文件检测`
3. 公开文件**禁止**包含真实服务器 IP / 用户名 / 密码，使用 `<YOUR_*>` 占位符
4. `credentials/` 目录**禁止**提交

详细规则见 [`AGENTS.md`](AGENTS.md)。

---

## 性能优化 / Performance

为节省 CI 构建时间，仓库做了三层缓存：

1. **OpenWrt 源码下载缓存**（`openwrt/dl/`）——跨 build 复用所有 `make` 下载的 tarball
2. **ccache 跨 build 缓存**（`~/.ccache`，2 GB）——C/C++ 编译缓存。`CONFIG_DEVEL_CCACHE=y` 已默认启用
3. **GitHub Actions 缓存**（`actions/cache@v4`）——上面两个目录都被 key 到 `openwrt_version`，同版本 rebuild 可复用

实际收益（ubuntu-22.04 runner）：

| 场景 | 首 build | 同版本再 build |
|------|---------|---------------|
| 全量 build（默认 config + frpc + aurora + passwall2） | ~2-4 小时 | ~1.5-3 小时 |
| 只换 `add_packages`（源码不变） | 同上 | ~30-60 分钟（ccache 命中） |

**额外时间节约**：如果你**不介意**用预编译的 Aurora 主题（牺牲 5-10 分钟本地编译 vs 0 分钟远程下载），eamonxg 提供了一个签名的 feed：

```bash
# 在已运行的 V50 镜像上（默认 config 不带 aurora 的情况下）
wget -qO /etc/apk/keys/eamonxg.pem https://openwrt.eamonxg.fun/eamonxg.pem
echo "https://openwrt.eamonxg.fun/snapshots/apk/packages.adb" \
    >> /etc/apk/repositories.d/customfeeds.list
apk update
apk add luci-theme-aurora   # 或 luci-theme-shadcn / luci-app-aurora-config
```

Feed 详情：[openwrt.eamonxg.fun](https://openwrt.eamonxg.fun/)（eamonxg 同时维护 `luci-theme-aurora`）。

要进一步省时，构建时把 aurora 留空：

- workflow_dispatch → `add_packages` 留空 → 镜像不含 aurora（编译更快）
- 设备开机后通过上述命令从 eamonxg feed 安装

---

## 致谢与上游引用 / Credits & upstream

本项目编译的 OpenWrt 镜像中的所有组件均来自上游开源项目，本仓库仅做"配方固化 + CI 自动化"。下列项目在此特别致谢——**默认 config 已启用的标 ✅，需手动加包启用的标 ➕**：

### 内核与基础系统

| 组件 | 上游 | 状态 |
|------|------|------|
| [OpenWrt](https://github.com/openwrt/openwrt) | openwrt/openwrt | ✅ 基础系统 |
| [LuCI](https://github.com/openwrt/luci) | openwrt/luci | ✅ Web 界面 |
| Linux Kernel (6.12.94) | kernel.org | ✅ via `kmod-*` |
| musl libc | musl.libc.org | ✅ |

### LuCI 应用

| 包名 | 上游 | 状态 |
|------|------|------|
| `luci-app-firewall` | openwrt/luci | ✅ 默认启用 |
| `luci-app-frpc` | [chi-mirror/frpc](https://github.com/chi-mirror/frp) + [openwrt/packages](https://github.com/openwrt/packages) | ✅ 默认启用 |
| `luci-app-passwall2` | [xiaorouji/openwrt-passwall](https://github.com/xiaorouji/openwrt-passwall) | ✅ 默认启用（feed: `passwall2`） |
| `luci-app-package-manager` | openwrt/luci | ✅ 默认启用 |
| `luci-app-attendedsysupgrade` | [openwrt/luci](https://github.com/openwrt/luci) | ✅ 默认启用 |
| `luci-app-nikki` | [nikkinikki-org/OpenWrt-nikki](https://github.com/nikkinikki-org/OpenWrt-nikki) | ➕ 需 `add_packages` 加 |
| `luci-app-ua3f` | [esirplayground/luci-app-ua3f](https://github.com/esirplayground/luci-app-ua3f) | ➕ 需 `add_packages` 加 |

### LuCI 主题

| 主题 | 上游 | 状态 |
|------|------|------|
| **`luci-theme-aurora`** | [eamonxg/luci-theme-aurora](https://github.com/eamonxg/luci-theme-aurora) | ✅ 默认启用（feed: `theme_aurora`） |
| `luci-theme-bootstrap` | openwrt/luci | ✅ 默认启用 |
| `luci-theme-material` | [openwrt/luci](https://github.com/openwrt/luci) | ➕ 可选 |

### LuCI 中文 / i18n

当前 `default.config` 已启用：

- ✅ `luci-i18n-frpc-zh-cn`
- ✅ `luci-i18n-passwall2-zh-cn`

如需更多中文包，触发 build 时 `add_packages: luci-i18n-base-zh-cn luci-i18n-firewall-zh-cn ...`

详细可用 i18n 包列表：`grep '^# CONFIG_PACKAGE_luci-i18n-' config/default.config`

### 反审查 / 代理栈（第三方）

| 组件 | 上游 | 状态 |
|------|------|------|
| `v2ray-geoip` / `v2ray-geosite` | [v2fly/v2fly-github-io](https://github.com/v2fly/v2fly-github-io) / Loyalsoldier | ✅ 路由数据库（**但无 client 配套**） |
| PassWall2 | [xiaorouji/openwrt-passwall](https://github.com/xiaorouji/openwrt-passwall) | ➕ 需加 |
| mihomo (Clash Meta) | [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) | ➕ 需加 `luci-app-mihomo` |
| Nikki (Hiddify 兼容) | [nikkinikki-org/OpenWrt-nikki](https://github.com/nikkinikki-org/OpenWrt-nikki) | ➕ 需加 |
| UA3F (User-Agent 伪装) | [esirplayground/luci-app-ua3f](https://github.com/esirplayground/luci-app-ua3f) | ➕ 需加 |
| Hiddify-core | [hiddify/hiddify-app](https://github.com/hiddify/hiddify-app) | ➕ 需加 |
| Zapret2 | [bol-van/zapret](https://github.com/bol-van/zapret) | ❌ 不在 feeds，手动注入到 `/opt/zapret2/` |

### 工具与辅助

| 组件 | 上游 |
|------|------|
| frpc (frp client) | [fatedier/frp](https://github.com/fatedier/frp) |
| OpenWrt Package 仓库 | [openwrt/packages](https://github.com/openwrt/packages) |

如果这些项目对您有帮助，请给上游点 ⭐ 支持原作者。

---

## 许可证 / License

MIT. 见 [LICENSE](LICENSE)。