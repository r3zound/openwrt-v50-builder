# openwrt-v50-builder

> Template-injection OpenWrt 25.12.5 firmware builder for ZTE MU3351 / V50 (armsr/armv8).

Build a customized OpenWrt firmware image for the ZTE MU3351 / V50 CPE without doing a full source compile. Instead, this skill mounts a pre-built ext4 image, adds/removes packages by manipulating files inside the mount, and ships the modified image.

## Highlights

- **No full rebuild**: takes ~5–15 minutes to add or remove a single plugin (vs hours for a full OpenWrt compile).
- **Template-injection method**: edit the existing 1 GB ext4 image directly, preserving ZTE's `/etc/rc.local` customizations, `resize2fs`, and `/opt/zapret2/`.
- **Po2lmo shortcut**: inject Chinese translations (`luci-i18n-*-zh-cn.lmo`) without recompiling the i18n package — directly compile `.po` files using the host's `po2lmo`.
- **Single-threaded `make`**: avoids race conditions in `grub2-efi-arm` and similar packages.
- **APKv3 / zstd**: knows the difference between `tar xzf` (won't work) and `tar --zstd -xf`.

## Quick start

1. **Read the skill** in [`docs/SKILL.md`](docs/SKILL.md) for the full procedure, the 10 iron rules, and the troubleshooting table.
2. **Configure environment variables** (replace the placeholders):

    ```bash
    export OPENWRT_BUILD_HOST="<YOUR_BUILD_SERVER_IP>"
    export OPENWRT_BUILD_USER="<YOUR_USER>"
    export OPENWRT_BUILD_PASS="<YOUR_SSH_PASSWORD>"
    export OPENWRT_SUDO_PASS="<YOUR_SUDO_PASSWORD>"
    ```

3. **Run the tools**:

    ```bash
    # Add or remove a package by editing the mounted image
    python tools/remove_pkgs.py

    # Compress a built image for distribution
    python tools/gzip_image.py
    ```

## Repository layout

```
.
├── README.md               # this file
├── AGENTS.md               # agent collaboration rules for this repo
├── LICENSE
├── docs/                   # long-form skill documents
│   ├── SKILL.md            # main skill (start here)
│   ├── OpenWrt固件构建指南.md
│   └── OpenWrt固件构建教程_脱敏版.md
├── tools/                  # reusable scripts (sanitized, use env vars)
│   ├── remove_pkgs.py
│   └── gzip_image.py
├── archive/                # one-time scripts from past sessions
│   └── 2026-09-22-remove-ua3f-nikki/
└── credentials/            # local-only credentials backup (NEVER committed)
```

The `credentials/` directory is git-ignored and holds private copies of the original (un-sanitized) files. Keep it on your local machine only.

## Target hardware

| Item | Value |
|------|-------|
| Device | ZTE MU3351 / V50 |
| Architecture | ARMv8 (`armsr/armv8`) |
| Run-time | Android VM running OpenWrt via crosvm |
| OpenWrt version | 25.12.5 (APK package manager) |
| Kernel | 6.12.94 |
| Image format | 1 GB ext4 (fixed size, no partition table) |

## Pre-built image contents (292 packages)

The base image (`openwrt-backup-XXXXXX.img`) already contains:

- Core: `base-files`, `busybox`, `procd`, `uci`, `dropbear`, `dnsmasq-full`, `firewall4`
- LuCI: `luci-mod-admin-full`, themes `aurora` + `bootstrap`, full `zh-cn` localization
- Apps: `luci-app-firewall`, `luci-app-passwall2`, `luci-app-nikki`, `luci-app-package-manager`
- Anti-censorship: PassWall2, UA3F, nikki + hiddify-core, mihomo-alpha, v2ray-geoip/geosite
- Zapret2 (manual install at `/opt/zapret2/`)
- ZTE customizations: `rc.local` model spoof + br-lan MAC fix + `resize2fs /dev/vda`

## Verified commands

```bash
# Compile a single package (mandatory -j1)
make package/<pkg>/compile V=s -j1

# Mount the image
sudo mount -o loop -t ext4 openwrt-final.img /mnt/backup-openwrt

# Inject an APK (note: zstd, not gzip)
sudo tar --zstd -xf bin/packages/aarch64_generic/packages/<pkg>-*.apk -C /tmp/extract
sudo cp -rv /tmp/extract/* /mnt/backup-openwrt/

# Unmount cleanly
sudo sync && sudo umount /mnt/backup-openwrt && sudo sync && sudo losetup -D
```

## Real-world test artifacts

- `openwrt-V50-frpc-noa3f-nikki-20260922.img` — built by removing `ua3f` and `nikki` from the frpc-20260822 image and adding `luci-i18n-frpc-zh-cn` via po2lmo.
- See [`archive/2026-09-22-remove-ua3f-nikki/`](archive/2026-09-22-remove-ua3f-nikki/) for the exact step-by-step scripts used.

## License

MIT. See [LICENSE](LICENSE).