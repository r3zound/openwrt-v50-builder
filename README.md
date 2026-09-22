# openwrt-v50-builder

> **本项目用于：构建可在 ZTE MU3351 / V50 等中兴系 CPE 设备内置的 Android 虚拟机（crosvm）中运行的 OpenWrt 固件包。**
>
> Build customized OpenWrt firmware images for ZTE MU3351 / V50 and similar ZTE CPE devices' Android-VM (crosvm) runtime.

针对运行在 **ZTE 中兴 CPE（MU3351 / V50 及同系列）内置 Android 虚拟机** 中的 OpenWrt 25.12.5 固件构建工具。通过 GitHub Actions 从上游 OpenWrt 源码编译，输出 ext4 rootfs 并发布到 GitHub Releases，可直接刷入设备的 VM 磁盘。

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
- `openwrt-final.img` — 原始 rootfs（用于检查）
- `SHA256SUMS` — 校验和

---

## 仓库结构 / Repository layout

```
.
├── README.md               # 本文件 / this file
├── AGENTS.md               # AI 协作规则
├── LICENSE                 # MIT 许可证
├── docs/                  # 长期文档（中文为主）
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

`config/default.config` 是从 `ZTE MU3351 / V50` 参考设备镜像里摘取的编译配置：

- **大小**：287 KB
- **已启用包**：239 个（`CONFIG_PACKAGE_*=y`）
- **目标**：`armsr/armv8 DEVICE_generic`
- **来源**：`/home/lg/openwrt-build/openwrt_V5/.config`（构建服务器上）

包含的关键组件：

- **核心系统**：`base-files`, `busybox`, `procd`, `uci`, `dropbear`, `dnsmasq-full`, `firewall4`
- **LuCI 界面**：`luci-mod-admin-full` + `aurora` + `bootstrap` 双主题 + 全中文包
- **代理反审查**：`PassWall2`, `UA3F`, `nikki + hiddify-core`, `mihomo-alpha`, `v2ray-geoip/geosite`
- **Zapret2**（手动安装在 `/opt/zapret2/`，**默认 config 不含**，需要 post-process 注入）
- **ZTE 定制**（手动写在 `/etc/rc.local`，**默认 config 不含**，需要 post-process 注入）：
  - 设备型号伪装 `ZTE MU3351 / V50`
  - `br-lan` MAC 固定 `02:00:00:00:88:01`
  - 首次开机 `resize2fs /dev/vda` 自动扩容

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

## 许可证 / License

MIT. 见 [LICENSE](LICENSE)。