#!/usr/bin/env python3
import os
import shutil
import math
from PIL import Image, ImageStat, ImageEnhance, ImageFilter, ImageOps

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, '.originals_backup')

IMAGE_DIRS = [
    os.path.join(BASE_DIR, 'NORM HOUSE AND POOL'),
    os.path.join(BASE_DIR, 'NORM KING SUIT'),
    os.path.join(BASE_DIR, 'NORM QUEEN SUIT'),
    BASE_DIR
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

def get_property_images():
    images = []
    for d in IMAGE_DIRS:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.startswith('.') or f in EXCLUDE_FILES:
                continue
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                path = os.path.join(d, f)
                if os.path.isfile(path):
                    # Check if it's in base dir and avoid subdirectories
                    if d == BASE_DIR:
                        if not f.lower().startswith(('norm', 'img', 'screenshot', 'queen', 'pic', 'whatsapp')):
                            continue
                    images.append(path)
    return sorted(list(set(images)))

def backup_images():
    print("Backing up original images...")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    images = get_property_images()
    for img_path in images:
        rel_path = os.path.relpath(img_path, BASE_DIR)
        dest_path = os.path.join(BACKUP_DIR, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        if not os.path.exists(dest_path):
            shutil.copy2(img_path, dest_path)
            print(f"Backed up: {rel_path}")
    print(f"Backup complete. Total {len(images)} images secured.")

def analyze_image(img):
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
        'r': r, 'g': g, 'b': b,
        'lum': lum, 'sat': s, 'val': v,
        'rb_ratio': rb_ratio,
        'contrast': contrast
    }

def build_lut(gamma=1.0, black_point=0, white_point=255, s_curve_factor=0.0):
    lut = []
    bp = black_point
    wp = max(bp + 1, white_point)
    for i in range(256):
        # Stretch black and white points
        norm = (i - bp) / (wp - bp)
        norm = max(0.0, min(1.0, norm))
        # Apply gamma
        val = norm ** gamma
        # Apply S-curve contrast if requested
        if s_curve_factor > 0:
            # smooth sigmoid blend
            sig = 0.5 * (1 + math.sin(math.pi * (val - 0.5)))
            val = (1 - s_curve_factor) * val + s_curve_factor * sig
        lut.append(int(round(val * 255)))
    return lut

def process_single_image(img_path, is_outdoor=False):
    with Image.open(img_path) as orig:
        img = orig.convert('RGB')
        w, h = img.size
        stats = analyze_image(img)
        
        # 1. Determine exposure/luminance target and curve
        # Indoor target lum ~ 145-160; Outdoor target lum ~ 130-145
        target_lum = 138 if is_outdoor else 155
        current_lum = stats['lum']
        
        # Calculate dynamic gamma adjustment
        if current_lum < 90:
            gamma = 0.65  # heavy shadow lift for very dark shots
        elif current_lum < 115:
            gamma = 0.78  # moderate shadow lift
        elif current_lum < 135:
            gamma = 0.88  # light shadow lift
        elif current_lum > 185:
            gamma = 1.15  # highlight recovery for blown out shots
        elif current_lum > 170:
            gamma = 1.08  # mild highlight taming
        else:
            gamma = 0.95  # subtle polish
            
        # 2. Dynamic Black/White Point stretch (Auto-levels)
        hist = img.histogram()
        total_pixels = w * h
        
        # Calculate luminance histogram
        lum_hist = [0] * 256
        for i in range(256):
            # approximate from RGB histogram
            lum_hist[i] = int(0.299 * hist[i] + 0.587 * hist[256 + i] + 0.114 * hist[512 + i])
            
        cum = 0
        bp = 0
        wp = 255
        # Low cutoff at 0.4%
        low_target = total_pixels * 0.004
        for i in range(256):
            cum += lum_hist[i]
            if cum >= low_target:
                bp = max(0, min(i, 30))  # don't crush real shadows
                break
                
        # High cutoff at 99.6%
        cum = 0
        for i in range(255, -1, -1):
            cum += lum_hist[i]
            if cum >= low_target:
                wp = min(255, max(i, 225))
                break
                
        # 3. Tone curve & Contrast S-curve
        s_curve = 0.25 if stats['contrast'] < 45 else 0.12
        lut = build_lut(gamma=gamma, black_point=bp, white_point=wp, s_curve_factor=s_curve)
        
        # Apply LUT to image
        # Separate channels for fine color temperature balance
        r_img, g_img, b_img = img.split()
        
        # Fine Color Temperature grading (Hospitality warm luxury look)
        # King Suite has R/B ~ 1.15; Outdoor has R/B ~ 0.8; Desaturated Queen has R/B ~ 1.05
        # We want warm, clean whites: R slightly higher than B, G neutral
        r_lut = [min(255, int(lut[i] * 1.03)) for i in range(256)]
        g_lut = [lut[i] for i in range(256)]
        
        if is_outdoor:
            # For outdoor: tame excess blue/cyan cast, balance greens
            b_lut = [min(255, int(lut[i] * 0.96)) for i in range(256)]
            g_lut = [min(255, int(lut[i] * 0.98)) for i in range(256)]
            r_lut = [min(255, int(lut[i] * 1.04)) for i in range(256)]
        else:
            # For indoor: warm hospitality glow (inviting golden-amber undertone)
            b_lut = [min(255, int(lut[i] * 0.94)) for i in range(256)]
            r_lut = [min(255, int(lut[i] * 1.05)) for i in range(256)]
            
        r_adj = r_img.point(r_lut)
        g_adj = g_img.point(g_lut)
        b_adj = b_img.point(b_lut)
        balanced_img = Image.merge('RGB', (r_adj, g_adj, b_adj))
        
        # 4. Saturation & Vibrance Harmonization
        current_sat = stats['sat']
        # Target saturation: outdoor ~ 72, indoor ~ 62
        target_sat = 72.0 if is_outdoor else 62.0
        
        if current_sat < 20:
            # Severely desaturated (e.g. Samsung screenshots with sat 9-18)
            sat_factor = 2.6
        elif current_sat < 35:
            sat_factor = 1.95
        elif current_sat < 50:
            sat_factor = 1.45
        elif current_sat > 130:
            # Severely oversaturated (e.g. WA outdoor pool shots with sat 140+)
            sat_factor = 0.58
        elif current_sat > 105:
            sat_factor = 0.72
        elif current_sat > 85:
            sat_factor = 0.85
        else:
            sat_factor = 1.05  # slight vibrancy polish
            
        enhancer = ImageEnhance.Color(balanced_img)
        saturated_img = enhancer.enhance(sat_factor)
        
        # 5. Clarity & Micro-contrast (Gentle Unsharp Mask)
        # Gives architectural photos crisp, professional definition
        sharpened = saturated_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=45, threshold=3))
        
        return sharpened

def run_pipeline():
    images = get_property_images()
    print(f"Found {len(images)} property images to process.")
    
    outdoor_keywords = ['pool', 'yard', 'house and pool', 'house front', 'house.jpg', 'backyard']
    
    print("\nProcessing images...")
    for img_path in images:
        rel = os.path.relpath(img_path, BASE_DIR)
        is_outdoor = any(k in rel.lower() for k in outdoor_keywords)
        
        processed = process_single_image(img_path, is_outdoor=is_outdoor)
        
        # Save high quality
        ext = os.path.splitext(img_path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            processed.save(img_path, 'JPEG', quality=95, optimize=True, subsampling=0)
        else:
            processed.save(img_path, 'PNG', optimize=True)
            
        print(f"Processed [{ 'Outdoor' if is_outdoor else 'Indoor' :7}]: {rel}")

if __name__ == '__main__':
    backup_images()
    run_pipeline()
