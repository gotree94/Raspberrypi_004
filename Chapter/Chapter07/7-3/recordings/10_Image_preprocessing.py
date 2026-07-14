import os
import cv2
import numpy as np

data_dir = os.path.join(os.path.dirname(__file__), "video")
base_dir = os.path.join(os.path.dirname(__file__), "processed")

output_cropped = os.path.join(base_dir, "cropped")
filters = {
    "filter_invert":       os.path.join(base_dir, "filter_invert"),
    "filter_otsu":         os.path.join(base_dir, "filter_otsu"),
    "filter_adaptive":     os.path.join(base_dir, "filter_adaptive"),
    "filter_invert_clahe": os.path.join(base_dir, "filter_invert_clahe"),
}
resized = {
    key: os.path.join(base_dir, key + "_resized") for key in filters
}

os.makedirs(output_cropped, exist_ok=True)
for d in list(filters.values()) + list(resized.values()):
    os.makedirs(d, exist_ok=True)

filenames = [f for f in os.listdir(data_dir) if f.endswith(".png")]
print(f"Found {len(filenames)} images")

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

for i, filename in enumerate(filenames):
    image_path = os.path.join(data_dir, filename)
    image = cv2.imread(image_path)

    height, width, channels = image.shape

    cropped = image[:int(height / 2), :, :]
    cv2.imwrite(os.path.join(output_cropped, filename), cropped)

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

    print(f"[{i + 1}/{len(filenames)}] {filename} done")

print("\nAll images processed!")
for key in filters:
    print(f"  {key:22s} -> {filters[key]}")
    print(f"  {key + '_resized':22s} -> {resized[key]}")
