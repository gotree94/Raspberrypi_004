"""
사진 전처리 스크립트
- 이미지 리사이즈
- 메타데이터 확인
- EXIF 정보 추출
실행: python photo_preprocess.py
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("Pillow 설치 필요: pip install Pillow")
    sys.exit(1)

PHOTO_DIR = Path(r"C:\Users\Administrator\Desktop\3d_simulator_project\photos")
OUTPUT_DIR = Path(r"C:\Users\Administrator\Desktop\3d_simulator_project\photos\processed")
MAX_SIZE = 2048  # 최대 해상도

def get_exif(image):
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                exif_data[decoded] = value
    except:
        pass
    return exif_data

def process_photos():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    photos = list(PHOTO_DIR.glob("*.jpg")) + list(PHOTO_DIR.glob("*.png")) + list(PHOTO_DIR.glob("*.jpeg"))
    
    if not photos:
        print("사진이 없습니다.")
        return
    
    print(f"전처리 시작: {len(photos)}장")
    print(f"출력 폴더: {OUTPUT_DIR}")
    print()
    
    for i, photo in enumerate(photos, 1):
        img = Image.open(photo)
        exif = get_exif(img)
        
        orig_size = img.size
        w, h = img.size
        
        # 리사이즈
        if max(w, h) > MAX_SIZE:
            ratio = MAX_SIZE / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # 출력
        output_path = OUTPUT_DIR / f"scan_{i:03d}.jpg"
        img.save(output_path, "JPEG", quality=90)
        
        # 정보 출력
        camera = exif.get("Model", "Unknown")
        focal = exif.get("FocalLength", "Unknown")
        print(f"  [{i:02d}/{len(photos)}] {photo.name} -> {output_path.name} | {orig_size} -> {img.size} | Camera: {camera}")
    
    print()
    print(f"완료! {len(photos)}장 처리됨")
    print(f"출력 위치: {OUTPUT_DIR}")

if __name__ == "__main__":
    process_photos()
