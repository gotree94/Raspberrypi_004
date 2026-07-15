import os
import sys
import fnmatch
import random
import pickle
from datetime import datetime
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

base_dir = os.path.dirname(__file__)

AVAILABLE_DIRS = {
    "video":           os.path.join(base_dir, "video"),
    "cropped":         os.path.join(base_dir, "processed", "cropped"),
    "invert":          os.path.join(base_dir, "processed", "filter_invert_resized"),
    "otsu":            os.path.join(base_dir, "processed", "filter_otsu_resized"),
    "adaptive":        os.path.join(base_dir, "processed", "filter_adaptive_resized"),
    "invert_clahe":    os.path.join(base_dir, "processed", "filter_invert_clahe_resized"),
    "resized":         os.path.join(base_dir, "processed", "resized"),
}

batch_size = 100
epochs = 10
lr = 1e-3
steps_per_epoch = 300
validation_steps = 200
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

AUG_PROB = 0.5
ROTATION_RANGE = 10
SHIFT_RANGE = 15
BRIGHTNESS_RANGE = 0.3
CONTRAST_RANGE = 0.3
BLUR_KSIZE = 5
NOISE_STD = 0.05
ANGLE_JITTER = 2.0


def print_usage():
    print(f"Usage: python {os.path.basename(__file__)} <data_source>")
    print(f"\nAvailable data sources:")
    for key, path in AVAILABLE_DIRS.items():
        count = len([f for f in os.listdir(path) if f.endswith(".png")]) if os.path.isdir(path) else 0
        print(f"  {key:15s} -> {path} ({count} images)")
    print(f"\nExample: python {os.path.basename(__file__)} video")


def list_image_paths_and_angles(folder):
    paths, angles = [], []
    for filename in os.listdir(folder):
        if fnmatch.fnmatch(filename, "*.png"):
            paths.append(os.path.join(folder, filename))
            angle = int(filename[-7:-4])
            angles.append(float(angle))
    return paths, angles


def train_valid_split(paths, angles, valid_ratio=0.2):
    idxs = list(range(len(paths)))
    random.shuffle(idxs)
    n = len(idxs)
    n_valid = int(n * valid_ratio)
    valid_idx = idxs[:n_valid]
    train_idx = idxs[n_valid:]
    X_train = [paths[i] for i in train_idx]
    y_train = [angles[i] for i in train_idx]
    X_valid = [paths[i] for i in valid_idx]
    y_valid = [angles[i] for i in valid_idx]
    return X_train, X_valid, y_train, y_valid


