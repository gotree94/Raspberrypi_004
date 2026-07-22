"""
사진 준비 상태 확인 스크립트
실행: python check_photos.py
"""
import os
import glob
from pathlib import Path

PHOTO_DIR = Path(r"C:\Users\Administrator\Desktop\3d_simulator_project\photos")

def check_photos():
    photos = list(PHOTO_DIR.glob("*.jpg")) + list(PHOTO_DIR.glob("*.png")) + list(PHOTO_DIR.glob("*.jpeg"))
    
    print("=" * 50)
    print("  실내 스캔 사진 상태 확인")
    print("=" * 50)
    print(f"  사진 폴더: {PHOTO_DIR}")
    print(f"  발견된 사진: {len(photos)}장")
    print()
    
    if len(photos) == 0:
        print("  [!] 사진이 없습니다. 촬영 후 photos 폴더에 넣어주세요.")
        print("      권장: 최소 20장 이상")
        return False
    
    if len(photos) < 10:
        print("  [!] 사진이 부족합니다. 추가 촬영 권장 (최소 20장)")
    elif len(photos) < 20:
        print("  [~] 보통 수준. 더 많으면 정확도 향상")
    else:
        print("  [OK] 충분한 사진 수!")
    
    print()
    print("  촬영된 파일:")
    for p in photos[:10]:
        print(f"    - {p.name}")
    if len(photos) > 10:
        print(f"    ... 외 {len(photos) - 10}장")
    
    return True

if __name__ == "__main__":
    check_photos()
