#!/bin/bash
set -e

echo "=== Updating system ==="
sudo apt update && sudo apt upgrade -y

echo "=== Installing rpicam-apps and dependencies ==="
sudo apt install -y rpicam-apps libcamera-dev python3-picamera2

echo "=== Checking camera detect ==="
if ! rpicam-hello --list-cameras 2>/dev/null; then
    echo "WARNING: rpicam-hello not found, trying libcamera-hello..."
    libcamera-hello --list-cameras 2>/dev/null || echo "No cameras detected yet."
fi

echo "=== Checking config.txt for camera ==="
CONFIG="/boot/firmware/config.txt"
[ ! -f "$CONFIG" ] && CONFIG="/boot/config.txt"

if grep -q "camera_auto_detect" "$CONFIG"; then
    echo "camera_auto_detect already set in $CONFIG"
else
    echo "camera_auto_detect=1" | sudo tee -a "$CONFIG"
    echo "Added camera_auto_detect=1 to $CONFIG"
    echo "A reboot may be required."
fi

echo ""
echo "=== Setup complete ==="
echo "List cameras:   rpicam-hello --list-cameras"
echo "Test preview:   rpicam-hello"
echo "Take a photo:   rpicam-still -o test.jpg"
echo "Record video:   rpicam-vid -o test.h264 -t 5000"
