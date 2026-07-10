"""
prepare_data.py
Self-Driving 데이터 준비: 영상 프레임 추출 + 차선 감지 + 가상 조향각 생성
개선 v2: Canny/ROI/Hough 최적화, 각도 스무딩, 데이터 균형
"""

import cv2
import numpy as np
import os
import json

# ===================== 설정 =====================
VIDEO_PATH = r"C:\Users\Administrator\Desktop\Self-Driving\Self-driving.mp4"
OUTPUT_DIR = r"C:\Users\Administrator\Desktop\Self-Driving\training_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FRAME_STEP = 3        # 모든 프레임을 다 쓰면 너무 많음 → 3프레임마다 1개 추출
IMG_WIDTH = 160       # CPU 학습을 위해 작은 해상도
IMG_HEIGHT = 80

# ===================== 차선 검출 + 조향각 계산 =====================

def detect_lanes_and_steering(frame):
    """
    입력: BGR 프레임 (1920x1080)
    반환: (차선이 그려진 시각화 이미지, 조향각(-1~1), 차선검출성공여부)

    조향각 계산 원리:
      - 바닥면(하단 ~55%)의 차선 위치를 감지
      - 이미지 중앙 대비 차선의 偏移(offset)으로 조향각 계산
      - 값 범위: -1 (좌회전) ~ 0 (직진) ~ +1 (우회전)
    """

    h, w = frame.shape[:2]

    # 1) ROI 확대 (하단 55%, 곡선 인지 향상)
    roi_top = int(h * 0.55)
    roi = frame[roi_top:, :]

    # 2) 전처리: 그레이 → 가우시안 블러 → Canny 에지 (더 민감하게)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 30, 100)

    # 3) Hough 변환으로 직선(차선) 검출 (더 긴 직선 위주, 노이즈 제거)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40,
                            minLineLength=30, maxLineGap=40)

    vis = frame.copy()
    steering = 0.0
    detected = False

    if lines is not None:
        left_xs, right_xs = [], []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 5:
                continue

            cv2.line(vis, (x1, roi_top + y1), (x2, roi_top + y2),
                     (0, 255, 0), 3)

            slope = (y2 - y1) / (x2 - x1 + 1e-6)
            if slope > 0.2:
                right_xs.append((x1 + x2) // 2)
            elif slope < -0.2:
                left_xs.append((x1 + x2) // 2)

        center_x = w // 2

        if left_xs and right_xs:
            detected = True
            left_x = np.mean(left_xs)
            right_x = np.mean(right_xs)
            lane_center = (left_x + right_x) / 2
            offset = (lane_center - center_x) / (center_x / 2)
            steering = np.clip(offset, -1.0, 1.0)

            cv2.line(vis, (int(lane_center), roi_top),
                     (int(lane_center), h), (255, 0, 0), 2)
        elif left_xs:
            detected = True
            left_x = np.mean(left_xs)
            offset = (left_x - center_x) / (center_x / 2) - 0.3
            steering = np.clip(offset, -1.0, 1.0)
        elif right_xs:
            detected = True
            right_x = np.mean(right_xs)
            offset = (right_x - center_x) / (center_x / 2) + 0.3
            steering = np.clip(offset, -1.0, 1.0)

        cv2.line(vis, (center_x, roi_top), (center_x, h), (0, 0, 255), 1)

    return vis, steering, detected


def draw_steering_info(img, steering, frame_idx):
    """조향각 정보를 이미지에 표시"""
    h, w = img.shape[:2]
    label = f"Steering: {steering:+.3f}"
    cv2.putText(img, label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2)

    bar_x, bar_y = w // 2, 60
    bar_w, bar_h = 200, 12
    cv2.rectangle(img, (bar_x - bar_w // 2, bar_y),
                  (bar_x + bar_w // 2, bar_y + bar_h), (100, 100, 100), -1)
    indicator_x = int(bar_x + steering * (bar_w // 2))
    color = (0, 255, 0) if abs(steering) < 0.1 else (0, 255, 255) if abs(steering) < 0.4 else (0, 0, 255)
    cv2.circle(img, (indicator_x, bar_y + bar_h // 2), 8, color, -1)

    cv2.putText(img, f"Frame: {frame_idx}", (10, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    return img


# ===================== 후처리 함수 =====================

def smooth_steering_angles(dataset, window=5):
    """조향각 이동평균 스무딩 (급격한 변화 완화)"""
    if window % 2 == 0:
        window += 1
    angles = np.array([item["steering"] for item in dataset])
    kernel = np.ones(window) / window
    smoothed = np.convolve(angles, kernel, mode='same')
    for i, item in enumerate(dataset):
        item["steering"] = round(float(smoothed[i]), 4)
    return dataset


def balance_dataset(dataset, keep_ratio=0.3):
    """직진(0 근처) 데이터를 줄여 클래스 불균형 완화"""
    keep = []
    for item in dataset:
        if abs(item["steering"]) < 0.08:
            if np.random.rand() < keep_ratio:
                keep.append(item)
        else:
            keep.append(item)
    return keep


# ===================== 메인 처리 =====================

def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"총 프레임: {total_frames}, FPS: {fps:.1f}")

    frame_idx = 0
    saved_count = 0
    dataset = []

    print("\n영상 처리 시작 (ESC 누르면 중단)...\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % FRAME_STEP == 0:
            vis_img, steering, detected = detect_lanes_and_steering(frame)

            if detected:
                small = cv2.resize(frame, (IMG_WIDTH, IMG_HEIGHT))
                small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                filename = f"frame_{saved_count:04d}.npy"
                np.save(os.path.join(OUTPUT_DIR, filename), small)
                dataset.append({"file": filename, "steering": round(steering, 4)})
                saved_count += 1

                vis_img = draw_steering_info(vis_img, steering, frame_idx)
                vis_small = cv2.resize(vis_img, (960, 540))
                cv2.imshow("Lane Detection & Steering", vis_small)

            if frame_idx % 30 == 0:
                print(f"  Frame {frame_idx}/{total_frames} | Detected: {detected} | Saved: {saved_count}")

        frame_idx += 1
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    # ===== 후처리 1: 조향각 스무딩 =====
    print(f"\n조향각 스무딩 적용 (window=5)...")
    dataset = smooth_steering_angles(dataset, window=5)

    # ===== 후처리 2: 데이터 균형 맞추기 =====
    print(f"  스무딩 전: {len(dataset)} samples")
    balanced = balance_dataset(dataset, keep_ratio=0.3)
    print(f"  균형 후:  {len(balanced)} samples ({len(dataset) - len(balanced)}개 직진 샘플 제거)")

    # 제거된 샘플의 .npy 파일 삭제
    kept_files = {item["file"] for item in balanced}
    for item in dataset:
        if item["file"] not in kept_files:
            os.remove(os.path.join(OUTPUT_DIR, item["file"]))

    # 메타데이터 저장
    metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump({"fps": fps, "total_frames": total_frames,
                    "saved_samples": len(balanced), "data": balanced}, f, indent=2)

    print(f"\n완료!")
    print(f"  전체 프레임: {total_frames}")
    print(f"  저장된 샘플: {len(balanced)}")
    print(f"  메타데이터: {metadata_path}")
    print(f"  이미지 크기: {IMG_WIDTH}x{IMG_HEIGHT}")


if __name__ == "__main__":
    main()
