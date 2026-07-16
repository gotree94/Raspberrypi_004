import os
import re
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(base_dir, "video")
dst_dir = os.path.join(base_dir, "video", "_debug_output")

debug_files = {}
for f in os.listdir(dst_dir):
    m = re.match(r"train_(\d+)_(\d+)\.png", f)
    if m:
        debug_files[m.group(1)] = m.group(2)

renamed = 0
skipped = 0
for f in sorted(os.listdir(src_dir)):
    if not f.startswith("train_") or not f.endswith(".png"):
        continue
    m = re.match(r"train_(\d+)_(\d+)\.png", f)
    if not m:
        continue
    num, old_angle = m.group(1), m.group(2)
    if num not in debug_files:
        skipped += 1
        continue
    new_angle = debug_files[num]
    if old_angle == new_angle:
        skipped += 1
        continue
    old_path = os.path.join(src_dir, f)
    new_name = f"train_{num}_{new_angle}.png"
    new_path = os.path.join(src_dir, new_name)
    os.rename(old_path, new_path)
    renamed += 1
    print(f"  {f} -> {new_name}")

print(f"\nDone. Renamed: {renamed}, Skipped: {skipped}")
