#!/usr/bin/env python3
import sys
import time
import os

os.environ["LIBCAMERA_RPI_CONFIG_FILE"] = (
    "/usr/share/libcamera/pipeline/rpi/vc4/rpi_apps.yaml"
)

TIMEOUT_YAML = "/usr/share/libcamera/pipeline/rpi/vc4/rpi_apps.yaml"
CUSTOM_YAML = "/tmp/rpi_apps_timeout.yaml"


def ensure_timeout_config():
    import shutil
    if not os.path.exists(TIMEOUT_YAML):
        return
    shutil.copy2(TIMEOUT_YAML, CUSTOM_YAML)
    with open(CUSTOM_YAML, "r") as f:
        content = f.read()
    if "camera_timeout_value_ms" in content:
        content = content.replace(
            '"camera_timeout_value_ms":',
            '"camera_timeout_value_ms":'
        )
        import re
        content = re.sub(
            r'"camera_timeout_value_ms"\s*:\s*\d+',
            '"camera_timeout_value_ms": 10000',
            content
        )
    else:
        content = content.replace(
            "}",
            '    "camera_timeout_value_ms": 10000,\n}',
            1
        )
    with open(CUSTOM_YAML, "w") as f:
        f.write(content)
    os.environ["LIBCAMERA_RPI_CONFIG_FILE"] = CUSTOM_YAML
    print(f"[INFO] Timeout config set to 10s: {CUSTOM_YAML}")


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
        for attempt in range(3):
            try:
                picam = Picamera2(camera_num=i)
                config = picam.create_still_configuration()
                picam.configure(config)
                picam.start()
                time.sleep(3)

                filename = f"test_camera_{i}.jpg"
                picam.capture_file(filename)
                picam.stop()
                picam.close()
                print(f"[OK] Photo saved: {filename}")
                break
            except Exception as e:
                print(f"[WARN] Attempt {attempt+1}/3 failed: {e}")
                try:
                    picam.stop()
                    picam.close()
                except Exception:
                    pass
                if attempt < 2:
                    print("  Retrying in 2s...")
                    time.sleep(2)
                else:
                    print(f"[FAIL] Camera {i} photo capture failed after 3 attempts.")


def take_test_video():
    print("\n" + "=" * 50)
    print("4. Taking 3-second test video from camera 0")
    print("=" * 50)
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder
    except ImportError:
        print("[SKIP] picamera2 not installed.")
        return

    for attempt in range(3):
        try:
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
            return
        except Exception as e:
            print(f"[WARN] Attempt {attempt+1}/3 failed: {e}")
            try:
                picam.stop()
                picam.close()
            except Exception:
                pass
            if attempt < 2:
                print("  Retrying in 2s...")
                time.sleep(2)
            else:
                print("[FAIL] Video capture failed after 3 attempts.")


if __name__ == "__main__":
    print("Raspberry Pi Camera Test Script")
    print("Pi 4 + Camera 1.3 / 2.1\n")

    ensure_timeout_config()
    check_cameras_cli()
    check_picamera2()
    take_test_photos()
    take_test_video()

    print("\n" + "=" * 50)
    print("All tests complete.")
    print("=" * 50)
