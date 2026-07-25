#!/bin/bash
set -e

CONFIG="/boot/firmware/config.txt"
[ ! -f "$CONFIG" ] && CONFIG="/boot/config.txt"

echo "=== Raspberry Pi Camera 1.3 (OV5647) Setup ==="
echo "Config file: $CONFIG"
echo ""

sudo apt update && sudo apt upgrade -y
sudo apt install -y rpicam-apps libcamera-dev python3-picamera2

# Disable auto-detect
if grep -q "camera_auto_detect=1" "$CONFIG"; then
    sudo sed -i 's/camera_auto_detect=1/#camera_auto_detect=1/' "$CONFIG"
    echo "[OK] Disabled camera_auto_detect"
fi

# Add OV5647 overlay
if grep -q "dtoverlay=ov5647" "$CONFIG"; then
    echo "[OK] dtoverlay=ov5647 already set"
else
    echo "dtoverlay=ov5647" | sudo tee -a "$CONFIG"
    echo "[OK] Added dtoverlay=ov5647"
fi

# Remove other camera overlays if present
sudo sed -i 's/^dtoverlay=imx219/#dtoverlay=imx219/' "$CONFIG" 2>/dev/null || true

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
echo "After reboot: python3 test_camera_v13.py"
