#!/bin/bash
echo "=== Camera 1.3 (OV5647) Quick Test ==="
rpicam-hello --list-cameras 2>/dev/null || libcamera-hello --list-cameras 2>/dev/null
echo ""
rpicam-still -t 5000 -o test_v13.jpg 2>/dev/null || libcamera-still -t 5000 -o test_v13.jpg 2>/dev/null
[ -f test_v13.jpg ] && echo "[OK] test_v13.jpg" || echo "[FAIL] photo"
rpicam-vid -t 3000 -o test_v13.h264 2>/dev/null || libcamera-vid -t 3000 -o test_v13.h264 2>/dev/null
[ -f test_v13.h264 ] && echo "[OK] test_v13.h264" || echo "[FAIL] video"
