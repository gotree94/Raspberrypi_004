#!/bin/bash
set -e

CONFIG="/boot/firmware/config.txt"
[ ! -f "$CONFIG" ] && CONFIG="/boot/config.txt"

echo "=== Raspberry Pi Camera 2.1 (IMX219) Setup ==="
echo "Config file: $CONFIG"
echo ""

sudo apt update && sudo apt upgrade -y
sudo apt install -y rpicam-apps libcamera-dev python3-picamera2

# Remove OV5647 overlay
sudo sed -i 's/^dtoverlay=ov5647/#dtoverlay=ov5647/' "$CONFIG" 2>/dev/null || true

# Enable auto-detect
if grep -q "#camera_auto_detect=1" "$CONFIG"; then
    sudo sed -i 's/#camera_auto_detect=1/camera_auto_detect=1/' "$CONFIG"
    echo "[OK] Enabled camera_auto_detect"
elif grep -q "camera_auto_detect=1" "$CONFIG"; then
    echo "[OK] camera_auto_detect already set"
else
    echo "camera_auto_detect=1" | sudo tee -a "$CONFIG"
    echo "[OK] Added camera_auto_detect=1"
fi

# GPU memory
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
echo "After reboot: python3 test_camera_v21.py"
