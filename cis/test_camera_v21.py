#!/usr/bin/env python3
import time
import os

def main():
    print("=" * 50)
    print("  Camera 2.1 (IMX219) Test Script")
    print("  Pi 4 + IMX219 8MP")
    print("=" * 50)

    print("\n[1] Camera detection (CLI)")
    print("-" * 50)
    ret = os.system("rpicam-hello --list-cameras")
    if ret != 0:
        ret = os.system("libcamera-hello --list-cameras")
    if ret != 0:
        print("[FAIL] No cameras detected.")
        return

    print("\n[2] Camera detection (Picamera2)")
    print("-" * 50)
    try:
        from picamera2 import Picamera2
    except ImportError:
        print("[SKIP] sudo apt install python3-picamera2")
        return

    cameras = Picamera2.global_camera_info()
    if not cameras:
        print("[FAIL] No cameras found.")
        return
    print(f"[OK] {len(cameras)} camera(s):")
    for i, cam in enumerate(cameras):
        print(f"  Camera {i}: {cam}")

    print("\n[3] Test photo")
    print("-" * 50)
    picam = None
    try:
        picam = Picamera2(camera_num=0)
        config = picam.create_still_configuration(
            main={"size": (3280, 2464)}
        )
        picam.configure(config)
        picam.start()
        time.sleep(2)

        picam.capture_file("test_v21.jpg")
        picam.stop()
        picam.close()
        print("[OK] Saved test_v21.jpg")
    except Exception as e:
        print(f"[FAIL] {e}")
        if picam:
            try: picam.stop()
            except: pass
            try: picam.close()
            except: pass

    print("\n[4] Test video (3 sec)")
    print("-" * 50)
    picam = None
    try:
        from picamera2.encoders import H264Encoder
        picam = Picamera2(camera_num=0)
        video_config = picam.create_video_configuration(
            main={"size": (1280, 720)}
        )
        picam.configure(video_config)

        encoder = H264Encoder(10000000)
        picam.start_recording(encoder, "test_v21.h264")
        time.sleep(3)
        picam.stop_recording()
        picam.stop()
        picam.close()
        print("[OK] Saved test_v21.h264")
    except Exception as e:
        print(f"[FAIL] {e}")
        if picam:
            try: picam.stop()
            except: pass
            try: picam.close()
            except: pass

    print("\n" + "=" * 50)
    print("  All tests complete.")
    print("=" * 50)

if __name__ == "__main__":
    main()
