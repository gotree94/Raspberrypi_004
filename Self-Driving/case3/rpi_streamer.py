"""
rpi_streamer.py — Raspberry Pi side
  - USB camera capture → MJPEG TCP stream
  - TCP command server → WASDX / continuous steering
  - Motor control via GPIO (PWM)
  - Threaded architecture

Usage:
  python rpi_streamer.py [--cam 0] [--video-port 8000] [--cmd-port 8001]

Protocol:
  Video:  4-byte payload length (uint32) + JPEG bytes (repeated)
  Command: "CMD:W\n" | "CMD:A\n" | "CMD:S\n" | "CMD:D\n" | "CMD:X\n"
           "STEER:left_speed,right_speed\n"  (continuous, -1.0~+1.0)
"""

import socket
import threading
import struct
import time
import sys
import argparse
from collections import deque

try:
    import cv2
except ImportError:
    cv2 = None
    print("[WARN] OpenCV not found. Install: pip install opencv-python")

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("[WARN] RPi.GPIO not found. Running in simulation mode.")


# ─── Motor Control ────────────────────────────────────────────
class MotorController:
    def __init__(self, ena=18, in1=23, in2=24, in3=25, in4=12, enb=13):
        self.ena = ena; self.in1 = in1; self.in2 = in2
        self.in3 = in3; self.in4 = in4; self.enb = enb
        self.left_speed = 0.0
        self.right_speed = 0.0
        if GPIO is not None:
            GPIO.setmode(GPIO.BCM)
            for pin in [ena, in1, in2, in3, in4, enb]:
                GPIO.setup(pin, GPIO.OUT)
            self.pwm_a = GPIO.PWM(ena, 1000)
            self.pwm_b = GPIO.PWM(enb, 1000)
            self.pwm_a.start(0)
            self.pwm_b.start(0)
        self._lock = threading.Lock()

    def set_speeds(self, left, right):
        left = max(-1.0, min(1.0, left))
        right = max(-1.0, min(1.0, right))
        with self._lock:
            self.left_speed = left
            self.right_speed = right
        self._apply()

    def _apply(self):
        with self._lock:
            l, r = self.left_speed, self.right_speed
        if GPIO is None:
            return
        # Left motor
        if l >= 0:
            GPIO.output(self.in1, GPIO.HIGH)
            GPIO.output(self.in2, GPIO.LOW)
        else:
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.HIGH)
        self.pwm_a.ChangeDutyCycle(abs(l) * 100)
        # Right motor
        if r >= 0:
            GPIO.output(self.in3, GPIO.HIGH)
            GPIO.output(self.in4, GPIO.LOW)
        else:
            GPIO.output(self.in3, GPIO.LOW)
            GPIO.output(self.in4, GPIO.HIGH)
        self.pwm_b.ChangeDutyCycle(abs(r) * 100)

    def stop(self):
        self.set_speeds(0, 0)

    def cleanup(self):
        if GPIO is not None:
            self.stop()
            self.pwm_a.stop()
            self.pwm_b.stop()
            GPIO.cleanup()


# ─── Command Handler ──────────────────────────────────────────
class CommandHandler:
    def __init__(self, motor, default_speed=0.5):
        self.motor = motor
        self.default_speed = default_speed

    def handle(self, cmd):
        cmd = cmd.strip()
        if cmd.startswith("CMD:"):
            key = cmd[4]
            if key == "W":
                self.motor.set_speeds(self.default_speed, self.default_speed)
            elif key == "S":
                self.motor.set_speeds(-self.default_speed, -self.default_speed)
            elif key == "A":
                self.motor.set_speeds(-self.default_speed, self.default_speed)
            elif key == "D":
                self.motor.set_speeds(self.default_speed, -self.default_speed)
            elif key == "X":
                self.motor.stop()
        elif cmd.startswith("STEER:"):
            try:
                parts = cmd[6:].split(",")
                l, r = float(parts[0]), float(parts[1])
                self.motor.set_speeds(l, r)
            except (IndexError, ValueError):
                pass


# ─── Video Stream Server ──────────────────────────────────────
class VideoStreamer:
    def __init__(self, camera_id=0, port=8000, width=320, height=240, fps=20):
        self.port = port
        self.width = width
        self.height = height
        self.fps = fps
        self._running = False
        self._clients = []
        self._frame_queue = deque(maxlen=1)
        self._cap = None
        self._cam_id = camera_id

    def start(self):
        self._running = True
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()
        s = threading.Thread(target=self._server_loop, daemon=True)
        s.start()

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
        for c in self._clients:
            try: c.close()
            except: pass

    def _capture_loop(self):
        if cv2 is None:
            return
        cap = cv2.VideoCapture(self._cam_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap = cap
        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue
            ret, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret:
                self._frame_queue.append(jpg.tobytes())
            time.sleep(1.0 / self.fps)

    def _server_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(5)
        srv.settimeout(1.0)
        print(f"[Video] Streaming on port {self.port}")
        while self._running:
            try:
                conn, addr = srv.accept()
                print(f"[Video] Client connected: {addr}")
                self._clients.append(conn)
                t = threading.Thread(target=self._client_loop, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
        srv.close()

    def _client_loop(self, conn):
        while self._running:
            try:
                data = self._frame_queue[-1] if self._frame_queue else None
                if data:
                    conn.sendall(struct.pack("!I", len(data)) + data)
                else:
                    time.sleep(0.01)
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
        try: conn.close()
        except: pass
        if conn in self._clients:
            self._clients.remove(conn)


# ─── Command Server ───────────────────────────────────────────
class CommandServer:
    def __init__(self, handler, port=8001):
        self.port = port
        self.handler = handler
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(2)
        srv.settimeout(1.0)
        print(f"[Command] Server on port {self.port}")
        while self._running:
            try:
                conn, addr = srv.accept()
                print(f"[Command] Client connected: {addr}")
                with conn:
                    buf = b""
                    while self._running:
                        try:
                            c = conn.recv(1024)
                            if not c:
                                break
                            buf += c
                            while b"\n" in buf:
                                line, buf = buf.split(b"\n", 1)
                                cmd = line.decode().strip()
                                if cmd:
                                    self.handler.handle(cmd)
                        except socket.timeout:
                            continue
            except socket.timeout:
                continue
        srv.close()


# ─── Main ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cam", type=int, default=0, help="Camera device ID")
    parser.add_argument("--video-port", type=int, default=8000)
    parser.add_argument("--cmd-port", type=int, default=8001)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--speed", type=float, default=0.5, help="Default motor speed")
    args = parser.parse_args()

    print("=" * 50)
    print("RPi Streamer — Self-Driving Data Collection Node")
    print("=" * 50)

    motor = MotorController()
    handler = CommandHandler(motor, default_speed=args.speed)

    streamer = VideoStreamer(args.cam, args.video_port, args.width, args.height, args.fps)
    cmd_server = CommandServer(handler, args.cmd_port)

    try:
        streamer.start()
        cmd_server.start()
        print("\nSystem ready. Connect PC controller now.")
        print(f"  Video: tcp://<rpi_ip>:{args.video_port}")
        print(f"  Cmd:   tcp://<rpi_ip>:{args.cmd_port}")
        print("  Press Ctrl+C to stop.\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        streamer.stop()
        cmd_server.stop()
        motor.cleanup()
        print("Done.")


if __name__ == "__main__":
    main()
