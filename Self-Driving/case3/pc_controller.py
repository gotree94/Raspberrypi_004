"""
pc_controller.py — PC side
  - Receive video stream from RPi → display with HUD
  - Read STM32 encoder via Serial → continuous steering
  - Keyboard WASDX fallback for speed/steering
  - Send commands to RPi via TCP
  - Record synchronized frame + steering to disk
  - Output: frame_XXXXXX.npy (160x80) + metadata.json

Usage:
  python pc_controller.py --rpi 192.168.1.100 [--com COM3] [--record]

Controls:
  W = forward      A = left (kb fallback)    SPACE = toggle record
  S = backward      D = right (kb fallback)   ESC  = quit
  X = stop          +/- = adjust speed
"""

import socket
import struct
import threading
import time
import json
import os
import sys
import argparse
import math
from pathlib import Path
from collections import deque

try:
    import cv2
    import numpy as np
except ImportError:
    print("ERROR: OpenCV + NumPy required.  pip install opencv-python numpy")
    sys.exit(1)


# ─── Video Receiver ───────────────────────────────────────────
class VideoReceiver:
    def __init__(self, host, port=8000):
        self.host = host
        self.port = port
        self._sock = None
        self._running = False
        self.latest_frame = None
        self._lock = threading.Lock()

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        if self._sock:
            try: self._sock.close()
            except: pass

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((self.host, self.port))
        s.settimeout(1.0)
        self._sock = s
        print(f"[Video] Connected to {self.host}:{self.port}")

    def get_frame(self):
        with self._lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def _loop(self):
        buf = b""
        while self._running:
            if self._sock is None:
                try:
                    self._connect()
                except Exception as e:
                    time.sleep(2)
                    continue
            try:
                data = self._sock.recv(65536)
                if not data:
                    self._sock = None
                    continue
                buf += data
                while len(buf) >= 4:
                    size = struct.unpack("!I", buf[:4])[0]
                    if len(buf) < 4 + size:
                        break
                    jpg = buf[4:4 + size]
                    buf = buf[4 + size:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8),
                                         cv2.IMREAD_COLOR)
                    if frame is not None:
                        with self._lock:
                            self.latest_frame = frame
            except socket.timeout:
                continue
            except (ConnectionRefusedError, BrokenPipeError, OSError) as e:
                print(f"[Video] Connection lost: {e}")
                self._sock = None
                time.sleep(2)


# ─── Command Sender ───────────────────────────────────────────
class CommandSender:
    def __init__(self, host, port=8001):
        self.host = host
        self.port = port
        self._sock = None
        self._running = False
        self._send_queue = deque()

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        if self._sock:
            try: self._sock.close()
            except: pass

    def send(self, cmd):
        self._send_queue.append(cmd)

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((self.host, self.port))
        s.settimeout(1.0)
        self._sock = s
        print(f"[Cmd] Connected to {self.host}:{self.port}")

    def _loop(self):
        while self._running:
            if self._sock is None:
                try:
                    self._connect()
                except Exception as e:
                    time.sleep(2)
                    continue
            try:
                if self._send_queue:
                    cmd = self._send_queue.popleft()
                    self._sock.sendall((cmd + "\n").encode())
                else:
                    time.sleep(0.01)
            except (BrokenPipeError, ConnectionResetError, OSError):
                self._sock = None
                time.sleep(2)


# ─── Serial Reader (STM32 Encoder) ────────────────────────────
class EncoderReader:
    def __init__(self, port=None, baud=115200):
        self.port = port
        self.baud = baud
        self._ser = None
        self._running = False
        self.value = 0.0  # -1.0 ~ +1.0
        self.connected = False

    def start(self):
        if not self.port:
            print("[Encoder] No serial port specified. Using keyboard only.")
            return
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        if self._ser:
            try: self._ser.close()
            except: pass

    def _loop(self):
        import serial
        while self._running:
            try:
                self._ser = serial.Serial(self.port, self.baud, timeout=0.1)
                self.connected = True
                print(f"[Encoder] Serial opened: {self.port} @ {self.baud}")
                while self._running:
                    line = self._ser.readline().strip()
                    if line:
                        try:
                            raw = int(line)
                            self.value = max(-1.0, min(1.0, raw / 1024.0))
                        except ValueError:
                            pass
            except serial.SerialException as e:
                self.connected = False
                print(f"[Encoder] Serial error: {e}. Retrying in 3s...")
                time.sleep(3)
            except Exception as e:
                print(f"[Encoder] Error: {e}")
                time.sleep(1)
            finally:
                if self._ser:
                    try: self._ser.close()
                    except: pass
                self._ser = None


# ─── Recorder ─────────────────────────────────────────────────
class Recorder:
    def __init__(self, out_dir="collected_data"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(exist_ok=True)
        self._recording = False
        self._frame_count = 0
        self._metadata = {}

    def toggle(self):
        self._recording = not self._recording
        if self._recording:
            self._frame_count = len(list(self.out_dir.glob("frame_*.npy")))
            self._metadata = {}
            print(f"[Record] STARTED → {self.out_dir} (starting #{self._frame_count})")
        else:
            self._save_metadata()
            print(f"[Record] STOPPED — {self._frame_count - len(self._metadata)} frames")
        return self._recording

    def record(self, frame, steering, timestamp):
        if not self._recording:
            return
        frame_small = cv2.resize(frame, (160, 80))
        path = self.out_dir / f"frame_{self._frame_count:06d}.npy"
        np.save(str(path), frame_small)
        self._metadata[self._frame_count] = {
            "steering": round(steering, 4),
            "timestamp": round(timestamp, 3)
        }
        self._frame_count += 1

    def _save_metadata(self):
        path = self.out_dir / "metadata.json"
        existing = {}
        if path.exists():
            with open(path) as f:
                existing = json.load(f)
        existing.update(self._metadata)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)

    def close(self):
        if self._recording:
            self._recording = False
            self._save_metadata()

    @property
    def is_recording(self):
        return self._recording


