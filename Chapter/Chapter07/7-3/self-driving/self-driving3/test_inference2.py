import os
import re
import sys
import cv2
import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base_dir = os.path.dirname(os.path.abspath(__file__))

MODEL_DIRS = {
    "invert":       os.path.join(base_dir, "model-20260715_221419_invert"),
    "otsu":         os.path.join(base_dir, "model-20260715_222327_otsu"),
    "adaptive":     os.path.join(base_dir, "model-20260715_223150_adaptive"),
    "invert_clahe": os.path.join(base_dir, "model-20260715_224033_invert_clahe"),
}

VIDEO_PATH = os.path.join(base_dir, "TEST2.mp4")
GT_DIR = os.path.join(base_dir, "video")
OUTPUT_DIR = os.path.join(base_dir, "test2_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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


def load_model_from_dir(model_dir):
    model = NvidiaModel().to(device)
    pt_path = os.path.join(model_dir, "lane_navigation_best.pt")
    checkpoint = torch.load(pt_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    val_loss = checkpoint.get("val_loss", None)
    return model, val_loss


def load_ground_truth(gt_dir):
    gt_angles = {}
    files = sorted([f for f in os.listdir(gt_dir) if f.endswith(".png")])
    for i, filename in enumerate(files):
        match = re.search(r'_(\d{3})\.png$', filename)
        if match:
            gt_angles[i] = int(match.group(1))
    return gt_angles


def main():
    import glob as glob_module

    if len(sys.argv) < 2:
        print(f"Usage: python {os.path.basename(__file__)} <model_keyword> [gt_folder] [output_folder]")
        print(f"  model_keyword: partial model folder name (e.g. 20260715_221419)")
        print(f"  gt_folder: ground truth folder (default: video)")
        print(f"  output_folder: output folder (default: test2_results_<keyword>)")
        print(f"")
        print(f"Examples:")
        print(f"  python {os.path.basename(__file__)} 20260715_224033")
        print(f"  python {os.path.basename(__file__)} 20260715_224033 video_shifted_m10")
        print(f"  python {os.path.basename(__file__)} 20260715_224033 video_shifted_m10 results_m10")
        sys.exit(1)

    keyword = sys.argv[1]
    gt_folder = sys.argv[2] if len(sys.argv) > 2 else "video"
    output_folder = sys.argv[3] if len(sys.argv) > 3 else f"test2_results_{keyword}"

    gt_dir = os.path.join(base_dir, gt_folder)
    output_dir = os.path.join(base_dir, output_folder)
    os.makedirs(output_dir, exist_ok=True)

    model_dirs = {}
    for d in glob_module.glob(os.path.join(base_dir, f"model-*_{keyword}")):
        folder_name = os.path.basename(d)
        filter_name = folder_name.split("_")[-1]
        model_dirs[filter_name] = d

    if not model_dirs:
        print(f"ERROR: No model folders found matching keyword: {keyword}")
        sys.exit(1)

    print(f"Found {len(model_dirs)} model(s): {list(model_dirs.keys())}")

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

    gt_angles = load_ground_truth(gt_dir)
    print(f"  Ground truth: {len(gt_angles)} files loaded from {gt_dir}")

    models = {}
    for name, md in model_dirs.items():
        try:
            m, vl = load_model_from_dir(md)
            models[name] = m
            print(f"  Loaded model: {name} (best_val_loss={vl:.4f})")
        except Exception as e:
            print(f"  FAILED to load model {name}: {e}")

    if not models:
        print("ERROR: No models loaded")
        sys.exit(1)

    predictions = {name: [] for name in models}
    ground_truth = []

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx in gt_angles:
            ground_truth.append((frame_idx, gt_angles[frame_idx]))

        for name, model in models.items():
            filtered = apply_filter(frame, name)
            input_tensor = preprocess_for_inference(filtered)
            input_batch = torch.from_numpy(input_tensor).float().unsqueeze(0).to(device)
            with torch.no_grad():
                pred = model(input_batch)
            angle = pred.item()
            predictions[name].append((frame_idx, angle))

        frame_idx += 1

    cap.release()
    print(f"\nProcessed {frame_idx} frames")

    colors = {"invert": "#2196F3", "otsu": "#FF9800", "adaptive": "#4CAF50", "invert_clahe": "#E91E63"}

    gt_frames = [g[0] for g in ground_truth]
    gt_vals = [g[1] for g in ground_truth]

    fig, axes = plt.subplots(len(models) + 1, 1, figsize=(16, 4 * (len(models) + 1)), sharex=True)
    if len(models) + 1 == 1:
        axes = [axes]

    axes[0].plot(gt_frames, gt_vals, color="black", linewidth=1.0, label="Ground Truth")
    axes[0].set_ylabel("Angle (deg)")
    axes[0].set_title("Ground Truth (from training data)")
    axes[0].axhline(y=90, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    for ax, (name, preds) in zip(axes[1:], predictions.items()):
        frames = [p[0] for p in preds]
        angles = [p[1] for p in preds]
        ax.plot(frames, angles, color=colors.get(name, "gray"), linewidth=0.8, label=f"{name}")
        ax.plot(gt_frames, gt_vals, color="black", linewidth=0.5, alpha=0.4, label="Ground Truth")
        ax.set_ylabel("Angle (deg)")
        ax.set_title(f"Model: {name} vs Ground Truth")
        ax.axhline(y=90, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Frame")
    plt.tight_layout()
    chart_path = os.path.join(output_dir, "prediction_vs_gt_chart.png")
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"\nSaved: {chart_path}")

    gt_by_frame = {g[0]: g[1] for g in ground_truth}

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for ax, (name, preds) in zip(axes, predictions.items()):
        pred_vals = [p[1] for p in preds if p[0] in gt_by_frame]
        gt_matched = [gt_by_frame[p[0]] for p in preds if p[0] in gt_by_frame]

        errors = [p - g for p, g in zip(pred_vals, gt_matched)]
        ax.hist(errors, bins=40, color=colors.get(name, "gray"), edgecolor="black", alpha=0.7)
        mean_err = np.mean(errors)
        std_err = np.std(errors)
        ax.axvline(mean_err, color="red", linestyle="--", linewidth=2,
                   label=f"Mean: {mean_err:.2f}\nStd: {std_err:.2f}")
        ax.axvline(0, color="black", linestyle=":", linewidth=1)
        ax.set_title(f"Prediction Error - {name}")
        ax.set_xlabel("Error (Pred - GT, deg)")
        ax.set_ylabel("Frequency")
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    err_path = os.path.join(output_dir, "error_distribution.png")
    plt.savefig(err_path, dpi=150)
    plt.close()
    print(f"Saved: {err_path}")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for ax, (name, preds) in zip(axes, predictions.items()):
        pred_vals = [p[1] for p in preds if p[0] in gt_by_frame]
        gt_matched = [gt_by_frame[p[0]] for p in preds if p[0] in gt_by_frame]

        ax.scatter(gt_matched, pred_vals, s=5, alpha=0.5, color=colors.get(name, "gray"))
        min_val = min(min(gt_matched), min(pred_vals)) - 2
        max_val = max(max(gt_matched), max(pred_vals)) + 2
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=1, label="Ideal (y=x)")
        ax.set_xlim(min_val, max_val)
        ax.set_ylim(min_val, max_val)
        ax.set_xlabel("Ground Truth (deg)")
        ax.set_ylabel("Predicted (deg)")
        ax.set_title(f"Scatter Plot - {name}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")

    plt.tight_layout()
    scatter_path = os.path.join(output_dir, "scatter_vs_gt.png")
    plt.savefig(scatter_path, dpi=150)
    plt.close()
    print(f"Saved: {scatter_path}")

    print("\n" + "=" * 80)
    print(f"{'Model':<15} {'MAE':>8} {'RMSE':>8} {'MaxErr':>8} {'Mean':>8} {'Std':>8}")
    print("-" * 80)
    for name, preds in predictions.items():
        pred_vals = np.array([p[1] for p in preds if p[0] in gt_by_frame])
        gt_matched = np.array([gt_by_frame[p[0]] for p in preds if p[0] in gt_by_frame])
        errors = pred_vals - gt_matched
        mae = np.mean(np.abs(errors))
        rmse = np.sqrt(np.mean(errors**2))
        max_err = np.max(np.abs(errors))
        print(f"{name:<15} {mae:>7.3f} {rmse:>7.3f} {max_err:>7.3f} {np.mean(pred_vals):>7.2f} {np.std(pred_vals):>7.2f}")
    print("=" * 80)

    print(f"\nAll results saved to: {output_dir}")


if __name__ == "__main__":
    main()
