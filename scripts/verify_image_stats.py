#!/usr/bin/env python3
import os
import math
from PIL import Image, ImageStat

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, '.originals_backup')

IMAGE_DIRS = [
    'NORM HOUSE AND POOL',
    'NORM KING SUIT',
    'NORM QUEEN SUIT',
    '.'
]

EXCLUDE_FILES = {
    'butterfly-left.png',
    'butterfly-right.png',
    'butterfly-real.png',
    'butterfly.svg',
    'butterfly-left.svg',
    'butterfly-right.svg',
    'real_butterfly_master.png',
    'Colias_eurytheme-transparent.png',
    'Danaus_plexippus-transparent.png',
    'single.png',
    'specimens.png'
}

def analyze_image(path):
    if not os.path.exists(path):
        return None
    with Image.open(path) as img:
        img_rgb = img.convert('RGB')
        stat = ImageStat.Stat(img_rgb)
        r, g, b = stat.mean
        std_r, std_g, std_b = stat.stddev
        lum = math.sqrt(0.299 * (r**2) + 0.587 * (g**2) + 0.114 * (b**2))
        
        hsv = img.convert('HSV')
        hstat = ImageStat.Stat(hsv)
        h, s, v = hstat.mean
        
        rb_ratio = r / (b + 1e-5)
        contrast = (std_r + std_g + std_b) / 3.0
        return {
            'lum': lum,
            'sat': s,
            'contrast': contrast,
            'rb_ratio': rb_ratio,
            'rgb': (r, g, b)
        }

def compare_all():
    print("=" * 105)
    print(f"{'Image File':38} | {'Orig Lum':8} -> {'New Lum':8} | {'Orig Sat':8} -> {'New Sat':8} | {'Orig R/B':8} -> {'New R/B':8}")
    print("=" * 105)
    
    orig_sats = []
    new_sats = []
    orig_lums = []
    new_lums = []
    
    for folder in IMAGE_DIRS:
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.exists(folder_path):
            continue
        print(f"\n--- {folder} ---")
        for f in sorted(os.listdir(folder_path)):
            if f.startswith('.') or f in EXCLUDE_FILES or not f.lower().endswith(('.jpg', '.jpeg')):
                continue
            if folder == '.' and not f.lower().startswith(('norm', 'img', 'screenshot', 'queen', 'pic', 'whatsapp')):
                continue
                
            curr_path = os.path.join(folder_path, f)
            rel = os.path.relpath(curr_path, BASE_DIR)
            back_path = os.path.join(BACKUP_DIR, rel)
            
            orig = analyze_image(back_path)
            curr = analyze_image(curr_path)
            
            if orig and curr:
                orig_sats.append(orig['sat'])
                new_sats.append(curr['sat'])
                orig_lums.append(orig['lum'])
                new_lums.append(curr['lum'])
                
                print(f"{f[:38]:38} | {orig['lum']:6.1f}   -> {curr['lum']:6.1f}   | {orig['sat']:6.1f}   -> {curr['sat']:6.1f}   | {orig['rb_ratio']:6.2f}   -> {curr['rb_ratio']:6.2f}")

    if orig_sats and new_sats:
        def mean_std(arr):
            m = sum(arr) / len(arr)
            var = sum((x - m) ** 2 for x in arr) / len(arr)
            return m, math.sqrt(var)
            
        m_os, s_os = mean_std(orig_sats)
        m_ns, s_ns = mean_std(new_sats)
        m_ol, s_ol = mean_std(orig_lums)
        m_nl, s_nl = mean_std(new_lums)
        
        print("\n" + "=" * 105)
        print("SUMMARY STATISTICAL COMPARISON:")
        print("=" * 105)
        print(f"SATURATION: Original Mean = {m_os:.1f}, StdDev = {s_os:.1f} (Min={min(orig_sats):.1f}, Max={max(orig_sats):.1f})")
        print(f"            Normalized Mean = {m_ns:.1f}, StdDev = {s_ns:.1f} (Min={min(new_sats):.1f}, Max={max(new_sats):.1f})")
        print(f"LUMINANCE:  Original Mean = {m_ol:.1f}, StdDev = {s_ol:.1f} (Min={min(orig_lums):.1f}, Max={max(orig_lums):.1f})")
        print(f"            Normalized Mean = {m_nl:.1f}, StdDev = {s_nl:.1f} (Min={min(new_lums):.1f}, Max={max(new_lums):.1f})")
        print("=" * 105)

if __name__ == '__main__':
    compare_all()
