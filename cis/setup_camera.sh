#!/bin/bash
set -e

CONFIG="/boot/firmware/config.txt"
[ ! -f "$CONFIG" ] && CONFIG="/boot/config.txt"

echo "=== Updating system ==="
sudo apt update && sudo apt upgrade -y

echo "=== Installing rpicam-apps and dependencies ==="
sudo apt install -y rpicam-apps libcamera-dev python3-picamera2

echo ""
echo "=== Configuring config.txt for Camera 1.3 (OV5647) ==="
echo "Config file: $CONFIG"

# Disable auto-detect, add manual overlay for OV5647
if grep -q "camera_auto_detect=1" "$CONFIG"; then
    sudo sed -i 's/camera_auto_detect=1/#camera_auto_detect=1/' "$CONFIG"
    echo "[OK] Disabled camera_auto_detect"
fi

if grep -q "dtoverlay=ov5647" "$CONFIG"; then
    echo "[OK] dtoverlay=ov5647 already set"
else
    echo "dtoverlay=ov5647" | sudo tee -a "$CONFIG"
    echo "[OK] Added dtoverlay=ov5647"
fi

# Ensure sufficient GPU memory
if ! grep -q "gpu_mem" "$CONFIG"; then
    echo "gpu_mem=128" | sudo tee -a "$CONFIG"
    echo "[OK] Added gpu_mem=128"
fi

echo ""
echo "=== Detecting cameras ==="
rpicam-hello --list-cameras 2>/dev/null || libcamera-hello --list-cameras 2>/dev/null

echo ""
echo "=== Setup complete ==="
echo "*** REBOOT REQUIRED: sudo reboot ***"
echo ""
echo "After reboot:"
echo "  List cameras:   rpicam-hello --list-cameras"
echo "  Test preview:   rpicam-hello"
echo "  Take a photo:   rpicam-still -o test.jpg"
echo "  Record video:   rpicam-vid -o test.h264 -t 5000"
