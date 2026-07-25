#!/bin/bash
echo "=== Camera 2.1 (IMX219) Quick Test ==="
rpicam-hello --list-cameras 2>/dev/null || libcamera-hello --list-cameras 2>/dev/null
echo ""
rpicam-still -t 5000 -o test_v21.jpg 2>/dev/null || libcamera-still -t 5000 -o test_v21.jpg 2>/dev/null
[ -f test_v21.jpg ] && echo "[OK] test_v21.jpg" || echo "[FAIL] photo"
rpicam-vid -t 3000 -o test_v21.h264 2>/dev/null || libcamera-vid -t 3000 -o test_v21.h264 2>/dev/null
[ -f test_v21.h264 ] && echo "[OK] test_v21.h264" || echo "[FAIL] video"
