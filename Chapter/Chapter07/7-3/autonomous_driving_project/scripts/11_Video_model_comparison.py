import os
import fnmatch
import cv2
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base_dir = os.path.dirname(__file__)
video_path = os.path.join(base_dir, "TEST2.mp4")

MODELS = {
    "otsu":         "model-20260715_145408",
    "adaptive":     "model-20260715_150216",
    "invert_clahe": "model-20260715_150926",
    "invert":       "model-20260715_151808",
}

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

video_img_dir = os.path.join(base_dir, "video")


def preprocess_otsu(frame):
    h, w = frame.shape[:2]
    crop = frame[:h // 2, :]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray_eq = clahe.apply(gray)
    _, out = cv2.threshold(gray_eq, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    out = cv2.resize(out, (200, 66))
    img = out.astype(np.float32) / 255.0
    return np.stack([img, img, img], axis=2)


def preprocess_adaptive(frame):
    h, w = frame.shape[:2]
    crop = frame[:h // 2, :]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray_eq = clahe.apply(gray)
    out = cv2.adaptiveThreshold(
        gray_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    out = cv2.resize(out, (200, 66))
    img = out.astype(np.float32) / 255.0
    return np.stack([img, img, img], axis=2)


def preprocess_invert_clahe(frame):
    h, w = frame.shape[:2]
    crop = frame[:h // 2, :]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray_eq = clahe.apply(gray)
    inv = 255 - gray_eq
    inv = clahe.apply(inv)
    inv = cv2.GaussianBlur(inv, (3, 3), 0)
    inv = cv2.resize(inv, (200, 66))
    img = inv.astype(np.float32) / 255.0
    return np.stack([img, img, img], axis=2)


def preprocess_invert(frame):
    h, w = frame.shape[:2]
    crop = frame[:h // 2, :]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray_eq = clahe.apply(gray)
    inv = 255 - gray_eq
    inv = cv2.GaussianBlur(inv, (3, 3), 0)
    inv = cv2.resize(inv, (200, 66))
    img = inv.astype(np.float32) / 255.0
    return np.stack([img, img, img], axis=2)


PREPROCESSORS = {
    "otsu":         preprocess_otsu,
    "adaptive":     preprocess_adaptive,
    "invert_clahe": preprocess_invert_clahe,
    "invert":       preprocess_invert,
}


def load_ground_truth_angles():
    gt_angles = []
    for filename in sorted(os.listdir(video_img_dir)):
        if fnmatch.fnmatch(filename, "*.png"):
            angle = int(filename[-7:-4])
            gt_angles.append(angle)
    return np.array(gt_angles, dtype=np.float32)


def load_models():
    loaded = {}
    for name, folder in MODELS.items():
        ts_path = os.path.join(base_dir, folder, "lane_navigation_final.torchscript")
        if not os.path.exists(ts_path):
            print(f"  SKIP {name}: {ts_path} not found")
            continue
        model = torch.jit.load(ts_path, map_location="cpu")
        model.eval()
        torch.set_num_threads(1)
        loaded[name] = model
        print(f"  Loaded {name} <- {folder}")
    return loaded


def main():
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    print("Loading models...")
    models = load_models()
    if not models:
        raise RuntimeError("No models loaded")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video: {total_frames} frames @ {fps:.1f} FPS")

    results = {name: [] for name in models}
    frame_indices = []
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_indices.append(frame_idx)
        for name, model in models.items():
            preprocessor = PREPROCESSORS[name]
            img = preprocessor(frame)
            x = img.transpose(2, 0, 1)
            x = np.expand_dims(x, axis=0)
            x_tensor = torch.from_numpy(x).float()
            with torch.no_grad():
                y = model(x_tensor)
            angle = float(y.item())
            results[name].append(angle)

        frame_idx += 1
        if frame_idx % 50 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames")

    cap.release()
    print(f"Done. Processed {frame_idx} frames.")

    gt_angles = load_ground_truth_angles()
    print(f"Ground truth: {len(gt_angles)} images from video/")

    frame_indices = np.array(frame_indices)
    time_seconds = frame_indices / fps

    gt_time = np.linspace(0, time_seconds[-1], len(gt_angles))

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    colors = {"otsu": "#2196F3", "adaptive": "#FF9800",
              "invert_clahe": "#4CAF50", "invert": "#E91E63"}

    ax = axes[0]
    ax.plot(gt_time, gt_angles, color="black", linewidth=1.5, linestyle="--",
            label="Ground Truth", zorder=5)
    for name in models:
        ax.plot(time_seconds, results[name], label=name, color=colors[name], linewidth=0.8)
    ax.set_ylabel("Steering Angle (deg)")
    ax.set_title("All Models - Predicted Steering Angles vs Ground Truth")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    for name in models:
        angles = np.array(results[name])
        ax.hist(angles, bins=50, alpha=0.5, label=name, color=colors[name], edgecolor="black")
    ax.set_xlabel("Steering Angle (deg)")
    ax.set_ylabel("Frequency")
    ax.set_title("Angle Distribution per Model")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    angles_arr = np.array([results[name] for name in models])
    mean_per_frame = np.mean(angles_arr, axis=0)
    std_per_frame = np.std(angles_arr, axis=0)
    ax.plot(time_seconds, mean_per_frame, color="blue", linewidth=1.0, label="Models Mean")
    ax.fill_between(time_seconds, mean_per_frame - std_per_frame,
                    mean_per_frame + std_per_frame, alpha=0.2, color="blue",
                    label="Models Std Dev")
    ax.plot(gt_time, gt_angles, color="black", linewidth=1.5, linestyle="--",
            label="Ground Truth", zorder=5)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Steering Angle (deg)")
    ax.set_title("Models Mean ± Std vs Ground Truth")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(base_dir, "video_model_comparison.png")
    plt.savefig(save_path, dpi=150)
    print(f"\nSaved: {save_path}")

    print("\n" + "=" * 55)
    print(f"{'Model':<15} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8}")
    print("-" * 55)
    for name in models:
        angles = np.array(results[name])
        print(f"{name:<15} {np.mean(angles):>7.2f} {np.std(angles):>7.2f} "
              f"{np.min(angles):>7.2f} {np.max(angles):>7.2f}")
    print("=" * 55)



if __name__ == "__main__":
    main()
