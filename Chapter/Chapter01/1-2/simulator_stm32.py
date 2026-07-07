#!/usr/bin/env python3
"""
NUCLEO STM32F103 차량 시뮬레이터 — 시리얼 포트 통신 전용
UART 115200 baud (기본)

사용법:
    python simulator_stm32.py                         # GUI 실행 (포트 선택)
    python simulator_stm32.py --serial-port COM3      # COM3 직접 지정
    python simulator_stm32.py --serial-port /dev/ttyACM0  # Linux
    python simulator_stm32.py --headless --serial-port COM3  # GUI 없이
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import random
import math
import sys
import argparse
import glob
import os
import socket  # COM 포트 스캔 fallback 용
import struct


# ============================================================
# 시리얼 포트 스캐너
# ============================================================
def scan_serial_ports():
    ports = []
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            desc = f"{p.device}"
            if p.description and p.description != p.device:
                desc += f" ({p.description})"
            ports.append({'device': p.device, 'description': desc})
        return ports
    except ImportError:
        pass
    if sys.platform.startswith('win'):
        for i in range(256):
            path = f'COM{i}'
            try:
                s = socket.socket()
                s.connect((path, 0))
                s.close()
                ports.append({'device': path, 'description': path})
            except:
                pass
    else:
        for pattern in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyAMA*', '/dev/ttyS*']:
            for path in glob.glob(pattern):
                if os.path.exists(path):
                    ports.append({'device': path, 'description': path})
    return ports


# ============================================================
# BinaryProtocol — 효율적 바이너리 패킷 인코딩/디코딩
# ============================================================
class BinaryProtocol:
    ACTUATOR_IDS = {
        'WHEEL1': 1, 'WHEEL2': 2, 'WHEEL3': 3, 'WHEEL4': 4,
        'SERVO1': 5, 'SERVO2': 6, 'CLCD': 7,
        'LED_G': 8, 'LED_B': 9,
        'LED_RGB_R': 10, 'LED_RGB_G': 11, 'LED_RGB_B': 12,
        'BUZZER': 13, 'LASER': 14, 'IR_TX': 15,
    }
    ID_TO_KEY = {v: k for k, v in ACTUATOR_IDS.items()}
    S_SIZE = 37

    @staticmethod
    def encode_status(engine):
        with engine.lock:
            lat = engine.gps_center_lat + engine.gps_radius * math.cos(engine.gps_theta)
            lng = engine.gps_center_lng + engine.gps_radius * math.sin(engine.gps_theta)
            data = bytearray(BinaryProtocol.S_SIZE)
            data[0] = ord('S')
            struct.pack_into('<H', data, 1, int(engine.sensors['CDS']['val']))
            struct.pack_into('<H', data, 3, int(engine.sensors['HALL']['val']))
            struct.pack_into('<H', data, 5, int(engine.sensors['TEMP']['val'] * 10))
            struct.pack_into('<H', data, 7, int(engine.sensors['HUMI_T']['val']))
            struct.pack_into('<H', data, 9, int(engine.sensors['HUMI_H']['val']))
            data[11] = int(engine.sensors['ROT']['val'])
            struct.pack_into('<H', data, 12, int(engine.sensors['US_DIST']['val']))
            struct.pack_into('<H', data, 14, int(engine.joy['x']))
            struct.pack_into('<H', data, 16, int(engine.joy['y']))
            data[18] = int(engine.sensors['IR_RX']['val'])
            struct.pack_into('<i', data, 19, int(lat * 10000))
            struct.pack_into('<i', data, 23, int(lng * 10000))
            struct.pack_into('<H', data, 27, int(engine.fuel))
            struct.pack_into('<h', data, 29, int(engine.acc_x))
            struct.pack_into('<h', data, 31, int(engine.acc_y))
            struct.pack_into('<h', data, 33, int(engine.acc_z))
            struct.pack_into('<H', data, 35, int(engine.rpm))
        return bytes(data)

    @staticmethod
    def decode_command(cmd_data):
        if len(cmd_data) < 2 or cmd_data[0] != ord('C'):
            return None
        id_ = cmd_data[1]
        key = BinaryProtocol.ID_TO_KEY.get(id_)
        if key is None:
            return [('?', '0')]
        if key == 'CLCD':
            text = cmd_data[2:34].split(b'\x00')[0].decode('utf-8', errors='ignore')
            return [(key, text)]
        if len(cmd_data) < 4:
            return None
        val = str(struct.unpack_from('<H', cmd_data, 2)[0])
        return [(key, val)]

    @staticmethod
    def encode_response(resp_str):
        if resp_str.startswith('R,OK'):
            return bytes([ord('R'), 0])
        err_msg = resp_str.split('=', 1)[1] if '=' in resp_str else resp_str[3:]
        err_bytes = err_msg.encode('utf-8')[:12]
        return bytes([ord('R'), 1]) + err_bytes.ljust(12, b'\x00')


# ============================================================
# SimulatorEngine — 모든 센서/액추에이터 상태 관리
# ============================================================
class SimulatorEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.sensors = {
            'CDS':     {'val': 500,  'min': 0,   'max': 999, 'rate': 10},
            'HALL':    {'val': 500,  'min': 0,   'max': 999, 'rate': 15},
            'TEMP':    {'val': 500,  'min': 0,   'max': 999, 'rate': 5},
            'HUMI_T':  {'val': 500,  'min': 0,   'max': 999, 'rate': 7},
            'HUMI_H':  {'val': 500,  'min': 0,   'max': 999, 'rate': 11},
            'ROT':     {'val': 0,    'min': 0,   'max': 100, 'rate': 0},
            'US_DIST': {'val': 500,  'min': 0,   'max': 999, 'rate': 18},
            'IR_RX':   {'val': 0,    'min': 0,   'max': 9,   'rate': 0},
        }
        self.joy = {'x': 500, 'y': 500}
        self.joy_dir_x = 1
        self.joy_dir_y = 1
        self.joy_count_x = 0
        self.joy_count_y = 0
        self.joy_step_x = 7
        self.joy_step_y = 11
        self.joy_cycles_x = 5
        self.joy_cycles_y = 5
        self.gps_center_lat = 37.5600
        self.gps_center_lng = 127.0000
        self.gps_radius = 0.001
        self.gps_theta = 0.0
        self.gps_speed = 2 * math.pi / 600
        self.fuel = 1000
        self.fuel_driving = True
        self.acc_x = 0.0
        self.acc_y = 5.0
        self.acc_z = 980.0
        self.rpm = 550
        self.act = {
            'WHEEL1': 0, 'WHEEL2': 0, 'WHEEL3': 0, 'WHEEL4': 0,
            'SERVO1': 0, 'SERVO2': 0, 'CLCD': '',
            'LED_G': 0, 'LED_B': 0,
            'LED_RGB_R': 0, 'LED_RGB_G': 0, 'LED_RGB_B': 0,
            'BUZZER': 0, 'LASER': 0, 'IR_TX': 0,
        }

    def update_sensors(self):
        with self.lock:
            for key, s in self.sensors.items():
                if s['rate'] > 0 and key not in ('ROT', 'IR_RX'):
                    delta = (random.random() - 0.5) * 2 * s['rate'] / 600
                    s['val'] = max(s['min'], min(s['max'], s['val'] + delta))
            if self.joy_count_x < self.joy_cycles_x:
                self.joy['x'] += self.joy_step_x * self.joy_dir_x
                self.joy_count_x += 1
            else:
                self.joy_dir_x *= -1
                self.joy_count_x = 0
                self.joy['x'] += self.joy_step_x * self.joy_dir_x
                self.joy_count_x += 1
            if self.joy_count_y < self.joy_cycles_y:
                self.joy['y'] += self.joy_step_y * self.joy_dir_y
                self.joy_count_y += 1
            else:
                self.joy_dir_y *= -1
                self.joy_count_y = 0
                self.joy['y'] += self.joy_step_y * self.joy_dir_y
                self.joy_count_y += 1
            self.joy['x'] = max(0, min(999, self.joy['x']))
            self.joy['y'] = max(0, min(999, self.joy['y']))
            self.gps_theta += self.gps_speed
            if self.gps_theta > 2 * math.pi:
                self.gps_theta -= 2 * math.pi
            if self.fuel > 0:
                self.fuel -= 0.1 if not self.fuel_driving else 1.0
                self.fuel = max(0, self.fuel)
            self.acc_x = (random.random() - 0.5) * 20
            self.acc_y = (random.random() - 0.5) * 20
            self.acc_z = 980 + (random.random() - 0.5) * 10
            self.rpm = max(0, min(999, self.rpm + (random.random() - 0.5) * 20))

    def get_status_line(self):
        with self.lock:
            lat = self.gps_center_lat + self.gps_radius * math.cos(self.gps_theta)
            lng = self.gps_center_lng + self.gps_radius * math.sin(self.gps_theta)
            return "S," + ",".join([
                f"CDS={self.sensors['CDS']['val']:.0f}",
                f"HALL={self.sensors['HALL']['val']:.0f}",
                f"TEMP={self.sensors['TEMP']['val']:.1f}",
                f"HUMI_T={self.sensors['HUMI_T']['val']:.0f}",
                f"HUMI_H={self.sensors['HUMI_H']['val']:.0f}",
                f"ROT={self.sensors['ROT']['val']:.0f}",
                f"US_DIST={self.sensors['US_DIST']['val']:.0f}",
                f"JOY_X={self.joy['x']:.0f}",
                f"JOY_Y={self.joy['y']:.0f}",
                f"IR_RX={self.sensors['IR_RX']['val']:.0f}",
                f"GPS_LAT={lat:.4f}",
                f"GPS_LNG={lng:.4f}",
                f"FUEL={self.fuel:.0f}",
                f"ACC_X={self.acc_x:.1f}",
                f"ACC_Y={self.acc_y:.1f}",
                f"ACC_Z={self.acc_z:.1f}",
                f"RPM={self.rpm:.0f}",
            ])

    def process_command(self, line):
        line = line.strip()
        if not line.startswith('C,'):
            return None
        body = line[2:]
        pairs = body.split(',')
        errors = []
        for pair in pairs:
            if '=' not in pair:
                continue
            k, v = pair.split('=', 1)
            k = k.strip().upper()
            v = v.strip()
            if k in ('WHEEL1', 'WHEEL2', 'WHEEL3', 'WHEEL4'):
                try:
                    val = int(v)
                    if 0 <= val <= 999:
                        self.act[k] = val
                    else:
                        errors.append(f"{k} out of range (0~999)")
                except ValueError:
                    errors.append(f"{k} invalid int")
            elif k in ('SERVO1', 'SERVO2'):
                try:
                    val = int(v)
                    if 0 <= val <= 999:
                        self.act[k] = val
                    else:
                        errors.append(f"{k} out of range (0~999)")
                except ValueError:
                    errors.append(f"{k} invalid int")
            elif k == 'CLCD':
                self.act['CLCD'] = v[:32]
            elif k in ('LED_G', 'LED_B'):
                try:
                    val = int(v)
                    if 0 <= val <= 999:
                        self.act[k] = val
                    else:
                        errors.append(f"{k} out of range (0~999)")
                except ValueError:
                    errors.append(f"{k} invalid int")
            elif k in ('LED_RGB_R', 'LED_RGB_G', 'LED_RGB_B'):
                try:
                    val = int(v)
                    if 0 <= val <= 999:
                        self.act[k] = val
                    else:
                        errors.append(f"{k} out of range (0~999)")
                except ValueError:
                    errors.append(f"{k} invalid int")
            elif k == 'BUZZER':
                if v in ('0', '1'):
                    self.act['BUZZER'] = int(v)
                else:
                    errors.append("BUZZER must be 0 or 1")
            elif k == 'LASER':
                if v in ('0', '1'):
                    self.act['LASER'] = int(v)
                else:
                    errors.append("LASER must be 0 or 1")
            elif k == 'IR_TX':
                try:
                    val = int(v)
                    if 1 <= val <= 9:
                        self.act['IR_TX'] = val
                    else:
                        errors.append("IR_TX out of range (1~9)")
                except ValueError:
                    errors.append("IR_TX invalid int")
            else:
                errors.append(f"Unknown key: {k}")
        if errors:
            return "R,ERR=" + "; ".join(errors)
        return "R,OK"

    def get_sensor_display(self):
        with self.lock:
            lat = self.gps_center_lat + self.gps_radius * math.cos(self.gps_theta)
            lng = self.gps_center_lng + self.gps_radius * math.sin(self.gps_theta)
            return {
                'CDS': f"{self.sensors['CDS']['val']:.0f}",
                'HALL': f"{self.sensors['HALL']['val']:.0f}",
                'TEMP': f"{self.sensors['TEMP']['val']:.1f}",
                'HUMI_T': f"{self.sensors['HUMI_T']['val']:.0f}",
                'HUMI_H': f"{self.sensors['HUMI_H']['val']:.0f}",
                'ROT': f"{self.sensors['ROT']['val']:.0f}",
                'US_DIST': f"{self.sensors['US_DIST']['val']:.0f}",
                'JOY_X': f"{self.joy['x']:.0f}",
                'JOY_Y': f"{self.joy['y']:.0f}",
                'IR_RX': f"{self.sensors['IR_RX']['val']:.0f}",
                'GPS_LAT': f"{lat:.4f}",
                'GPS_LNG': f"{lng:.4f}",
                'FUEL': f"{self.fuel:.0f}",
                'ACC_X': f"{self.acc_x:.1f}",
                'ACC_Y': f"{self.acc_y:.1f}",
                'ACC_Z': f"{self.acc_z:.1f}",
                'RPM': f"{self.rpm:.0f}",
            }


# ============================================================
# Communication Handler (Serial 전용)
# ============================================================
class CommsHandler:
    def __init__(self, engine, serial_port=None, baud=115200, mode='ascii'):
        self.engine = engine
        self.serial_port = serial_port
        self.baud = baud
        self.mode = mode
        self.running = True
        self.ser = None
        self.tx_count = 0
        self.rx_count = 0
        self.callback = None
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except:
            pass

    def disconnect(self):
        self.stop()

    def set_callback(self, cb):
        self.callback = cb

    def _run(self):
        try:
            import serial
            self.ser = serial.Serial(self.serial_port, self.baud, timeout=1)
            if self.callback:
                self.callback('log', f"시리얼 열림: {self.serial_port} @ {self.baud}bps ({self.mode})")
            if self.mode == 'efficient':
                self._run_efficient()
            else:
                self._run_ascii()
            if self.ser and self.ser.is_open:
                self.ser.close()
        except ImportError:
            if self.callback:
                self.callback('log', "❌ pyserial 미설치: pip install pyserial")
        except Exception as e:
            if self.callback:
                self.callback('log', f"❌ 시리얼 오류: {e}")

    def _run_ascii(self):
        buf = ''
        while self.running:
            try:
                data = self.ser.read(1024)
                if data:
                    buf += data.decode('utf-8', errors='ignore')
                    while '\n' in buf:
                        line, buf = buf.split('\n', 1)
                        resp = self.engine.process_command(line)
                        if resp:
                            self.ser.write((resp + '\n').encode())
                            self.tx_count += 1
                            if self.callback:
                                self.callback('rx_cmd', line)
                                self.callback('tx_resp', resp)
                else:
                    time.sleep(0.01)
            except serial.SerialException:
                time.sleep(0.5)

    def _run_efficient(self):
        while self.running:
            try:
                header = self.ser.read(1)
                if not header:
                    time.sleep(0.01)
                    continue
                if header[0] == ord('C'):
                    id_byte = self.ser.read(1)
                    if not id_byte:
                        continue
                    if id_byte[0] == 7:
                        payload = self.ser.read(32)
                        if len(payload) < 32:
                            continue
                        cmd_data = bytes([ord('C'), 7]) + payload
                    else:
                        val_bytes = self.ser.read(2)
                        if len(val_bytes) < 2:
                            continue
                        cmd_data = bytes([ord('C'), id_byte[0]]) + val_bytes
                    pairs = BinaryProtocol.decode_command(cmd_data)
                    if pairs and pairs[0][0] != '?':
                        key, val = pairs[0]
                        cmd_line = f"C,{key}={val}"
                        resp = self.engine.process_command(cmd_line)
                        if resp:
                            self.ser.write(BinaryProtocol.encode_response(resp))
                            self.tx_count += 1
                            if self.callback:
                                self.callback('rx_cmd', cmd_line)
                                self.callback('tx_resp', resp)
                    else:
                        self.ser.write(BinaryProtocol.encode_response("R,ERR=Unknown key"))
                        if self.callback:
                            self.callback('log', f"[BIN] unknown ID: {id_byte[0]}")
                elif header[0] == ord('R'):
                    self.ser.read(1)
                    if self.callback:
                        self.callback('log', "[BIN] unexpected R")
            except serial.SerialException:
                time.sleep(0.5)

    def send_status(self, line):
        if self.ser and self.ser.is_open:
            try:
                if self.mode == 'efficient':
                    payload = BinaryProtocol.encode_status(self.engine)
                else:
                    payload = (line + '\n').encode()
                self.ser.write(payload)
                self.tx_count += 1
                if self.callback:
                    self.callback('tx_status', line)
            except:
                pass


# ============================================================
# Tkinter GUI
# ============================================================
class SimulatorGUI:
    COLORS = {
        'bg': '#1e1e2e',
        'fg': '#cdd6f4',
        'card': '#313244',
        'accent': '#89b4fa',
        'green': '#a6e3a1',
        'red': '#f38ba8',
        'yellow': '#f9e2af',
    }

    def __init__(self, engine, comms):
        self.engine = engine
        self.comms = comms
        self.comms.set_callback(self.on_comms)
        self._updating = False
        self._connected = False

        self.root = tk.Tk()
        mode_label = "Binary" if self.comms.mode == 'efficient' else "ASCII"
        self.root.title(f"NUCLEO STM32F103 차량 시뮬레이터 — {mode_label}")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 1000, 950
        if sh < h + 80:
            h = sh - 80
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(900, 600)
        self.root.configure(bg=self.COLORS['bg'])

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=self.COLORS['bg'], foreground=self.COLORS['fg'],
                        fieldbackground=self.COLORS['card'])
        style.configure('TLabel', background=self.COLORS['bg'], foreground=self.COLORS['fg'])
        style.configure('TFrame', background=self.COLORS['bg'])
        style.configure('TLabelframe', background=self.COLORS['bg'], foreground=self.COLORS['fg'])
        style.configure('TLabelframe.Label', background=self.COLORS['bg'], foreground=self.COLORS['fg'])
        style.configure('TButton', background=self.COLORS['card'], foreground=self.COLORS['fg'])
        style.map('TButton', background=[('active', self.COLORS['accent'])])

        self._build_ui()

        if self.comms.serial_port:
            self.port_combo.set(self.comms.serial_port)

        self._start_10hz_loop()

    def _build_ui(self):
        conn_frame = tk.Frame(self.root, bg=self.COLORS['card'])
        conn_frame.pack(fill=tk.X, padx=10, pady=(10, 2))

        tk.Label(conn_frame, text="COM 포트:", bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], font=('Consolas', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        self.port_combo = ttk.Combobox(conn_frame, width=32, font=('Consolas', 9))
        self.port_combo.pack(side=tk.LEFT, padx=2)

        tk.Button(conn_frame, text="🔄", command=self._refresh_ports, width=3,
                  bg=self.COLORS['card'], fg=self.COLORS['accent'],
                  font=('Consolas', 10)).pack(side=tk.LEFT, padx=2)

        self.conn_btn = tk.Button(conn_frame, text="연결", command=self._toggle_connection,
                                  bg=self.COLORS['green'], fg='black',
                                  font=('Consolas', 9, 'bold'), width=8)
        self.conn_btn.pack(side=tk.LEFT, padx=10)

        self.conn_status = tk.Label(conn_frame, text="⛔ 연결 끊김", bg=self.COLORS['card'],
                                    fg=self.COLORS['red'], font=('Consolas', 9))
        self.conn_status.pack(side=tk.LEFT, padx=5)

        self._refresh_ports()

        top = tk.Frame(self.root, bg=self.COLORS['bg'])
        top.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        sensor_frame = tk.LabelFrame(top, text="센서 (10Hz 자동 전송)", fg=self.COLORS['accent'],
                                     bg=self.COLORS['bg'], font=('Consolas', 11, 'bold'))
        sensor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.sensor_labels = {}
        sensors = [
            ('CDS', 'CDS 조도'), ('HALL', 'HALL 홀센서'),
            ('TEMP', 'TEMP 온도'), ('HUMI_T', 'HUMI_T 온습도 온도'),
            ('HUMI_H', 'HUMI_H 온습도 습도'), ('ROT', 'ROT 로터리'),
            ('US_DIST', 'US_DIST 초음파'), ('JOY_X', 'JOY_X 조이스틱 X'),
            ('JOY_Y', 'JOY_Y 조이스틱 Y'), ('IR_RX', 'IR_RX 수신'),
            ('GPS_LAT', 'GPS_LAT 위도'), ('GPS_LNG', 'GPS_LNG 경도'),
            ('FUEL', 'FUEL 연료'), ('ACC_X', 'ACC_X 가속도 X'),
            ('ACC_Y', 'ACC_Y 가속도 Y'), ('ACC_Z', 'ACC_Z 가속도 Z'),
            ('RPM', 'RPM'),
        ]
        for i, (key, label) in enumerate(sensors):
            lbl = tk.Label(sensor_frame, text=f"{label} :", anchor='e',
                           bg=self.COLORS['card'], fg=self.COLORS['fg'],
                           font=('Consolas', 10), width=22)
            lbl.grid(row=i, column=0, sticky='e', padx=5, pady=1)
            val = tk.Label(sensor_frame, text="---", anchor='w',
                           bg=self.COLORS['card'], fg=self.COLORS['yellow'],
                           font=('Consolas', 10), width=14)
            val.grid(row=i, column=1, sticky='w', padx=5, pady=1)
            self.sensor_labels[key] = val

        act_frame = tk.LabelFrame(top, text="액추에이터 제어 (RPi → STM32)", fg=self.COLORS['accent'],
                                  bg=self.COLORS['bg'], font=('Consolas', 11, 'bold'))
        act_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        row = 0
        self.wheel_scales = {}
        for i in range(1, 5):
            lbl = tk.Label(act_frame, text=f"WHEEL{i}", bg=self.COLORS['card'],
                           fg=self.COLORS['fg'], font=('Consolas', 9), width=10, anchor='e')
            lbl.grid(row=row, column=0, sticky='e', padx=3, pady=1)
            var = tk.DoubleVar(value=0)
            var.trace_add('write', lambda *a, idx=i: self._on_wheel_change(idx))
            tk.Scale(act_frame, from_=0, to=999, orient=tk.HORIZONTAL,
                     variable=var, length=160, bg=self.COLORS['card'],
                     fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                     troughcolor=self.COLORS['bg'], font=('Consolas', 7)).grid(
                         row=row, column=1, padx=3, pady=1)
            val_lbl = tk.Label(act_frame, text="0", bg=self.COLORS['card'],
                               fg=self.COLORS['green'], font=('Consolas', 9), width=5)
            val_lbl.grid(row=row, column=2, padx=3, pady=1)
            self.wheel_scales[i] = (var, val_lbl)
            row += 1

        self.servo_scales = {}
        for i in range(1, 3):
            lbl = tk.Label(act_frame, text=f"SERVO{i}", bg=self.COLORS['card'],
                           fg=self.COLORS['fg'], font=('Consolas', 9), width=10, anchor='e')
            lbl.grid(row=row, column=0, sticky='e', padx=3, pady=1)
            var = tk.DoubleVar(value=0)
            var.trace_add('write', lambda *a, idx=i: self._on_servo_change(idx))
            tk.Scale(act_frame, from_=0, to=999, orient=tk.HORIZONTAL,
                     variable=var, length=160, bg=self.COLORS['card'],
                     fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                     troughcolor=self.COLORS['bg'], font=('Consolas', 7)).grid(
                         row=row, column=1, padx=3, pady=1)
            ang_lbl = tk.Label(act_frame, text="0°", bg=self.COLORS['card'],
                               fg=self.COLORS['green'], font=('Consolas', 9), width=5)
            ang_lbl.grid(row=row, column=2, padx=3, pady=1)
            self.servo_scales[i] = (var, ang_lbl)
            row += 1

        # CLCD
        tk.Label(act_frame, text="CLCD", bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], font=('Consolas', 9), width=10, anchor='e').grid(
                     row=row, column=0, sticky='e', padx=3, pady=1)
        self.clcd_entry = tk.Entry(act_frame, bg=self.COLORS['card'], fg=self.COLORS['fg'],
                                   font=('Consolas', 9), width=22)
        self.clcd_entry.grid(row=row, column=1, padx=3, pady=1)
        tk.Button(act_frame, text="CLCD 전송", command=self._send_clcd,
                  bg=self.COLORS['card'], fg=self.COLORS['accent'],
                  font=('Consolas', 8)).grid(row=row, column=2, padx=3)
        self.clcd_display = tk.Label(act_frame, text="[                ]\n[                ]",
                                     bg='black', fg=self.COLORS['green'],
                                     font=('Consolas', 9), width=22, anchor='w')
        self.clcd_display.grid(row=row+1, column=0, columnspan=3, pady=2)
        row += 2

        # 2색 LED
        tk.Label(act_frame, text="LED G (초)", bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], font=('Consolas', 9), width=10, anchor='e').grid(
                     row=row, column=0, sticky='e', padx=3, pady=1)
        self.led2g_var = tk.DoubleVar(value=0)
        self.led2g_var.trace_add('write', lambda *a: self._on_led2_change('g'))
        tk.Scale(act_frame, from_=0, to=999, orient=tk.HORIZONTAL,
                 variable=self.led2g_var, length=160, bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                 troughcolor=self.COLORS['bg'], font=('Consolas', 7)).grid(
                     row=row, column=1, padx=3, pady=1)
        row += 1

        tk.Label(act_frame, text="LED B (파)", bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], font=('Consolas', 9), width=10, anchor='e').grid(
                     row=row, column=0, sticky='e', padx=3, pady=1)
        self.led2b_var = tk.DoubleVar(value=0)
        self.led2b_var.trace_add('write', lambda *a: self._on_led2_change('b'))
        tk.Scale(act_frame, from_=0, to=999, orient=tk.HORIZONTAL,
                 variable=self.led2b_var, length=160, bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                 troughcolor=self.COLORS['bg'], font=('Consolas', 7)).grid(
                     row=row, column=1, padx=3, pady=1)
        row += 1

        for _, (k, c) in enumerate([('R', '빨강'), ('G', '초록'), ('B', '파랑')]):
            tk.Label(act_frame, text=f"RGB {c}", bg=self.COLORS['card'],
                     fg=self.COLORS['fg'], font=('Consolas', 9), width=10, anchor='e').grid(
                         row=row, column=0, sticky='e', padx=3, pady=1)
            var = tk.DoubleVar(value=0)
            var.trace_add('write', lambda *a, ch_=k.lower(): self._on_led3_change(ch_))
            tk.Scale(act_frame, from_=0, to=999, orient=tk.HORIZONTAL,
                     variable=var, length=160, bg=self.COLORS['card'],
                     fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                     troughcolor=self.COLORS['bg'], font=('Consolas', 7)).grid(
                         row=row, column=1, padx=3, pady=1)
            setattr(self, f'led3{k.lower()}_var', var)
            row += 1

        btn_frame = tk.Frame(act_frame, bg=self.COLORS['bg'])
        btn_frame.grid(row=row, column=0, columnspan=3, pady=5)
        self.buzzer_btn = tk.Button(btn_frame, text="BUZZER OFF", width=10,
                                    command=self._toggle_buzzer,
                                    bg=self.COLORS['card'], fg=self.COLORS['red'],
                                    font=('Consolas', 9))
        self.buzzer_btn.pack(side=tk.LEFT, padx=5)
        self.laser_btn = tk.Button(btn_frame, text="LASER OFF", width=10,
                                   command=self._toggle_laser,
                                   bg=self.COLORS['card'], fg=self.COLORS['red'],
                                   font=('Consolas', 9))
        self.laser_btn.pack(side=tk.LEFT, padx=5)
        row += 1

        ir_frame = tk.Frame(act_frame, bg=self.COLORS['bg'])
        ir_frame.grid(row=row, column=0, columnspan=3, pady=3)
        tk.Label(ir_frame, text="IR TX:", bg=self.COLORS['bg'],
                 fg=self.COLORS['accent'], font=('Consolas', 9, 'bold')).pack(side=tk.LEFT)
        for n in range(1, 10):
            tk.Button(ir_frame, text=str(n), width=2,
                      command=lambda v=n: self._ir_tx(v),
                      bg=self.COLORS['card'], fg=self.COLORS['accent'],
                      font=('Consolas', 9)).pack(side=tk.LEFT, padx=1)
        row += 1

        ir_rx_frame = tk.Frame(act_frame, bg=self.COLORS['bg'])
        ir_rx_frame.grid(row=row, column=0, columnspan=3, pady=3)
        tk.Label(ir_rx_frame, text="IR RX:", bg=self.COLORS['bg'],
                 fg=self.COLORS['green'], font=('Consolas', 9, 'bold')).pack(side=tk.LEFT)
        for n in range(0, 10):
            tk.Button(ir_rx_frame, text=str(n), width=2,
                      command=lambda v=n: self._ir_rx(v),
                      bg=self.COLORS['card'], fg=self.COLORS['green'],
                      font=('Consolas', 9)).pack(side=tk.LEFT, padx=1)
        row += 1

        rot_frame = tk.LabelFrame(act_frame, text="로터리 엔코더", fg=self.COLORS['accent'],
                                   bg=self.COLORS['bg'], font=('Consolas', 10, 'bold'))
        rot_frame.grid(row=row, column=0, columnspan=3, pady=5, sticky='ew')
        self.rot_var = tk.DoubleVar(value=0)
        tk.Scale(rot_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.rot_var,
                 length=300, bg=self.COLORS['card'], fg=self.COLORS['fg'],
                 highlightbackground=self.COLORS['bg'], troughcolor=self.COLORS['bg'],
                 font=('Consolas', 8)).pack(padx=10, pady=5)
        self.rot_var.trace_add('write', lambda *a: self._update_rotary())
        row += 1

        gps_frame = tk.LabelFrame(act_frame, text="GPS 중심 설정", fg=self.COLORS['accent'],
                                   bg=self.COLORS['bg'], font=('Consolas', 10, 'bold'))
        gps_frame.grid(row=row, column=0, columnspan=3, pady=5, sticky='ew')
        self.gps_lat_var = tk.StringVar(value="37.5600")
        self.gps_lng_var = tk.StringVar(value="127.0000")
        tk.Label(gps_frame, text="위도:", bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], font=('Consolas', 9)).pack(side=tk.LEFT, padx=3)
        tk.Entry(gps_frame, textvariable=self.gps_lat_var, width=10,
                 bg=self.COLORS['card'], fg=self.COLORS['fg'],
                 font=('Consolas', 9)).pack(side=tk.LEFT, padx=2)
        tk.Label(gps_frame, text="경도:", bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], font=('Consolas', 9)).pack(side=tk.LEFT, padx=3)
        tk.Entry(gps_frame, textvariable=self.gps_lng_var, width=10,
                 bg=self.COLORS['card'], fg=self.COLORS['fg'],
                 font=('Consolas', 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(gps_frame, text="적용", command=self._set_gps_center,
                  bg=self.COLORS['card'], fg=self.COLORS['accent'],
                  font=('Consolas', 8)).pack(side=tk.LEFT, padx=5)
        row += 1

        fuel_frame = tk.Frame(act_frame, bg=self.COLORS['bg'])
        fuel_frame.grid(row=row, column=0, columnspan=3, pady=3)
        tk.Button(fuel_frame, text="⛽ 연료 채움", command=self._refill_fuel,
                  bg=self.COLORS['card'], fg=self.COLORS['green'],
                  font=('Consolas', 10, 'bold'), width=12).pack(side=tk.LEFT, padx=2)
        self.fuel_mode_btn = tk.Button(fuel_frame, text="모드: 주행",
                                       command=self._toggle_fuel_mode,
                                       bg=self.COLORS['card'], fg=self.COLORS['yellow'],
                                       font=('Consolas', 9), width=12)
        self.fuel_mode_btn.pack(side=tk.LEFT, padx=2)

        bottom = tk.Frame(self.root, bg=self.COLORS['bg'])
        bottom.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        log_frame = tk.LabelFrame(bottom, text="시리얼 로그", fg=self.COLORS['accent'],
                                   bg=self.COLORS['bg'], font=('Consolas', 10, 'bold'))
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=8, bg='black', fg=self.COLORS['green'],
            font=('Consolas', 9), insertbackground=self.COLORS['fg'])
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        status_frame = tk.Frame(self.root, bg=self.COLORS['card'])
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.status_label = tk.Label(
            status_frame, text="포트 선택 후 연결하세요 | 10Hz | TX: 0 | RX: 0",
            bg=self.COLORS['card'], fg=self.COLORS['fg'],
            font=('Consolas', 9), anchor='w')
        self.status_label.pack(fill=tk.X, padx=5, pady=3)

        cmd_frame = tk.Frame(bottom, bg=self.COLORS['bg'])
        cmd_frame.pack(fill=tk.X, pady=2)
        self.cmd_entry = tk.Entry(cmd_frame, bg=self.COLORS['card'], fg=self.COLORS['fg'],
                                  font=('Consolas', 9))
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.cmd_entry.insert(0, "ex: C,WHEEL1=500,WHEEL2=500,SERVO1=90")
        self.cmd_entry.bind('<Return>', lambda e: self._send_manual_cmd())
        tk.Button(cmd_frame, text="명령 전송", command=self._send_manual_cmd,
                  bg=self.COLORS['card'], fg=self.COLORS['accent'],
                  font=('Consolas', 8)).pack(side=tk.RIGHT)

    # --------------------------------------------------------
    # 연결 제어
    # --------------------------------------------------------
    def _refresh_ports(self):
        ports = scan_serial_ports()
        self.port_combo['values'] = [p['description'] for p in ports]
        if ports and not self.port_combo.get():
            self.port_combo.set(ports[0]['description'])

    def _toggle_connection(self):
        if self._connected:
            self.comms.stop()
            self._connected = False
            self.conn_btn.config(text="연결", bg=self.COLORS['green'])
            self.conn_status.config(text="⛔ 연결 끊김", fg=self.COLORS['red'])
            self.log("[SERIAL] 연결 종료됨")
            return

        port_str = self.port_combo.get().strip()
        if not port_str:
            self.log("[SERIAL] COM 포트를 선택하세요")
            return

        dev = port_str.split(' ')[0] if port_str else port_str
        self.comms.stop()
        time.sleep(0.2)
        self.comms.serial_port = dev
        self.comms.baud = 115200
        self.comms.ser = None
        self.comms.tx_count = 0
        self.comms.rx_count = 0
        self.comms.start()
        self._connected = True
        self.conn_btn.config(text="종료", bg=self.COLORS['red'])
        self.conn_status.config(text=f"✅ {dev}", fg=self.COLORS['green'])
        self.log(f"[SERIAL] {dev} @ 115200bps 연결 시작")

    # --------------------------------------------------------
    # 액추에이터 콜백
    # --------------------------------------------------------
    def _on_wheel_change(self, i):
        if self._updating:
            return
        val = int(self.wheel_scales[i][0].get())
        self._send_actuator_cmd(f"C,WHEEL{i}={val}")

    def _on_servo_change(self, i):
        if self._updating:
            return
        val = int(self.servo_scales[i][0].get())
        self._send_actuator_cmd(f"C,SERVO{i}={val}")

    def _on_led2_change(self, ch):
        if self._updating:
            return
        val = int(getattr(self, f'led2{ch}_var').get())
        self._send_actuator_cmd(f"C,LED_{ch.upper()}={val}")

    def _on_led3_change(self, ch):
        if self._updating:
            return
        val = int(getattr(self, f'led3{ch}_var').get())
        self._send_actuator_cmd(f"C,LED_RGB_{ch.upper()}={val}")

    def _send_clcd(self):
        text = self.clcd_entry.get()[:32]
        line1 = text[:16] if len(text) >= 16 else text
        line2 = text[16:32] if len(text) > 16 else ''
        self.clcd_display.config(text=f"[{line1:<16}]\n[{line2:<16}]")
        self._send_actuator_cmd(f"C,CLCD={text}")

    def _toggle_buzzer(self):
        new = 0 if self.engine.act['BUZZER'] else 1
        self._send_actuator_cmd(f"C,BUZZER={new}")
        new = self.engine.act['BUZZER']
        self.buzzer_btn.config(text=f"BUZZER {'ON' if new else 'OFF'}",
                               fg=self.COLORS['green'] if new else self.COLORS['red'])

    def _toggle_laser(self):
        new = 0 if self.engine.act['LASER'] else 1
        self._send_actuator_cmd(f"C,LASER={new}")
        new = self.engine.act['LASER']
        self.laser_btn.config(text=f"LASER {'ON' if new else 'OFF'}",
                              fg=self.COLORS['green'] if new else self.COLORS['red'])

    def _ir_tx(self, val):
        self.engine.act['IR_TX'] = val
        self._send_actuator_cmd(f"C,IR_TX={val}")
        self.log(f"[IR TX] 버튼 {val} 전송")

    def _ir_rx(self, val):
        with self.engine.lock:
            self.engine.sensors['IR_RX']['val'] = val
        self.log(f"[IR RX] 수신값 설정: {val}")

    def _update_rotary(self):
        val = int(self.rot_var.get())
        with self.engine.lock:
            self.engine.sensors['ROT']['val'] = val

    def _set_gps_center(self):
        try:
            lat = float(self.gps_lat_var.get())
            lng = float(self.gps_lng_var.get())
            with self.engine.lock:
                self.engine.gps_center_lat = lat
                self.engine.gps_center_lng = lng
            self.log(f"[GPS] 중심 설정: {lat:.4f}, {lng:.4f}")
        except ValueError:
            self.log("[GPS] 잘못된 좌표값")

    def _refill_fuel(self):
        with self.engine.lock:
            self.engine.fuel = 1000
        self.log("[FUEL] 연료가 가득 채워졌습니다 (1000)")

    def _toggle_fuel_mode(self):
        with self.engine.lock:
            self.engine.fuel_driving = not self.engine.fuel_driving
            mode = self.engine.fuel_driving
        label = "주행" if mode else "정차"
        self.fuel_mode_btn.config(text=f"모드: {label}",
                                  fg=self.COLORS['green'] if mode else self.COLORS['red'])
        self.log(f"[FUEL] 연료 모드: {'주행(1/틱)' if mode else '정차(0.1/틱)'}")

    def _send_actuator_cmd(self, cmd_line):
        self.comms.rx_count += 1
        if self.comms.ser and self.comms.ser.is_open:
            self.comms.ser.write((cmd_line + '\n').encode())
        resp = self.engine.process_command(cmd_line)
        self.log(f"[TX→STM32] {cmd_line}")
        if resp:
            self.log(f"[RX←STM32] {resp}")

    def _send_manual_cmd(self):
        line = self.cmd_entry.get().strip()
        if line:
            self._send_actuator_cmd(line)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)

    def on_comms(self, tag, msg):
        if tag == 'log':
            self.root.after(0, lambda: self.log(f"[{tag}] {msg}"))
        elif tag == 'rx_cmd':
            self.root.after(0, lambda: self.log(f"[RX←RPi] {msg}"))
        elif tag == 'tx_resp':
            self.root.after(0, lambda: self.log(f"[TX→RPi] {msg}"))

    def _start_10hz_loop(self):
        def loop():
            self.engine.update_sensors()
            display = self.engine.get_sensor_display()
            for key, val_str in display.items():
                if key in self.sensor_labels:
                    self.sensor_labels[key].config(text=val_str)

            self._updating = True
            with self.engine.lock:
                for i in range(1, 5):
                    var, lbl = self.wheel_scales[i]
                    val = self.engine.act[f'WHEEL{i}']
                    var.set(val)
                    lbl.config(text=str(val))
                for i in range(1, 3):
                    var, lbl = self.servo_scales[i]
                    val = self.engine.act[f'SERVO{i}']
                    var.set(val)
                    lbl.config(text=f"{val * 180 / 1000:.0f}°")
                self.led2g_var.set(self.engine.act['LED_G'])
                self.led2b_var.set(self.engine.act['LED_B'])
                self.led3r_var.set(self.engine.act['LED_RGB_R'])
                self.led3g_var.set(self.engine.act['LED_RGB_G'])
                self.led3b_var.set(self.engine.act['LED_RGB_B'])
            self._updating = False

            status_line = self.engine.get_status_line()
            self.comms.send_status(status_line)

            port_display = self.comms.serial_port or "미연결"
            self.status_label.config(
                text=f"{port_display} | 115200bps | 10Hz | TX: {self.comms.tx_count} | RX: {self.comms.rx_count}")

            self.root.after(100, loop)

        self.root.after(100, loop)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.comms.stop()
        self.root.destroy()


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='NUCLEO STM32F103 차량 시뮬레이터 (Serial)')
    parser.add_argument('--serial-port', default=None, help='시리얼 포트 (예: COM3, /dev/ttyACM0)')
    parser.add_argument('--baud', type=int, default=115200, help='보드레이트 (기본: 115200)')
    parser.add_argument('--headless', action='store_true', help='GUI 없이 실행')
    parser.add_argument('--efficient', action='store_true', help='효율적 바이너리 프로토콜 사용')
    args = parser.parse_args()

    mode = 'efficient' if args.efficient else 'ascii'
    engine = SimulatorEngine()
    comms = CommsHandler(engine, serial_port=args.serial_port, baud=args.baud, mode=mode)

    if args.headless:
        if not args.serial_port:
            print("headless 모드에서는 --serial-port 가 필요합니다")
            sys.exit(1)
        comms.start()
        print(f"[Headless] STM32F103 시뮬레이터 실행 중 ({mode})")
        print(f"  시리얼 포트: {args.serial_port} @ {args.baud}bps")
        try:
            while True:
                time.sleep(0.1)
                engine.update_sensors()
                comms.send_status(engine.get_status_line())
        except KeyboardInterrupt:
            print("\n종료")
        finally:
            comms.stop()
    else:
        gui = SimulatorGUI(engine, comms)
        gui.run()


if __name__ == '__main__':
    main()
