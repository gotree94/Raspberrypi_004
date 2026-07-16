import cv2
import numpy as np
import os
import random
import json
import matplotlib

VIDEO_DIR = r"video"
ANNOT_FILE = r"annotations.json"

if os.path.exists(ANNOT_FILE):
    with open(ANNOT_FILE, "r") as f:
        ANNOTATIONS = json.load(f)
else:
    ANNOTATIONS = {}


def preprocess(frame):
    cropped = frame.copy()
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blur)
    dark_thresh = int(np.percentile(enhanced, 15))
    _, thresh = cv2.threshold(enhanced, dark_thresh, 255, cv2.THRESH_BINARY_INV)
    return cropped, gray, blur, enhanced, thresh, dark_thresh


def draw_annotations(img, fname, scale):
    if fname not in ANNOTATIONS:
        return
    ann = ANNOTATIONS[fname]
    colors = {
        "left_inner": (0, 255, 0),
        "left_outer": (0, 200, 0),
        "right_inner": (0, 0, 255),
        "right_outer": (0, 0, 200),
    }
    labels = {"left_inner": "L1", "left_outer": "L2", "right_inner": "R1", "right_outer": "R2"}
    for side, pts in ann.items():
        if not pts or len(pts) < 2:
            continue
        color = colors.get(side, (255, 255, 255))
        p1 = (int(pts[0][0] * scale), int(pts[0][1] * scale))
        p2 = (int(pts[1][0] * scale), int(pts[1][1] * scale))
        cv2.line(img, p1, p2, color, 1)
        label = labels.get(side, side)
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2
        cv2.putText(img, label, (mx - 10, my - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def detect_and_draw(frame):
    cropped, gray, blur, enhanced, thresh, dark_thresh = preprocess(frame)
    crop_h, crop_w = cropped.shape[:2]
    mid_x = crop_w // 2
    min_tape_width = 50
    scan_ys = np.linspace(20, crop_h - 20, 16).astype(int)

    left_inner = []
    right_inner = []
    debug_img = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
    cv2.line(debug_img, (mid_x, 0), (mid_x, crop_h), (128, 128, 128), 1)

    print(f"  crop: {crop_w}x{crop_h}, mid_x={mid_x}, dark_thresh={dark_thresh}, min_tape={min_tape_width}")

    for sy in scan_ys:
        row = thresh[sy, :]
        white_count = int(np.sum(row > 0))

        white_runs = []
        x = 0
        while x < crop_w:
            if row[x] > 0:
                start = x
                while x < crop_w and row[x] > 0:
                    x += 1
                white_runs.append((start, x - 1, x - start))
            else:
                x += 1

        lx = None
        x = mid_x
        while x >= 0:
            if row[x] > 0:
                run_end = x
                while x >= 0 and row[x] > 0:
                    x -= 1
                run_start = x + 1
                run_len = run_end - run_start + 1
                if run_len >= min_tape_width:
                    lx = run_end
                    break
            x -= 1

        rx = None
        x = mid_x
        while x < crop_w:
            if row[x] > 0:
                run_start = x
                while x < crop_w and row[x] > 0:
                    x += 1
                run_end = x - 1
                run_len = run_end - run_start + 1
                if run_len >= min_tape_width:
                    rx = run_start
                    break
            x += 1

        runs_str = " ".join([f"[{s}-{e}:w{w}]" for s, e, w in white_runs])
        lx_str = f"x={lx}" if lx is not None else "FAIL"
        rx_str = f"x={rx}" if rx is not None else "FAIL"
        print(f"  y={sy:3d} white={white_count:3d} runs={len(white_runs)} {runs_str}")
        print(f"         L: {lx_str}  R: {rx_str}")

        if lx is not None:
            left_inner.append((lx, sy))
            cv2.circle(debug_img, (lx, sy), 6, (0, 255, 255), -1)
        if rx is not None:
            right_inner.append((rx, sy))
            cv2.circle(debug_img, (rx, sy), 6, (255, 0, 255), -1)

    print(f"  Result: L={len(left_inner)} R={len(right_inner)}")

    steer = 90
    if len(left_inner) >= 3 and len(right_inner) >= 3:
        n = min(len(left_inner), len(right_inner))
        lx_arr = np.array([p[0] for p in left_inner[:n]])
        rx_arr = np.array([p[0] for p in right_inner[:n]])
        ys_arr = np.array([p[1] for p in left_inner[:n]])
        center_xs = (lx_arr + rx_arr) / 2.0

        top_cx, bot_cx = center_xs[0], center_xs[-1]
        top_y, bot_y = ys_arr[0], ys_arr[-1]
        cv2.line(debug_img, (int(top_cx), int(top_y)), (int(bot_cx), int(bot_y)), (0, 165, 255), 3)
        cv2.line(debug_img, (mid_x, 0), (mid_x, crop_h), (128, 128, 128), 2)

        dx = bot_cx - top_cx
        dy = bot_y - top_y
        if dy > 0:
            steer = 90 - np.degrees(np.arctan2(dx, dy))
            steer = float(np.clip(steer, 0, 180))
            cv2.putText(debug_img, f"Angle: {steer:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    return debug_img, gray, blur, enhanced, thresh, steer, dark_thresh


def make_panel(images, labels, panel_w=480):
    resized = []
    for img, label in zip(images, labels):
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        scale = panel_w / w
        disp = cv2.resize(img, (panel_w, int(h * scale)))
        cv2.putText(disp, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        resized.append(disp)

    h = max(r.shape[0] for r in resized)
    w = max(r.shape[1] for r in resized)

    panels = []
    for r in resized:
        pad = np.zeros((h, w, 3), dtype=np.uint8)
        pad[:r.shape[0], :r.shape[1]] = r
        panels.append(pad)

    return np.vstack(panels)


def main():
    files = sorted([f for f in os.listdir(VIDEO_DIR) if f.startswith("train_") and f.endswith(".png")])
    samples = files
    print(f"Processing {len(samples)} samples\n")

    out_dir = os.path.join(VIDEO_DIR, "_debug_output")
    os.makedirs(out_dir, exist_ok=True)

    results = []
    for i, fname in enumerate(samples):
        frame = cv2.imread(os.path.join(VIDEO_DIR, fname))
        if frame is None:
            continue

        debug_img, gray, blur, enhanced, thresh, steer, dark_thresh = detect_and_draw(frame)

        if fname in ANNOTATIONS:
            ann = ANNOTATIONS[fname]
            crop_y = frame.shape[0] // 2
            colors = {
                "left_inner": (0, 255, 255),
                "left_outer": (0, 200, 200),
                "right_inner": (255, 0, 255),
                "right_outer": (200, 0, 200),
            }
            labels_dict = {"left_inner": "L1", "left_outer": "L2", "right_inner": "R1", "right_outer": "R2"}
            for side, pts in ann.items():
                if not pts or len(pts) < 2:
                    continue
                color = colors.get(side, (255, 255, 255))
                p1 = (int(pts[0][0]), int(pts[0][1] - crop_y))
                p2 = (int(pts[1][0]), int(pts[1][1] - crop_y))
                h_orig = debug_img.shape[0]
                if 0 <= p1[1] < h_orig and 0 <= p2[1] < h_orig:
                    cv2.line(debug_img, p1, p2, color, 3)
                    mx = (p1[0] + p2[0]) // 2
                    my = (p1[1] + p2[1]) // 2
                    cv2.putText(debug_img, labels_dict.get(side, side), (mx - 15, my - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        orig_num = fname.split('_')[1]
        out_name = f"train_{orig_num}_{int(steer):03d}.png"
        out_path = os.path.join(out_dir, out_name)
        cv2.imwrite(out_path, debug_img)
        results.append((out_name, steer))
        print(f"  [{i+1}/{len(samples)}] {fname} -> {out_name} (angle={steer:.1f})")

    print(f"\nDone. {len(results)} images saved to {out_dir}")

    good = [r for r in results if 45 <= r[1] <= 135]
    bad = [r for r in results if r[1] < 45 or r[1] > 135]
    print(f"  Good (45-135): {len(good)}")
    print(f"  Edge (<45 or >135): {len(bad)}")
    if bad:
        print("  Edge cases:")
        for fname, angle in sorted(bad, key=lambda x: x[1]):
            print(f"    {fname} -> {angle:.1f}")

    if results:
        angles = [r[1] for r in results]

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f"Steering Angles Debug ({len(results)} frames)", fontsize=14)

        ax1.hist(angles, bins=50, color="steelblue", edgecolor="black", alpha=0.8)
        ax1.axvline(x=90, color="red", linestyle="--", label="Center (90)")
        ax1.set_xlabel("Angle (0=Left, 180=Right)")
        ax1.set_ylabel("Count")
        ax1.set_title("Angle Distribution")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.plot(range(len(angles)), angles, color="steelblue", linewidth=0.8, alpha=0.8)
        ax2.axhline(y=90, color="red", linestyle="--", label="Center (90)")
        ax2.set_xlabel("Frame")
        ax2.set_ylabel("Angle")
        ax2.set_title("Angle over Time")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        chart_path = os.path.join(out_dir, "steering_angles_debug.png")
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"\nChart saved: {chart_path}")


if __name__ == "__main__":
    main()
