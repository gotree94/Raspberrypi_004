import os
import sys
import cv2
import numpy as np

base_dir = os.path.dirname(os.path.abspath(__file__))

if len(sys.argv) < 2:
    print(f"Usage: python {os.path.basename(__file__)} <input_folder> [output_folder]")
    print(f"  input_folder: folder containing train_*.png images")
    print(f"  output_folder: folder name for preprocessed output (default: processed_<input_folder>)")
    print(f"")
    print(f"Examples:")
    print(f"  python {os.path.basename(__file__)} video")
    print(f"  python {os.path.basename(__file__)} video_shifted_m10")
    print(f"  python {os.path.basename(__file__)} video_shifted_m10 processed_shifted_m10")
    sys.exit(1)

input_folder = sys.argv[1]
output_folder = sys.argv[2] if len(sys.argv) > 2 else f"processed_{input_folder}"

input_dir = os.path.join(base_dir, input_folder)
output_base = os.path.join(base_dir, output_folder)

filters = {
    "filter_invert":       os.path.join(output_base, "filter_invert"),
    "filter_otsu":         os.path.join(output_base, "filter_otsu"),
    "filter_adaptive":     os.path.join(output_base, "filter_adaptive"),
    "filter_invert_clahe": os.path.join(output_base, "filter_invert_clahe"),
}
resized = {
    key: os.path.join(output_base, key + "_resized") for key in filters
}

for d in list(filters.values()) + list(resized.values()):
    os.makedirs(d, exist_ok=True)

filenames = [f for f in os.listdir(input_dir) if f.endswith(".png")]
print(f"Found {len(filenames)} images in {input_dir}")

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

for i, filename in enumerate(filenames):
    image_path = os.path.join(input_dir, filename)
    image = cv2.imread(image_path)
    if image is None:
        continue

    height, width, channels = image.shape
    cropped = image[:int(height / 2), :, :]
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    gray_eq = clahe.apply(gray)

    invert = 255 - gray_eq
    invert = cv2.GaussianBlur(invert, (3, 3), 0)
    cv2.imwrite(os.path.join(filters["filter_invert"], filename), invert)
    cv2.imwrite(os.path.join(resized["filter_invert"], filename),
                cv2.resize(invert, (200, 66)))

    _, otsu = cv2.threshold(gray_eq, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cv2.imwrite(os.path.join(filters["filter_otsu"], filename), otsu)
    cv2.imwrite(os.path.join(resized["filter_otsu"], filename),
                cv2.resize(otsu, (200, 66)))

    adaptive = cv2.adaptiveThreshold(
        gray_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    cv2.imwrite(os.path.join(filters["filter_adaptive"], filename), adaptive)
    cv2.imwrite(os.path.join(resized["filter_adaptive"], filename),
                cv2.resize(adaptive, (200, 66)))

    inv_clahe = 255 - gray_eq
    inv_clahe = clahe.apply(inv_clahe)
    inv_clahe = cv2.GaussianBlur(inv_clahe, (3, 3), 0)
    cv2.imwrite(os.path.join(filters["filter_invert_clahe"], filename), inv_clahe)
    cv2.imwrite(os.path.join(resized["filter_invert_clahe"], filename),
                cv2.resize(inv_clahe, (200, 66)))

    if (i + 1) % 200 == 0:
        print(f"  [{i + 1}/{len(filenames)}] {filename} done")

print("\nAll images processed!")
for key in filters:
    count = len([f for f in os.listdir(filters[key]) if f.endswith(".png")])
    print(f"  {key:22s} -> {count} images")
    count_r = len([f for f in os.listdir(resized[key]) if f.endswith(".png")])
    print(f"  {key + '_resized':22s} -> {count_r} images")