# ─── HUD Overlay ──────────────────────────────────────────────
def draw_hud(frame, steering, speed, encoder_val, recording, fps, cmd_str):
    h, w = frame.shape[:2]
    cy = h // 2
    cx = w // 2

    # Steering bar (bottom center)
    bar_w, bar_h = 200, 16
    bar_x = cx - bar_w // 2
    bar_y = h - 40
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
    steer_px = int((steering + 1) / 2 * bar_w)
    color = (0, 255, 0) if abs(steering) < 0.2 else (0, 255, 255) if abs(steering) < 0.5 else (0, 0, 255)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + steer_px, bar_y + bar_h), color, -1)
    cv2.putText(frame, f"S:{steering:+.2f}", (bar_x, bar_y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Status panel (top-left)
    lines = [
        f"FPS: {fps:.0f}",
        f"Speed: {speed:.2f}",
        f"Enc: {encoder_val:+.3f}",
        f"Cmd: {cmd_str}",
        f"REC: {'●' if recording else '○'}",
    ]
    for i, txt in enumerate(lines):
        cv2.putText(frame, txt, (10, 20 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 255) if i == 4 else (255, 255, 255), 1)

    return frame


# ─── Main PC Controller ───────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpi", required=True, help="Raspberry Pi IP address")
    parser.add_argument("--video-port", type=int, default=8000)
    parser.add_argument("--cmd-port", type=int, default=8001)
    parser.add_argument("--com", help="STM32 serial port (e.g. COM3)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--record", action="store_true", help="Start recording immediately")
    parser.add_argument("--out", default="collected_data", help="Output directory")
    args = parser.parse_args()

    print("=" * 55)
    print("PC Controller — Self-Driving Data Collection Station")
    print("=" * 55)
    print(f"RPi: {args.rpi}")
    print(f"STM32: {args.com or '(keyboard only)'}")
    print(f"Output: {args.out}")
    print(f"Record: {'ON' if args.record else 'OFF'}")
    print("-" * 55)

    # Init components
    video = VideoReceiver(args.rpi, args.video_port)
    cmd = CommandSender(args.rpi, args.cmd_port)
    encoder = EncoderReader(args.com, args.baud)
    recorder = Recorder(args.out)

    video.start()
    cmd.start()
    encoder.start()

    if args.record:
        recorder.toggle()

    # State
    base_speed = 0.5
    kb_steering = 0.0   # keyboard fallback
    auto_steering = 0.0  # encoder steering
    last_cmd = "X"
    last_frame_time = time.time()
    fps = 0.0

    print("\nControls:")
    print("  W/S = forward/back    A/D = steer (kb fallback)")
    print("  X = stop              SPACE = toggle record")
    print("  +/- = adjust speed    ESC = quit\n")

    try:
        while True:
            frame = video.get_frame()
            now = time.time()

            if frame is not None:
                # FPS
                dt = now - last_frame_time
                if dt > 0:
                    fps = 0.9 * fps + 0.1 / dt
                last_frame_time = now

                # Steering from encoder (if available) or keyboard
                if encoder.connected:
                    auto_steering = encoder.value
                steering = auto_steering if encoder.connected else kb_steering

                # Compute motor speeds
                left = base_speed * (1.0 - steering)
                right = base_speed * (1.0 + steering)

                # Send continuous steer command
                cmd.send(f"STEER:{left:.3f},{right:.3f}")
                last_cmd = f"S {steering:+.2f}"

                # Record
                recorder.record(frame, steering, now)

                # Display
                display = draw_hud(frame, steering, base_speed,
                                   auto_steering if encoder.connected else kb_steering,
                                   recorder.is_recording, fps, last_cmd)
                cv2.imshow("Self-Driving Controller", display)

            # Keyboard
            key = cv2.waitKey(10) & 0xFF
            if key == 27:   # ESC
                break
            elif key == 32:  # SPACE
                recorder.toggle()
            elif key == ord('w') or key == ord('W'):
                base_speed = min(1.0, base_speed + 0.1)
                cmd.send("CMD:W")
                last_cmd = "W"
            elif key == ord('s') or key == ord('S'):
                base_speed = max(-1.0, base_speed - 0.1)
                cmd.send("CMD:S")
                last_cmd = "S"
            elif key == ord('a') or key == ord('A'):
                kb_steering = max(-1.0, kb_steering - 0.2)
                if not encoder.connected:
                    cmd.send("CMD:A")
                    last_cmd = "A"
            elif key == ord('d') or key == ord('D'):
                kb_steering = min(1.0, kb_steering + 0.2)
                if not encoder.connected:
                    cmd.send("CMD:D")
                    last_cmd = "D"
            elif key == ord('x') or key == ord('X'):
                base_speed = 0.0
                cmd.send("CMD:X")
                last_cmd = "X"
            elif key == ord('=') or key == ord('+'):
                base_speed = min(1.0, base_speed + 0.1)
            elif key == ord('-') or key == ord('_'):
                base_speed = max(-1.0, base_speed - 0.1)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down...")
        cmd.send("CMD:X")
        time.sleep(0.2)
        recorder.close()
        video.stop()
        cmd.stop()
        encoder.stop()
        cv2.destroyAllWindows()

        total = len(recorder._metadata)
        print(f"Done. {total} frames saved to {args.out}/")
        if total > 0:
            print(f"Run training: python train_model.py --data {args.out}")


if __name__ == "__main__":
    main()
