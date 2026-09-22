# -*- coding: utf-8 -*-
"""Compress an OpenWrt ext4 image (.img -> .img.gz) with progress reporting.

Usage:
  python3 tools/gzip_image.py --src PATH [--dst PATH] [--level 1-9]

Defaults to .gz next to the source if --dst is omitted.
"""
import argparse
import hashlib
import gzip
import os
import sys
import time


def parse_args():
    p = argparse.ArgumentParser(description='gzip-compress an .img file')
    p.add_argument('--src', required=True, help='source .img path')
    p.add_argument('--dst', default=None,
                   help='destination .img.gz path (default: <src>.gz)')
    p.add_argument('--level', type=int, default=6, choices=range(1, 10),
                   help='gzip level (1=fast, 9=best, default=6)')
    return p.parse_args()


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    args = parse_args()
    src = args.src
    dst = args.dst or (src + '.gz')

    src_size = os.path.getsize(src)
    print(f'src: {src}')
    print(f'  size: {src_size/1024/1024:.1f} MB')
    print(f'dst: {dst}')

    if os.path.exists(dst):
        os.remove(dst)
        print(f'  removed old dst')

    t0 = time.time()
    state = {'last_pct': -1}

    with open(src, 'rb') as f_in, gzip.open(dst, 'wb', compresslevel=args.level) as f_out:
        chunk_size = 8 * 1024 * 1024
        while True:
            chunk = f_in.read(chunk_size)
            if not chunk:
                break
            f_out.write(chunk)
            transferred = f_in.tell()
            pct = int(transferred * 100 / src_size)
            if pct != state['last_pct'] and pct % 2 == 0:
                state['last_pct'] = pct
                elapsed = time.time() - t0
                speed = transferred / elapsed / (1024 * 1024) if elapsed > 0 else 0
                eta = (src_size - transferred) / (transferred / elapsed) if transferred > 0 else 0
                print(f'\r  {pct}% ({transferred/1024/1024:.0f}/{src_size/1024/1024:.0f} MB) '
                      f'{speed:.1f} MB/s ETA {eta/60:.1f}min', end='', flush=True)

    print()

    dst_size = os.path.getsize(dst)
    elapsed = time.time() - t0
    print(f'\ndone')
    print(f'  output: {dst_size/1024/1024:.1f} MB (ratio {dst_size/src_size*100:.1f}%)')
    print(f'  time:   {elapsed/60:.1f} min')

    print('  computing SHA256...')
    h = hashlib.sha256()
    with open(dst, 'rb') as f:
        while True:
            c = f.read(8 * 1024 * 1024)
            if not c:
                break
            h.update(c)
    print(f'  .gz SHA256: {h.hexdigest()}')


if __name__ == '__main__':
    main()