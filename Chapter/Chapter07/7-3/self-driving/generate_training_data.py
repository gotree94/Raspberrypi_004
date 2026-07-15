import os
import sys
import cv2
import numpy as np
import torch
import torch.nn as nn

base_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(base_dir)

MODEL_DIRS = {
    "invert":       os.path.join(parent_dir, "model-20260715_210333"),
    "otsu":         os.path.join(parent_dir, "model-20260715_211154"),
    "adaptive":     os.path.join(parent_dir, "model-20260715_211949"),
    "invert_clahe": os.path.join(parent_dir, "model-20260715_212841"),
}

VIDEO_PATH = os.path.join(base_dir, "TEST2.mp4")
OUTPUT_DIR = os.path.join(base_dir, "video")
os.makedirs(OUTPUT_DIR, exist_ok=True)

USE_FRAMES = None

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class NvidiaModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 24, kernel_size=5, stride=2),
            nn.ELU(inplace=True),
            nn.Conv2d(24, 36, kernel_size=5, stride=2),
            nn.ELU(inplace=True),
            nn.Conv2d(36, 48, kernel_size=5, stride=2),
            nn.ELU(inplace=True),
            nn.Conv2d(48, 64, kernel_size=3, stride=1),
            nn.ELU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ELU(inplace=True),
        )
        self.flatten = nn.Flatten()
        with torch.no_grad():
            tmp = torch.zeros(1, 3, 66, 200)
            f = self.features(tmp)
            flat_dim = f.numel()
        self.mlp = nn.Sequential(
            nn.Dropout(p=0.2),
            nn.Linear(flat_dim, 100),
            nn.ELU(inplace=True),
            nn.Linear(100, 50),
            nn.ELU(inplace=True),
            nn.Linear(50, 10),
            nn.ELU(inplace=True),
            nn.Linear(10, 1),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.flatten(x)
        x = self.mlp(x)
        return x


def apply_filter(frame_bgr, filter_name):
    height, width, _ = frame_bgr.shape
    cropped = frame_bgr[:int(height / 2), :, :]
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_eq = clahe.apply(gray)

    if filter_name == "invert":
        result = 255 - gray_eq
        result = cv2.GaussianBlur(result, (3, 3), 0)
    elif filter_name == "otsu":
        _, result = cv2.threshold(gray_eq, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    elif filter_name == "adaptive":
        result = cv2.adaptiveThreshold(
            gray_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
    elif filter_name == "invert_clahe":
        result = 255 - gray_eq
        result = clahe.apply(result)
        result = cv2.GaussianBlur(result, (3, 3), 0)
    else:
        raise ValueError(f"Unknown filter: {filter_name}")

    resized = cv2.resize(result, (200, 66))
    return resized


def preprocess_for_inference(img_uint8):
    if len(img_uint8.shape) == 2:
        img_uint8 = cv2.cvtColor(img_uint8, cv2.COLOR_GRAY2BGR)
    img = img_uint8.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    return img


def load_model(filter_name):
    model = NvidiaModel().to(device)
    pt_path = os.path.join(MODEL_DIRS[filter_name], "lane_navigation_best.pt")
    checkpoint = torch.load(pt_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model


def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"ERROR: Video not found: {VIDEO_PATH}")
        sys.exit(1)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"ERROR: Cannot open video: {VIDEO_PATH}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {VIDEO_PATH}")
    print(f"  Frames: {total_frames}, FPS: {fps:.1f}, Resolution: {width}x{height}")

    if USE_FRAMES is None:
        use_frames = total_frames // 2
    else:
        use_frames = USE_FRAMES
    print(f"  Using first {use_frames} frames (half of total)")

    models = {}
    for name in MODEL_DIRS:
        try:
            m = load_model(name)
            models[name] = m
            print(f"  Loaded model: {name}")
        except Exception as e:
            print(f"  FAILED to load model {name}: {e}")

    if not models:
        print("ERROR: No models loaded")
        sys.exit(1)

    saved_count = 0

    print(f"\nProcessing video and saving images to: {OUTPUT_DIR}")
    print(f"  Original + Flipped images (angle: 180 - original)")
    print("Press Ctrl+C to stop early\n")

    try:
        for frame_idx in range(use_frames):
            ret, frame = cap.read()
            if not ret:
                break

            angles = []
            for name, model in models.items():
                filtered = apply_filter(frame, name)
                input_tensor = preprocess_for_inference(filtered)
                input_batch = torch.from_numpy(input_tensor).float().unsqueeze(0).to(device)
                with torch.no_grad():
                    pred = model(input_batch)
                angles.append(pred.item())

            avg_angle = np.mean(angles)
            orig_angle = int(round(avg_angle))
            orig_angle = max(0, min(180, orig_angle))

            orig_filename = f"train_{saved_count + 1:06d}_{orig_angle:03d}.png"
            orig_filepath = os.path.join(OUTPUT_DIR, orig_filename)
            cv2.imwrite(orig_filepath, frame)
            saved_count += 1

            flipped_frame = cv2.flip(frame, 1)
            flipped_angle = 180 - orig_angle
            flipped_angle = max(0, min(180, flipped_angle))

            flip_filename = f"train_{saved_count + 1:06d}_{flipped_angle:03d}.png"
            flip_filepath = os.path.join(OUTPUT_DIR, flip_filename)
            cv2.imwrite(flip_filepath, flipped_frame)
            saved_count += 1

            if (frame_idx + 1) % 100 == 0:
                print(f"  Frame {frame_idx + 1}/{use_frames} | "
                      f"Saved {saved_count} images | "
                      f"Last angle: {orig_angle} -> flipped: {flipped_angle}")

    except KeyboardInterrupt:
        print(f"\nStopped early at frame {frame_idx}")

    cap.release()
    print(f"\nDone! Saved {saved_count} images to: {OUTPUT_DIR}")
    print(f"  Original: {saved_count // 2} images")
    print(f"  Flipped:  {saved_count // 2} images")
    print(f"  Filename format: train_{{sequence}}_{{angle}}.png")


if __name__ == "__main__":
    main()
