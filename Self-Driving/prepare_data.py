"""
prepare_data.py
Self-Driving 데이터 준비: 영상 프레임 추출 + 차선 감지 + 가상 조향각 생성
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
      - 바닥면(하단 1/3)의 차선 위치를 감지
      - 이미지 중앙 대비 차선의偏移(offset)으로 조향각 계산
      - 값 범위: -1 (좌회전) ~ 0 (직진) ~ +1 (우회전)
    """

    h, w = frame.shape[:2]

    # 1) 바닥면 ROI (하단 1/3, 전체 너비)
    roi_top = int(h * 2 / 3)
    roi = frame[roi_top:, :]

    # 2) 전처리: 그레이 → 가우시안 블러 → Canny 에지
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    # 3) Hough 변환으로 직선(차선) 검출
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30,
                            minLineLength=20, maxLineGap=50)

    vis = frame.copy()
    steering = 0.0
    detected = False

    if lines is not None:
        left_xs, right_xs = [], []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 수평선 제외
            if abs(y2 - y1) < 5:
                continue

            # 차선 위에 그리기
            cv2.line(vis, (x1, roi_top + y1), (x2, roi_top + y2),
                     (0, 255, 0), 3)

            # 기울기와 x위치로 좌/우 차선 분류
            slope = (y2 - y1) / (x2 - x1 + 1e-6)
            if slope > 0.2:   # 우측 차선 (기울기 양수)
                right_xs.append((x1 + x2) // 2)
            elif slope < -0.2:  # 좌측 차선 (기울기 음수)
                left_xs.append((x1 + x2) // 2)

        center_x = w // 2

        if left_xs and right_xs:
            detected = True
            left_x = np.mean(left_xs)
            right_x = np.mean(right_xs)
            lane_center = (left_x + right_x) / 2
            offset = (lane_center - center_x) / (center_x / 2)
            steering = np.clip(offset, -1.0, 1.0)

            # 시각화: 차선 중심선
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

        # 중앙 마커
        cv2.line(vis, (center_x, roi_top), (center_x, h), (0, 0, 255), 1)

    return vis, steering, detected


def draw_steering_info(img, steering, frame_idx):
    """조향각 정보를 이미지에 표시"""
    h, w = img.shape[:2]
    # 조향각 텍스트
    label = f"Steering: {steering:+.3f}"
    cv2.putText(img, label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2)

    # 조향 바
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


# ===================== 메인 처리 =====================

def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"총 프레임: {total_frames}, FPS: {fps:.1f}")

    frame_idx = 0
    saved_count = 0
    dataset = []  # (파일명, 조향각)

    print("\n영상 처리 시작 (ESC 누르면 중단)...\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # FRAME_STEP 간격으로 처리
        if frame_idx % FRAME_STEP == 0:
            # 차선 검출 + 조향각 계산
            vis_img, steering, detected = detect_lanes_and_steering(frame)

            # 차선이 검출된 프레임만 저장 (학습 품질 향상)
            if detected:
                # 학습용 작은 이미지로 리사이즈
                small = cv2.resize(frame, (IMG_WIDTH, IMG_HEIGHT))
                small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                filename = f"frame_{saved_count:04d}.npy"
                np.save(os.path.join(OUTPUT_DIR, filename), small)
                dataset.append({"file": filename, "steering": round(steering, 4)})
                saved_count += 1

                # 시각화
                vis_img = draw_steering_info(vis_img, steering, frame_idx)
                vis_small = cv2.resize(vis_img, (960, 540))
                cv2.imshow("Lane Detection & Steering", vis_small)

            if frame_idx % 30 == 0:
                print(f"  Frame {frame_idx}/{total_frames} | Detected: {detected} | Saved: {saved_count}")

        frame_idx += 1
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

    # 메타데이터 저장
    metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump({"fps": fps, "total_frames": total_frames,
                    "saved_samples": saved_count, "data": dataset}, f, indent=2)

    print(f"\n완료!")
    print(f"  전체 프레임: {total_frames}")
    print(f"  저장된 샘플: {saved_count}")
    print(f"  메타데이터: {metadata_path}")
    print(f"  이미지 크기: {IMG_WIDTH}x{IMG_HEIGHT}")


if __name__ == "__main__":
    main()