def augment_image(img_bgr, angle):
    h, w = img_bgr.shape[:2]

    if random.random() < AUG_PROB:
        img_bgr = cv2.flip(img_bgr, 1)
        angle = 180.0 - angle

    if random.random() < AUG_PROB:
        rot_deg = random.uniform(-ROTATION_RANGE, ROTATION_RANGE)
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot_deg, 1.0)
        img_bgr = cv2.warpAffine(img_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        angle += rot_deg

    if random.random() < AUG_PROB:
        shift_x = random.uniform(-SHIFT_RANGE, SHIFT_RANGE)
        M = np.float32([[1, 0, shift_x], [0, 1, 0]])
        img_bgr = cv2.warpAffine(img_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        angle += (shift_x / w) * 20.0

    if random.random() < AUG_PROB:
        brightness = random.uniform(1.0 - BRIGHTNESS_RANGE, 1.0 + BRIGHTNESS_RANGE)
        contrast = random.uniform(1.0 - CONTRAST_RANGE, 1.0 + CONTRAST_RANGE)
        img_f = img_bgr.astype(np.float32)
        mean_val = img_f.mean()
        img_f = (img_f - mean_val) * contrast + mean_val
        img_f = img_f * brightness
        img_f = np.clip(img_f, 0, 255)
        img_bgr = img_f.astype(np.uint8)

    if random.random() < AUG_PROB:
        if random.random() < 0.5:
            ksize = BLUR_KSIZE if BLUR_KSIZE % 2 == 1 else BLUR_KSIZE + 1
            img_bgr = cv2.GaussianBlur(img_bgr, (ksize, ksize), 0)
        else:
            noise = np.random.normal(0, NOISE_STD * 255, img_bgr.shape).astype(np.float32)
            img_f = img_bgr.astype(np.float32) + noise
            img_bgr = np.clip(img_f, 0, 255).astype(np.uint8)

    if random.random() < AUG_PROB:
        angle += random.uniform(-ANGLE_JITTER, ANGLE_JITTER)

    return img_bgr, angle


def preprocess_for_training(bgr, need_resize=True):
    if need_resize:
        bgr = cv2.resize(bgr, (200, 66))
    img = bgr.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    return img


def infinite_batch(image_paths, steering_angles, batch_size, need_resize=True, augment=False):
    n = len(image_paths)
    assert n > 0
    while True:
        idxs = np.random.randint(0, n, size=batch_size)
        xs, ys = [], []
        for i in idxs:
            img = cv2.imread(image_paths[i], cv2.IMREAD_COLOR)
            if img is None:
                raise FileNotFoundError(image_paths[i])
            angle = steering_angles[i]
            if augment:
                img, angle = augment_image(img, angle)
            x = preprocess_for_training(img, need_resize)
            xs.append(x)
            ys.append([angle])
        x_batch = torch.from_numpy(np.stack(xs)).float()
        y_batch = torch.from_numpy(np.array(ys, dtype=np.float32))
        yield x_batch, y_batch


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


def train_one_epoch(model, optimizer, criterion, train_gen, steps_per_epoch):
    model.train()
    run_loss = 0.0
    seen = 0
    for _ in range(steps_per_epoch):
        x, y = next(train_gen)
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad(set_to_none=True)
        pred = model(x)
        loss = criterion(pred, y)
        loss.backward()
        optimizer.step()
        bs = x.size(0)
        run_loss += loss.item() * bs
        seen += bs
    return run_loss / max(seen, 1)


@torch.no_grad()
def evaluate(model, criterion, valid_gen, validation_steps):
    model.eval()
    total_loss, total_mae = 0.0, 0.0
    seen = 0
    for _ in range(validation_steps):
        x, y = next(valid_gen)
        x, y = x.to(device), y.to(device)
        pred = model(x)
        loss = criterion(pred, y)
        mae = torch.mean(torch.abs(pred - y))
        bs = x.size(0)
        total_loss += loss.item() * bs
        total_mae += mae.item() * bs
        seen += bs
    if seen == 0:
        return float('inf'), float('inf')
    return total_loss / seen, total_mae / seen


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in AVAILABLE_DIRS:
        print_usage()
        sys.exit(1)

    src_key = sys.argv[1]
    data_dir = AVAILABLE_DIRS[src_key]
    need_resize = (src_key in ("video", "cropped"))

    print(f"Data source : {src_key}")
    print(f"Directory   : {data_dir}")
    print(f"Resize      : {need_resize}")
    print(f"Device      : {device}")
    print(f"Augmentation: ON (flip, rotation, shift, brightness/contrast, blur/noise, jitter)")

    paths, angles = list_image_paths_and_angles(data_dir)
    if len(paths) == 0:
        raise RuntimeError(f'No PNG images found in: {data_dir}')

    X_train, X_valid, y_train, y_valid = train_valid_split(paths, angles, valid_ratio=0.2)
    print(f"Train: {len(X_train)} | Valid: {len(X_valid)}")

    model = NvidiaModel().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(base_dir, f"model-{timestamp}")
    os.makedirs(save_dir, exist_ok=True)

    best_val = float("inf")
    history = {"train_loss": [], "val_loss": [], "val_mae": []}

    train_gen = infinite_batch(X_train, y_train, batch_size, need_resize, augment=True)
    valid_gen = infinite_batch(X_valid, y_valid, batch_size, need_resize, augment=False)

    for ep in range(1, epochs + 1):
        tr_loss = train_one_epoch(model, optimizer, criterion, train_gen, steps_per_epoch)
        val_loss, val_mae = evaluate(model, criterion, valid_gen, validation_steps)

        old_lr = optimizer.param_groups[0]["lr"]
        scheduler.step(val_loss)
        new_lr = optimizer.param_groups[0]["lr"]
        if new_lr != old_lr:
            print(f"[scheduler] LR reduced: {old_lr:.6f} -> {new_lr:.6f}")

        history["train_loss"].append(tr_loss)
        history["val_loss"].append(val_loss)
        history["val_mae"].append(val_mae)

        print(f"Epoch {ep:02d}/{epochs} | train_loss={tr_loss:.5f} | val_loss={val_loss:.5f} | val_MAE(deg)={val_mae:.3f}")

        if val_loss < best_val:
            best_val = val_loss
            best_pt = os.path.join(save_dir, "lane_navigation_best.pt")
            torch.save({"model_state": model.state_dict(), "val_loss": val_loss}, best_pt)
            print(f"Saved BEST checkpoint -> {best_pt}")

    final_pt = os.path.join(save_dir, "lane_navigation_final.pt")
    torch.save({"model_state": model.state_dict()}, final_pt)
    print(f"Saved final weights -> {final_pt}")

    model.eval()
    example = torch.zeros(1, 3, 66, 200, device=device)
    traced = torch.jit.trace(model, example)
    ts_path = os.path.join(save_dir, "lane_navigation_final.torchscript")
    traced.save(ts_path)
    print(f"Saved TorchScript -> {ts_path}")

    hist_path = os.path.join(save_dir, "history.pickle")
    with open(hist_path, "wb") as f:
        pickle.dump(history, f, pickle.HIGHEST_PROTOCOL)
    print(f"Saved history -> {hist_path}")

    print(f"Training complete. Model saved to: {save_dir}")


if __name__ == "__main__":
    main()
