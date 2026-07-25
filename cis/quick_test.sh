#!/bin/bash

echo "=== Camera Detection ==="
rpicam-hello --list-cameras 2>/dev/null || libcamera-hello --list-cameras 2>/dev/null
echo ""

echo "=== Test Photo (5 sec preview then capture) ==="
rpicam-still -t 5000 -o test_photo.jpg 2>/dev/null || \
libcamera-still -t 5000 -o test_photo.jpg 2>/dev/null

if [ -f test_photo.jpg ]; then
    echo "[OK] Saved test_photo.jpg"
else
    echo "[FAIL] No photo captured"
fi

echo ""
echo "=== Test Video (3 seconds) ==="
rpicam-vid -t 3000 -o test_video.h264 2>/dev/null || \
libcamera-vid -t 3000 -o test_video.h264 2>/dev/null

if [ -f test_video.h264 ]; then
    echo "[OK] Saved test_video.h264"
else
    echo "[FAIL] No video captured"
fi
