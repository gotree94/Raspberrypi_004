"""
simulator.py
Self-Driving 자율주행 시뮬레이터
학습된 모델로 실시간 조향각 예측 + 시각화
"""

import numpy as np
import cv2
import os
import json
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf

# ===================== 설정 =====================
VIDEO_PATH = r"Self-driving.mp4"
MODEL_PATH = r"steering_model.keras"
DATA_DIR = r"training_data"
IMG_WIDTH, IMG_HEIGHT = 160, 80


# ===================== 라이브 차선 검출 (시각화용) =====================

def draw_lane_and_steering(frame, steering_angle, is_autonomous=False):
    """프레임에 차선 정보와 조향각 시각화"""
    h, w = frame.shape[:2]
    vis = frame.copy()

    # 상단 정보 표시줄
    mode_text = "AI AUTO" if is_autonomous else "HUMAN (Ground Truth)"
    mode_color = (0, 200, 0) if is_autonomous else (200, 200, 0)
    cv2.putText(vis, mode_text, (w // 2 - 100, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, mode_color, 2)

    # 조향각 텍스트
    angle_deg = steering_angle * 45  # -1~1 → -45°~45°
    steer_text = f"Steering: {steering_angle:+.3f} ({angle_deg:+.1f} deg)"
    cv2.putText(vis, steer_text, (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # 조향 바 (하단)
    bar_center_x, bar_y = w // 2, h - 60
    bar_w, bar_h = 300, 16
    # 배경
    cv2.rectangle(vis, (bar_center_x - bar_w // 2, bar_y),
                  (bar_center_x + bar_w // 2, bar_y + bar_h), (60, 60, 60), -1)
    # 중앙선
    cv2.line(vis, (bar_center_x, bar_y - 5),
             (bar_center_x, bar_y + bar_h + 5), (255, 255, 255), 1)
    # 조향 indicator
    indicator_x = int(bar_center_x + steering_angle * (bar_w // 2))
    color = (0, 255, 0) if abs(steering_angle) < 0.1 else \
            (0, 255, 255) if abs(steering_angle) < 0.4 else (0, 0, 255)
    cv2.circle(vis, (indicator_x, bar_y + bar_h // 2), 10, color, -1)
    cv2.putText(vis, "L", (bar_center_x - bar_w // 2 - 25, bar_y + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(vis, "R", (bar_center_x + bar_w // 2 + 10, bar_y + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # 속도 게이지 (프레임 단순 표시)
    cv2.putText(vis, f"Frame: {getattr(draw_lane_and_steering, 'frame_count', 0)}",
                (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

    return vis


# ===================== 데이터셋 로드 (Ground Truth) =====================

def load_ground_truth():
    """prepare_data.py 로 생성된 metadata에서 Ground Truth 조향각 로드"""
    with open(os.path.join(DATA_DIR, "metadata.json")) as f:
        meta = json.load(f)

    steering_map = {}  # 파일명 → 조향각
    for item in meta["data"]:
        steering_map[item["file"]] = item["steering"]
    return steering_map, meta["fps"]


# ===================== 자율주행 루프 =====================

class SelfDrivingSimulator:
    def __init__(self, model_path, video_path):
        self.model = tf.keras.models.load_model(model_path)
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_step = 3

        # Ground Truth 데이터
        self.gt_map, _ = load_ground_truth()

        # 통계
        self.frame_count = 0
        self.gt_angles = []
        self.pred_angles = []
        self.start_time = time.time()

        print(f"모델 로드 완료: {model_path}")
        print(f"영상: {self.total_frames} 프레임, {self.fps:.1f} FPS")

    def predict_steering(self, frame):
        """한 프레임으로 조향각 예측"""
        small = cv2.resize(frame, (IMG_WIDTH, IMG_HEIGHT))
        small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        x = np.expand_dims(small_rgb, axis=0).astype(np.float32) / 127.5 - 1.0
        pred = self.model.predict(x, verbose=0)[0, 0]
        return float(np.clip(pred, -1.0, 1.0))

    def get_gt_steering(self, saved_idx):
        """저장된 데이터셋 인덱스로 Ground Truth 조향각 반환"""
        filename = f"frame_{saved_idx:04d}.npy"
        return self.gt_map.get(filename, 0.0)

    def run(self):
        print("\n=== Self-Driving Simulator ===")
        print("  SPACE: 일시정지/재개")
        print("  ESC: 종료\n")

        pause = False
        frame_idx = 0
        saved_idx = 0  # GT 대응 인덱스

        cv2.namedWindow("Self-Driving Simulator", cv2.WINDOW_NORMAL)

        while True:
            if not pause:
                ret, frame = self.cap.read()
                if not ret:
                    print("\n영상 끝 - 처음으로 돌아갑니다.")
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_idx = 0
                    saved_idx = 0
                    continue

                if frame_idx % self.frame_step == 0:
                    # AI 예측
                    pred_angle = self.predict_steering(frame)

                    # Ground Truth (같은 조건에서만 비교)
                    gt_angle = self.get_gt_steering(saved_idx)

                    self.gt_angles.append(gt_angle)
                    self.pred_angles.append(pred_angle)
                    saved_idx += 1

                    # 시각화
                    vis = draw_lane_and_steering(frame, pred_angle, is_autonomous=True)
                    draw_lane_and_steering.frame_count = frame_idx

                    # 실제/예측 비교 텍스트
                    h, w = vis.shape[:2]
                    cv2.putText(vis, f"GT Steering: {gt_angle:+.3f}",
                                (w - 280, 70), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (200, 200, 100), 2)

                    # 미니 차트 (우측 상단)
                    chart_x, chart_y = w - 260, 100
                    chart_w, chart_h = 240, 100
                    cv2.rectangle(vis, (chart_x, chart_y),
                                  (chart_x + chart_w, chart_y + chart_h),
                                  (30, 30, 30), -1)

                    if len(self.gt_angles) > 1:
                        recent = min(100, len(self.gt_angles))
                        gt_recent = self.gt_angles[-recent:]
                        pred_recent = self.pred_angles[-recent:]
                        for i in range(1, recent):
                            x1 = chart_x + int((i - 1) / recent * chart_w)
                            x2 = chart_x + int(i / recent * chart_w)
                            # GT (노랑)
                            y1_gt = chart_y + chart_h // 2 - int(gt_recent[i - 1] * chart_h // 2)
                            y2_gt = chart_y + chart_h // 2 - int(gt_recent[i] * chart_h // 2)
                            cv2.line(vis, (x1, y1_gt), (x2, y2_gt), (0, 255, 255), 1)
                            # Pred (초록)
                            y1_pr = chart_y + chart_h // 2 - int(pred_recent[i - 1] * chart_h // 2)
                            y2_pr = chart_y + chart_h // 2 - int(pred_recent[i] * chart_h // 2)
                            cv2.line(vis, (x1, y1_pr), (x2, y2_pr), (0, 255, 0), 1)

                    cv2.putText(vis, "--- GT vs Pred (recent 100) ---",
                                (chart_x, chart_y - 5), cv2.FONT_HERSHEY_SIMPLEX,
                                0.4, (150, 150, 150), 1)

                    # 리사이즈 후 표시
                    display = cv2.resize(vis, (1280, 720))
                    cv2.imshow("Self-Driving Simulator", display)

                frame_idx += 1

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == 32:  # SPACE
                pause = not pause
                status = "PAUSED" if pause else "RUNNING"
                print(f"  [{status}]")

        self.finish()

    def finish(self):
        self.cap.release()
        cv2.destroyAllWindows()

        # 최종 통계
        total_time = time.time() - self.start_time
        print("\n" + "=" * 50)
        print("시뮬레이션 종료")
        print(f"  실행 시간: {total_time:.1f}s")
        print(f"  예측 프레임: {len(self.pred_angles)}")

        if self.gt_angles and self.pred_angles:
            gt_arr = np.array(self.gt_angles[:len(self.pred_angles)])
            pred_arr = np.array(self.pred_angles)
            mae = np.mean(np.abs(gt_arr - pred_arr))
            mse = np.mean((gt_arr - pred_arr) ** 2)
            print(f"  GT vs Pred MAE: {mae:.4f}")
            print(f"  GT vs Pred MSE: {mse:.6f}")

        # 저장
        save_img = os.path.join(r"C:\Users\Administrator\Desktop\Self-Driving", "simulator_result.png")
        print(f"  결과 저장 완료")


# ===================== 메인 =====================

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"[!] 모델 파일이 없습니다: {MODEL_PATH}")
        print("    먼저 prepare_data.py → train_model.py 를 순서대로 실행하세요.")
        return

    sim = SelfDrivingSimulator(MODEL_PATH, VIDEO_PATH)
    sim.run()


if __name__ == "__main__":
    main()
