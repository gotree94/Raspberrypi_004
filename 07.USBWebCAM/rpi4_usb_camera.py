#!/usr/bin/env python3
"""
usb_camera.py
Raspberry Pi 3B+ / 4B | Debian 13 Trixie
USB 카메라 영상을 OpenCV로 화면에 표시

설치:
    pip install opencv-python --break-system-packages
    또는
    sudo apt install python3-opencv

실행:
    python3 usb_camera.py
    python3 usb_camera.py --device 0        # 카메라 장치 번호
    python3 usb_camera.py --width 1280 --height 720
    python3 usb_camera.py --fps 30
    python3 usb_camera.py --save             # 영상 저장 모드
"""

import cv2
import argparse
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(description="USB 카메라 뷰어 (OpenCV)")
    parser.add_argument("--device", type=int, default=0,
                        help="카메라 장치 번호 (기본값: 0 = /dev/video0)")
    parser.add_argument("--width",  type=int, default=640,
                        help="해상도 가로 (기본값: 640)")
    parser.add_argument("--height", type=int, default=480,
                        help="해상도 세로 (기본값: 480)")
    parser.add_argument("--fps",    type=int, default=30,
                        help="프레임 레이트 (기본값: 30)")
    parser.add_argument("--save",   action="store_true",
                        help="영상을 파일로 저장")
    parser.add_argument("--output", type=str, default="output.avi",
                        help="저장 파일명 (기본값: output.avi)")
    return parser.parse_args()


def open_camera(device: int, width: int, height: int, fps: int) -> cv2.VideoCapture:
    """카메라 열기 및 설정"""
    cap = cv2.VideoCapture(device)

    if not cap.isOpened():
        print(f"[오류] /dev/video{device} 를 열 수 없습니다.")
        print("  - 카메라 연결 확인: ls /dev/video*")
        print("  - 다른 장치 번호 시도: --device 1")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS,          fps)

    # 실제 적용된 값 출력 (카메라가 지원하지 않는 해상도는 자동 조정됨)
    actual_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[카메라] /dev/video{device} 오픈 성공")
    print(f"  해상도: {actual_w} x {actual_h}")
    print(f"  FPS   : {actual_fps:.1f}")

    return cap


def create_writer(filename: str, fps: float, width: int, height: int) -> cv2.VideoWriter:
    """영상 저장용 VideoWriter 생성"""
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    if not writer.isOpened():
        print(f"[경고] 저장 파일을 열 수 없습니다: {filename}")
        return None
    print(f"[저장] {filename} 으로 녹화 시작")
    return writer


def draw_overlay(frame, fps: float, frame_count: int, recording: bool):
    """화면에 정보 오버레이 표시"""
    h, w = frame.shape[:2]

    # FPS 표시
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # 해상도 표시
    cv2.putText(frame, f"{w}x{h}",
                (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

    # 프레임 카운터
    cv2.putText(frame, f"Frame: {frame_count}",
                (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # 녹화 중 표시
    if recording:
        cv2.circle(frame, (w - 20, 20), 8, (0, 0, 255), -1)
        cv2.putText(frame, "REC",
                    (w - 55, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # 키 안내
    guide = "q:종료  s:스냅샷  r:녹화토글  g:그레이스케일"
    cv2.putText(frame, guide,
                (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)


def main():
    args = parse_args()

    print("=" * 45)
    print("  USB 카메라 뷰어 (OpenCV)")
    print("=" * 45)
    print(f"  OpenCV 버전: {cv2.__version__}")

    cap    = open_camera(args.device, args.width, args.height, args.fps)
    writer = None
    recording = args.save

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS) or args.fps

    if recording:
        writer = create_writer(args.output, actual_fps, actual_w, actual_h)

    print("\n[키 조작]")
    print("  q          : 종료")
    print("  s          : 스냅샷 저장 (snapshot_N.jpg)")
    print("  r          : 녹화 시작/중지")
    print("  g          : 그레이스케일 토글")
    print("  f          : 좌우 반전 토글")
    print("-" * 45)

    frame_count  = 0
    snapshot_num = 0
    grayscale    = False
    flip         = False
    fps_display  = 0.0
    t_prev       = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[오류] 프레임을 읽을 수 없습니다.")
            break

        frame_count += 1

        # FPS 계산 (30프레임마다 갱신)
        if frame_count % 30 == 0:
            t_now       = time.time()
            fps_display = 30.0 / (t_now - t_prev)
            t_prev      = t_now

        # 효과 적용
        if flip:
            frame = cv2.flip(frame, 1)

        if grayscale:
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(gray,  cv2.COLOR_GRAY2BGR)

        # 오버레이 표시
        draw_overlay(frame, fps_display, frame_count, recording)

        # 녹화
        if recording and writer:
            writer.write(frame)

        # 화면 출력
        cv2.imshow("USB Camera - RPi", frame)

        # 키 입력 처리 (1ms 대기)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("[종료] 사용자 요청")
            break

        elif key == ord("s"):
            filename = f"snapshot_{snapshot_num:04d}.jpg"
            cv2.imwrite(filename, frame)
            print(f"[스냅샷] 저장: {filename}")
            snapshot_num += 1

        elif key == ord("r"):
            recording = not recording
            if recording:
                fname  = f"rec_{int(time.time())}.avi"
                writer = create_writer(fname, actual_fps, actual_w, actual_h)
            else:
                if writer:
                    writer.release()
                    writer = None
                print("[녹화] 중지")

        elif key == ord("g"):
            grayscale = not grayscale
            print(f"[그레이스케일] {'ON' if grayscale else 'OFF'}")

        elif key == ord("f"):
            flip = not flip
            print(f"[좌우반전] {'ON' if flip else 'OFF'}")

    # 정리
    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print("[완료]")


if __name__ == "__main__":
    main()
