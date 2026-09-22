#!/usr/bin/env bash
# Template-injection OpenWrt image modifier.
# Usage:
#   ./tools/inject.sh --template PATH [--remove "pkg1 pkg2"] [--output PATH]
#
# Copies --template to --output (so the original is preserved), mounts the copy
# with ext4, removes every file/dir whose name matches any --remove token
# (case-insensitive), and unmounts cleanly. Designed to run in GitHub Actions
# where sudo is implicit for the runner user.

set -euo pipefail

TEMPLATE=""
OUTPUT="openwrt-final.img"
REMOVE=""
MOUNT="/mnt/template-inject"

usage() {
  cat <<EOF
Usage: $0 --template PATH [options]

  --template PATH   Source .img (read only). Required.
  --remove  "PKGS" Space-separated package names to remove.
                    Example: "ua3f nikki hiddify"
  --output  PATH   Destination .img (written). Default: openwrt-final.img
  --mount   PATH   Mount point. Default: /mnt/template-inject

Note: this script does not download the template or gzip the output;
      those are the caller's responsibility.
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template) TEMPLATE="$2"; shift 2 ;;
    --remove)   REMOVE="$2";   shift 2 ;;
    --output)   OUTPUT="$2";   shift 2 ;;
    --mount)    MOUNT="$2";    shift 2 ;;
    -h|--help)  usage ;;
    *)          echo "Unknown arg: $1"; usage ;;
  esac
done

[[ -z "$TEMPLATE" ]] && { echo "--template is required"; usage; }
[[ ! -f "$TEMPLATE" ]] && { echo "Template not found: $TEMPLATE"; exit 1; }

# Always run cleanup on exit, even on error.
cleanup() {
  echo "[cleanup] sync + umount + losetup -D"
  sudo sync 2>/dev/null || true
  sudo umount "$MOUNT" 2>/dev/null || true
  sudo sync 2>/dev/null || true
  sudo losetup -D 2>/dev/null || true
  sudo rmdir "$MOUNT" 2>/dev/null || true
}
trap cleanup EXIT

# 1) copy
echo "[1] cp $TEMPLATE $OUTPUT"
cp "$TEMPLATE" "$OUTPUT"

# 2) mount
echo "[2] sudo mount -o loop -t ext4 $OUTPUT $MOUNT"
sudo mkdir -p "$MOUNT"
sudo mount -o loop -t ext4 "$OUTPUT" "$MOUNT"

# small delay so mount is fully settled before find() walks it
sleep 1
ls "$MOUNT" | head -3
echo

# 3) remove
if [[ -n "$REMOVE" ]]; then
  echo "[3] Remove packages: $REMOVE"
  for pkg in $REMOVE; do
    mapfile -t files < <(find "$MOUNT" -iname "*${pkg}*" \
      -not -path "*/proc/*" 2>/dev/null || true)
    if [[ ${#files[@]} -eq 0 ]]; then
      echo "  [skip] $pkg: no files"
      continue
    fi
    echo "  [rm]   $pkg: ${#files[@]} files"
    for f in "${files[@]}"; do
      sudo rm -rf "$f" 2>/dev/null || true
    done

    # Verify zero leftovers
    leftover=$(find "$MOUNT" -iname "*${pkg}*" -not -path "*/proc/*" 2>/dev/null \
               | wc -l)
    if [[ "$leftover" -gt 0 ]]; then
      echo "  [WARN] $pkg: $leftover file(s) remain"
      exit 1
    fi
  done
fi

# 4) verify ZTE rc.local still has device model
echo
echo "[4] verify ZTE customizations preserved"
if grep -q "ZTE MU3351" "$MOUNT/etc/rc.local" 2>/dev/null; then
  echo "  [OK] /etc/rc.local contains 'ZTE MU3351'"
else
  echo "  [WARN] /etc/rc.local does not contain 'ZTE MU3351'"
fi
[[ -x "$MOUNT/usr/sbin/resize2fs" ]] \
  && echo "  [OK] resize2fs present" \
  || echo "  [WARN] resize2fs missing"
[[ -d "$MOUNT/opt/zapret2" ]] \
  && echo "  [OK] zapret2 present" \
  || echo "  [WARN] zapret2 missing"

echo
echo "[done] $OUTPUT ready (umount will happen via cleanup trap)"