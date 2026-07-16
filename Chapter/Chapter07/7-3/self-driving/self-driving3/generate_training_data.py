import os
import sys
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base_dir = os.path.dirname(os.path.abspath(__file__))

VIDEO_PATH = os.path.join(base_dir, "TEST2.mp4")
OUTPUT_DIR = os.path.join(base_dir, "video")
os.makedirs(OUTPUT_DIR, exist_ok=True)

USE_FRAMES = None


def estimate_angle(frame):
    height, width = frame.shape[:2]
    cropped = frame[int(height * 0.5):, :, :]
    crop_h, crop_w = cropped.shape[:2]
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blur)

    dark_thresh = int(np.percentile(enhanced, 15))
    _, thresh = cv2.threshold(enhanced, dark_thresh, 255, cv2.THRESH_BINARY_INV)

    mid_x = crop_w // 2
    min_tape_width = 100

    scan_ys = np.linspace(20, crop_h - 20, 12).astype(int)

    left_inner_xs = []
    right_inner_xs = []
    valid_ys = []

    for sy in scan_ys:
        row = thresh[sy, :]

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
            x += 1

        if lx is not None:
            left_inner_xs.append(lx)
            valid_ys.append(sy)
        if rx is not None:
            right_inner_xs.append(rx)

    if len(valid_ys) >= 3 and len(left_inner_xs) >= 3 and len(right_inner_xs) >= 3:
        n = min(len(left_inner_xs), len(right_inner_xs), len(valid_ys))
        lx_arr = np.array(left_inner_xs[:n])
        rx_arr = np.array(right_inner_xs[:n])
        ys_arr = np.array(valid_ys[:n])

        center_xs = (lx_arr + rx_arr) / 2.0

        top_y = ys_arr[0]
        bot_y = ys_arr[-1]
        top_cx = center_xs[0]
        bot_cx = center_xs[-1]

        dx = bot_cx - top_cx
        dy = bot_y - top_y
        if dy > 0:
            angle_rad = np.arctan2(dx, dy)
            angle_deg = np.degrees(angle_rad)
            steer = 90 - angle_deg
            return int(np.clip(steer, 0, 180))

    return 90


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

    saved_count = 0
    all_angles = []

    print(f"\nProcessing video and saving images to: {OUTPUT_DIR}")
    print("Press Ctrl+C to stop early\n")

    try:
        for frame_idx in range(use_frames):
            ret, frame = cap.read()
            if not ret:
                break

            angle = estimate_angle(frame)
            all_angles.append(angle)
            orig_filename = f"train_{saved_count + 1:06d}_{angle:03d}.png"
            cv2.imwrite(os.path.join(OUTPUT_DIR, orig_filename), frame)
            saved_count += 1

            flipped_frame = cv2.flip(frame, 1)
            flipped_angle = 180 - angle
            all_angles.append(flipped_angle)
            flip_filename = f"train_{saved_count + 1:06d}_{flipped_angle:03d}.png"
            cv2.imwrite(os.path.join(OUTPUT_DIR, flip_filename), flipped_frame)
            saved_count += 1

            if (frame_idx + 1) % 100 == 0:
                print(f"  Frame {frame_idx + 1}/{use_frames} | Saved {saved_count} images | Angle: {angle} -> Flipped: {flipped_angle}")

    except KeyboardInterrupt:
        print(f"\nStopped early at frame {frame_idx}")

    cap.release()

    if all_angles:
        angles_arr = np.array(all_angles)
        plt.figure(figsize=(12, 5))
        plt.hist(angles_arr, bins=180, range=(0, 180), color='steelblue', edgecolor='black', linewidth=0.3)
        plt.xlabel('Steering Angle (0-180)')
        plt.ylabel('Count')
        plt.title(f'Steering Angle Distribution (Total: {len(all_angles)} frames)')
        plt.axvline(x=90, color='red', linestyle='--', label='Center (90)')
        plt.legend()
        plt.tight_layout()
        plot_path = os.path.join(base_dir, "steering_angles.png")
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"\nAngle distribution saved to: {plot_path}")

    print(f"\nDone! Saved {saved_count} images to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
