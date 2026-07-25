#!/usr/bin/env python3
import sys
import time
import os

def check_cameras_cli():
    print("=" * 50)
    print("1. Detecting cameras via rpicam-hello --list-cameras")
    print("=" * 50)
    ret = os.system("rpicam-hello --list-cameras")
    if ret != 0:
        print("rpicam-hello not available, trying libcamera-hello...")
        ret = os.system("libcamera-hello --list-cameras")
    if ret != 0:
        print("[FAIL] No camera tools found or no cameras detected.")
        return False
    return True

def check_picamera2():
    print("\n" + "=" * 50)
    print("2. Detecting cameras via Picamera2")
    print("=" * 50)
    try:
        from picamera2 import Picamera2
    except ImportError:
        print("[SKIP] picamera2 not installed. Install with:")
        print("       sudo apt install python3-picamera2")
        return False

    cameras = Picamera2.global_camera_info()
    if not cameras:
        print("[FAIL] No cameras found via Picamera2.")
        return False

    print(f"[OK] Found {len(cameras)} camera(s):")
    for i, cam in enumerate(cameras):
        print(f"  Camera {i}: {cam}")
    return True

def take_test_photos():
    print("\n" + "=" * 50)
    print("3. Taking test photos from each camera")
    print("=" * 50)
    try:
        from picamera2 import Picamera2
    except ImportError:
        print("[SKIP] picamera2 not installed.")
        return

    cameras = Picamera2.global_camera_info()
    if not cameras:
        print("[FAIL] No cameras available.")
        return

    for i, cam_info in enumerate(cameras):
        print(f"\n--- Camera {i} ---")
        try:
            picam = Picamera2(camera_num=i)
            config = picam.create_still_configuration()
            picam.configure(config)
            picam.start()
            time.sleep(2)

            filename = f"test_camera_{i}.jpg"
            picam.capture_file(filename)
            picam.stop()
            picam.close()
            print(f"[OK] Photo saved: {filename}")
        except Exception as e:
            print(f"[ERROR] Camera {i}: {e}")

def take_test_video():
    print("\n" + "=" * 50)
    print("4. Taking 3-second test video from camera 0")
    print("=" * 50)
    try:
        from picamera2 import Picamera2
    except ImportError:
        print("[SKIP] picamera2 not installed.")
        return

    try:
        from picamera2.encoders import H264Encoder
        picam = Picamera2(camera_num=0)
        video_config = picam.create_video_configuration(
            main={"size": (1280, 720)}
        )
        picam.configure(video_config)

        encoder = H264Encoder(10000000)
        output = "test_video.h264"
        picam.start_recording(encoder, output)
        time.sleep(3)
        picam.stop_recording()
        picam.stop()
        picam.close()
        print(f"[OK] Video saved: {output}")
    except Exception as e:
        print(f"[ERROR] Video capture failed: {e}")

if __name__ == "__main__":
    print("Raspberry Pi Camera Test Script")
    print("Pi 4 + Camera 1.3 / 2.1\n")

    check_cameras_cli()
    check_picamera2()
    take_test_photos()
    take_test_video()

    print("\n" + "=" * 50)
    print("All tests complete.")
    print("=" * 50)
