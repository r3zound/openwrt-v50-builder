# -*- coding: utf-8 -*-
"""把 openwrt-V50-frpc-noa3f-nikki-20260922.img 压缩成 .img.gz"""
import sys, os, time, gzip, hashlib
sys.stdout.reconfigure(encoding='utf-8')

SRC = r'D:\OneDrive\User\Network\CPE\V50\OpenWRT虚机资源等1个文件\OpenWRT虚机资源\openwrt-V50-frpc-noa3f-nikki-20260922.img'
DST = SRC + '.gz'

src_size = os.path.getsize(SRC)
print(f'源: {SRC}')
print(f'  大小: {src_size/1024/1024:.1f} MB')
print(f'目标: {DST}')

if os.path.exists(DST):
    os.remove(DST)
    print(f'  已删旧 {DST}')

t0 = time.time()
state = {'last_pct': -1}

with open(SRC, 'rb') as f_in:
    with gzip.open(DST, 'wb', compresslevel=6) as f_out:
        chunk_in = 8 * 1024 * 1024  # 8MB chunks
        while True:
            chunk = f_in.read(chunk_in)
            if not chunk:
                break
            f_out.write(chunk)
            # progress
            transferred = f_in.tell()
            pct = int(transferred * 100 / src_size)
            if pct != state['last_pct'] and pct % 2 == 0:
                state['last_pct'] = pct
                elapsed = time.time() - t0
                speed = transferred / elapsed / (1024*1024) if elapsed > 0 else 0
                eta = (src_size - transferred) / (transferred / elapsed) if transferred > 0 else 0
                print(f'\r  {pct}% ({transferred/1024/1024:.0f}/{src_size/1024/1024:.0f} MB) {speed:.1f} MB/s ETA {eta/60:.1f}min', end='', flush=True)

print()

dst_size = os.path.getsize(DST)
elapsed = time.time() - t0
print(f'\n压缩完成')
print(f'  输出大小: {dst_size/1024/1024:.1f} MB (压缩比 {dst_size/src_size*100:.1f}%)')
print(f'  用时: {elapsed/60:.1f} min')

# sha256 of gz
print('  计算 .gz SHA256...')
h = hashlib.sha256()
with open(DST, 'rb') as f:
    while True:
        c = f.read(8*1024*1024)
        if not c: break
        h.update(c)
gz_sha = h.hexdigest()
print(f'  .gz SHA256: {gz_sha}')

# sha256 of original img (for record)
h2 = hashlib.sha256()
with open(SRC, 'rb') as f:
    while True:
        c = f.read(8*1024*1024)
        if not c: break
        h2.update(c)
img_sha = h2.hexdigest()
print(f'  .img SHA256: {img_sha}')