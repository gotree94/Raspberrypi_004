#!/usr/bin/env python3
"""
Raspberry Pi 4 컨트롤러 — STM32F103 시뮬레이터 검증 도구 (GUI, ASCII 전용)
SIMULATOR_DEV_GUIDE.md Stage 12~14 기준 프로토콜

사용법:
    python rpi_controller_v1.py                           # GUI 실행 (포트 선택)
    python rpi_controller_v1.py --serial-port COM3        # COM3 직접 연결
    python rpi_controller_v1.py --serial-port COM3 --auto-test  # CLI 자동 테스트
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import sys
import argparse
import os
import glob
import socket


# ============================================================
# 포트 스캐너
# ============================================================
def scan_serial_ports():
    ports = []
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            desc = f"{p.device}"
            if p.description and p.description != p.device:
                desc += f" ({p.description})"
            ports.append(desc)
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
                ports.append(path)
            except:
                pass
    else:
        for pat in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyAMA*', '/dev/ttyS*']:
            for path in glob.glob(pat):
                if os.path.exists(path):
                    ports.append(path)
    return ports


# ============================================================
# RPi Controller — 백엔드 (시리얼 통신 + 데이터 처리, ASCII 전용)
# ============================================================
class RPiController:
    def __init__(self, serial_port=None, baud=115200):
        self.serial_port = serial_port
        self.baud = baud
        self.ser = None
        self.running = True
        self._read_thread = None
        self.lock = threading.Lock()

        self.latest = {}
        self.packet_count = 0
        self.last_status_time = 0
        self.log_buffer = []
        self.max_log = 200

        self.on_status = None
        self.on_response = None
        self.on_error = None
        self.on_log = None

    def connect(self, port=None):
        if port:
            self.serial_port = port
        if not self.serial_port:
            self._emit_log("[ERROR] 포트가 지정되지 않음")
            return False
        try:
            import serial
            self.ser = serial.Serial(self.serial_port, self.baud, timeout=1)
            self.running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            self._emit_log(f"{self.serial_port} @ {self.baud}bps 연결됨")
            return True
        except ImportError:
            self._emit_log("[ERROR] pyserial 필요: pip install pyserial")
            return False
        except Exception as e:
            self._emit_log(f"[ERROR] 연결 실패: {e}")
            return False

    def disconnect(self):
        self.running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except:
                pass
        self._emit_log("연결 종료")

    def _emit_log(self, msg):
        with self.lock:
            self.log_buffer.append(msg)
            if len(self.log_buffer) > self.max_log:
                self.log_buffer = self.log_buffer[-self.max_log:]
        if self.on_log:
            self.on_log(msg)

    def _read_loop(self):
        import serial
        buf = ''
        while self.running and self.ser and self.ser.is_open:
            try:
                data = self.ser.read(1024)
                if not data:
                    time.sleep(0.01)
                    continue
                buf += data.decode('utf-8', errors='ignore')
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    self._process_line(line.strip())
            except serial.SerialException:
                time.sleep(0.5)
            except:
                time.sleep(0.1)

    def _process_line(self, line):
        if not line:
            return
        with self.lock:
            self.packet_count += 1
            self.last_status_time = time.time()

        if line.startswith('S,'):
            parts = line[2:].split(',')
            data = {}
            for p in parts:
                if '=' in p:
                    k, v = p.split('=', 1)
                    data[k] = v
            with self.lock:
                self.latest = data
            if self.on_status:
                self.on_status(data)
        elif line.startswith('R,'):
            self._emit_log(f"[RX] {line}")
            if self.on_response:
                self.on_response(line)

    def send_cmd(self, cmd_str):
        if not self.ser or not self.ser.is_open:
            self._emit_log("[ERROR] 연결되지 않음")
            return None
        full = cmd_str if cmd_str.startswith('C,') else f"C,{cmd_str}"
        try:
            self.ser.write((full + '\n').encode())
            self._emit_log(f"[TX] {full}")
            return full
        except Exception as e:
            self._emit_log(f"[ERROR] 전송 실패: {e}")
            return None

    def auto_test(self, progress_cb=None, done_cb=None):
        tests = [
            ("WHEEL1=500", "바퀴1 속도 설정"),
            ("WHEEL2=300", "바퀴2 속도 설정"),
            ("WHEEL3=700", "바퀴3 속도 설정"),
            ("WHEEL4=999", "바퀴4 최고 속도"),
            ("WHEEL1=0",   "바퀴1 정지"),
            ("SERVO1=0",   "서보1 0도"),
            ("SERVO1=500", "서보1 90도"),
            ("SERVO1=999", "서보1 180도"),
            ("SERVO2=250", "서보2 45도"),
            ("CLCD=Hello World!", "CLCD 1행 출력"),
            ("CLCD=Line1\nLine2", "CLCD 2행 출력"),
            ("LED_G=500",  "2색 LED G=500"),
            ("LED_B=800",  "2색 LED B=800"),
            ("LED_RGB_R=999", "3색 LED R=999"),
            ("LED_RGB_G=500", "3색 LED G=500"),
            ("LED_RGB_B=200", "3색 LED B=200"),
            ("BUZZER=1",   "부저 ON"),
            ("BUZZER=0",   "부저 OFF"),
            ("LASER=1",    "레이저 ON"),
            ("LASER=0",    "레이저 OFF"),
            ("IR_TX=5",    "IR 송신 5"),
            ("IR_TX=9",    "IR 송신 9"),
        ]
        error_tests = [
            ("WHEEL1=1000", "범위 초과"),
            ("SERVO3=500",  "없는 키"),
            ("BUZZER=2",    "잘못된 값"),
            ("INVALID_KEY=1", "알 수 없는 키"),
        ]
        passed = 0
        failed = 0
        results = []

        for cmd, desc in tests:
            if progress_cb:
                progress_cb(f"[TEST] {desc} ({cmd})... ", None)
            self.send_cmd(cmd)
            time.sleep(0.3)
            found = False
            for _ in range(10):
                with self.lock:
                    for log in reversed(self.log_buffer):
                        if '[RX] R,OK' in log:
                            found = True
                            break
                if found:
                    break
                time.sleep(0.1)
            if found:
                results.append((desc, cmd, True, "R,OK"))
                passed += 1
                if progress_cb:
                    progress_cb("", True)
            else:
                results.append((desc, cmd, False, "R,OK 없음"))
                failed += 1
                if progress_cb:
                    progress_cb("", False)

        for cmd, desc in error_tests:
            if progress_cb:
                progress_cb(f"[TEST] {desc} ({cmd})... ", None)
            self.send_cmd(cmd)
            time.sleep(0.3)
            found = False
            err_msg = ""
            for _ in range(10):
                with self.lock:
                    for log in reversed(self.log_buffer):
                        if '[RX] R,ERR' in log:
                            found = True
                            err_msg = log.split('] ')[-1] if '] ' in log else log
                            break
                if found:
                    break
                time.sleep(0.1)
            if found:
                results.append((desc, cmd, True, err_msg))
                passed += 1
                if progress_cb:
                    progress_cb("", True)
            else:
                results.append((desc, cmd, False, "R,ERR 없음"))
                failed += 1
                if progress_cb:
                    progress_cb("", False)

        if done_cb:
            done_cb(passed, failed, results)
        return failed == 0


# ============================================================
# Tkinter GUI (ASCII 전용)
# ============================================================
class ControllerGUI:
    COLORS = {
        'bg': '#1e1e2e',
        'fg': '#cdd6f4',
        'card': '#313244',
        'accent': '#89b4fa',
        'green': '#a6e3a1',
        'red': '#f38ba8',
        'yellow': '#f9e2af',
    }

    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.ctrl.on_status = self._on_status
        self.ctrl.on_log = self._on_log
        self.ctrl.on_response = self._on_response
        self._connected = False
        self._updating = False

        self.root = tk.Tk()
        self.root.title("RPi Controller — STM32F103 시뮬레이터 검증 도구 (ASCII)")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 1050, 920
        if sh < h + 80:
            h = sh - 80
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(950, 600)
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

        if self.ctrl.serial_port:
            self.port_combo.set(self.ctrl.serial_port)

        self._start_sensor_update()

    def _build_ui(self):
        conn_frame = tk.Frame(self.root, bg=self.COLORS['card'])
        conn_frame.pack(fill=tk.X, padx=10, pady=(10, 2))

        tk.Label(conn_frame, text="COM 포트:", bg=self.COLORS['card'],
                 fg=self.COLORS['fg'], font=('Consolas', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        self.port_combo = ttk.Combobox(conn_frame, width=32, font=('Consolas', 9))
        self.port_combo.pack(side=tk.LEFT, padx=2)

        tk.Button(conn_frame, text="\U0001f504", command=self._refresh_ports, width=3,
                  bg=self.COLORS['card'], fg=self.COLORS['accent'],
                  font=('Consolas', 10)).pack(side=tk.LEFT, padx=2)

        self.conn_btn = tk.Button(conn_frame, text="연결", command=self._toggle_connection,
                                  bg=self.COLORS['green'], fg='black',
                                  font=('Consolas', 9, 'bold'), width=8)
        self.conn_btn.pack(side=tk.LEFT, padx=10)

        self.conn_status = tk.Label(conn_frame, text="\u26d4 연결 끊김", bg=self.COLORS['card'],
                                    fg=self.COLORS['red'], font=('Consolas', 9))
        self.conn_status.pack(side=tk.LEFT, padx=5)

        self._refresh_ports()

        panes = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.COLORS['bg'],
                               sashwidth=3, sashrelief=tk.RAISED)
        panes.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = tk.Frame(panes, bg=self.COLORS['bg'])
        panes.add(left_frame, width=440, minsize=300)

        sensor_frame = tk.LabelFrame(left_frame, text="센서 데이터 (실시간)",
                                     fg=self.COLORS['accent'], bg=self.COLORS['bg'],
                                     font=('Consolas', 11, 'bold'))
        sensor_frame.pack(fill=tk.BOTH, expand=True)

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
            ('RPM', 'RPM 엔진회전수'),
        ]
        for i, (key, label) in enumerate(sensors):
            bg_color = self.COLORS['card'] if i % 2 == 0 else self.COLORS['bg']
            lbl = tk.Label(sensor_frame, text=f"{label} :", anchor='e',
                           bg=bg_color, fg=self.COLORS['fg'],
                           font=('Consolas', 10), width=24)
            lbl.grid(row=i, column=0, sticky='e', padx=5, pady=1)
            val = tk.Label(sensor_frame, text="---", anchor='w',
                           bg=bg_color, fg=self.COLORS['yellow'],
                           font=('Consolas', 10, 'bold'), width=16)
            val.grid(row=i, column=1, sticky='w', padx=5, pady=1)
            self.sensor_labels[key] = val

        sensor_frame.grid_columnconfigure(0, weight=1)

        right_frame = tk.Frame(panes, bg=self.COLORS['bg'])
        panes.add(right_frame, width=460, minsize=300)

        right_canvas = tk.Canvas(right_frame, bg=self.COLORS['bg'],
                                 highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=right_canvas.yview)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_canvas.configure(yscrollcommand=right_scroll.set)

        ctrl_frame = tk.Frame(right_canvas, bg=self.COLORS['bg'])
        right_canvas_window = right_canvas.create_window((0, 0), window=ctrl_frame, anchor='nw')

        def _configure_inner(event):
            right_canvas.configure(scrollregion=right_canvas.bbox('all'))
            right_canvas.itemconfig(right_canvas_window, width=right_canvas.winfo_width())

        ctrl_frame.bind('<Configure>', _configure_inner)
        right_canvas.bind('<Configure>', lambda e: right_canvas.itemconfig(
            right_canvas_window, width=e.width))

        _bind_mousewheel(right_canvas)

        cmd_label = tk.Label(ctrl_frame, text="명령 전송 (ASCII)", fg=self.COLORS['accent'],
                             bg=self.COLORS['bg'], font=('Consolas', 11, 'bold'))
        cmd_label.pack(anchor='w', padx=5, pady=(5, 2))

        entry_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg'])
        entry_frame.pack(fill=tk.X, padx=5, pady=2)
        self.cmd_entry = tk.Entry(entry_frame, bg=self.COLORS['card'], fg=self.COLORS['fg'],
                                  font=('Consolas', 9))
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.cmd_entry.insert(0, "ex: WHEEL1=500")
        self.cmd_entry.bind('<Return>', lambda e: self._send_manual())
        tk.Button(entry_frame, text="전송", command=self._send_manual,
                  bg=self.COLORS['card'], fg=self.COLORS['accent'],
                  font=('Consolas', 8, 'bold'), width=6).pack(side=tk.RIGHT)

        self.test_btn = tk.Button(ctrl_frame, text="\u25b6 자동 테스트 실행 (26개)",
                                  command=self._start_auto_test,
                                  bg=self.COLORS['card'], fg=self.COLORS['green'],
                                  font=('Consolas', 10, 'bold'))
        self.test_btn.pack(fill=tk.X, padx=5, pady=3)

        sep1 = tk.Frame(ctrl_frame, height=2, bg=self.COLORS['card'])
        sep1.pack(fill=tk.X, padx=5, pady=5)

        act_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg'])
        act_frame.pack(fill=tk.X, padx=5)

        self.var_wheel = {}
        for i in range(1, 5):
            row_f = tk.Frame(act_frame, bg=self.COLORS['bg'])
            row_f.pack(fill=tk.X, pady=1)
            tk.Label(row_f, text=f"WHEEL{i}", bg=self.COLORS['bg'],
                     fg=self.COLORS['fg'], font=('Consolas', 9), width=8, anchor='e').pack(side=tk.LEFT)
            var = tk.DoubleVar(value=0)
            var.trace_add('write', lambda *a, idx=i: self._on_scale_change(f'WHEEL{idx}', int(self.var_wheel[idx][0].get())))
            s = tk.Scale(row_f, from_=0, to=999, orient=tk.HORIZONTAL,
                         variable=var, length=140, bg=self.COLORS['card'],
                         fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                         troughcolor=self.COLORS['bg'], font=('Consolas', 7), showvalue=0)
            s.pack(side=tk.LEFT, padx=3)
            vl = tk.Label(row_f, text="0", bg=self.COLORS['bg'],
                          fg=self.COLORS['green'], font=('Consolas', 9), width=5)
            vl.pack(side=tk.LEFT)
            self.var_wheel[i] = (var, vl)

        self.var_servo = {}
        for i in range(1, 3):
            row_f = tk.Frame(act_frame, bg=self.COLORS['bg'])
            row_f.pack(fill=tk.X, pady=1)
            tk.Label(row_f, text=f"SERVO{i}", bg=self.COLORS['bg'],
                     fg=self.COLORS['fg'], font=('Consolas', 9), width=8, anchor='e').pack(side=tk.LEFT)
            var = tk.DoubleVar(value=0)
            var.trace_add('write', lambda *a, idx=i: self._on_scale_change(f'SERVO{idx}', int(self.var_servo[idx][0].get())))
            tk.Scale(row_f, from_=0, to=999, orient=tk.HORIZONTAL,
                     variable=var, length=140, bg=self.COLORS['card'],
                     fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                     troughcolor=self.COLORS['bg'], font=('Consolas', 7), showvalue=0).pack(side=tk.LEFT, padx=3)
            al = tk.Label(row_f, text="0\u00b0", bg=self.COLORS['bg'],
                          fg=self.COLORS['green'], font=('Consolas', 9), width=5)
            al.pack(side=tk.LEFT)
            self.var_servo[i] = (var, al)

        sep2 = tk.Frame(ctrl_frame, height=2, bg=self.COLORS['card'])
        sep2.pack(fill=tk.X, padx=5, pady=5)

        clcd_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg'])
        clcd_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(clcd_frame, text="CLCD", bg=self.COLORS['bg'],
                 fg=self.COLORS['fg'], font=('Consolas', 9), width=8, anchor='e').pack(side=tk.LEFT)
        self.clcd_entry = tk.Entry(clcd_frame, bg=self.COLORS['card'], fg=self.COLORS['fg'],
                                   font=('Consolas', 9), width=20)
        self.clcd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(clcd_frame, text="전송", command=self._send_clcd,
                  bg=self.COLORS['card'], fg=self.COLORS['accent'],
                  font=('Consolas', 8)).pack(side=tk.LEFT, padx=2)
        self.clcd_disp = tk.Label(ctrl_frame, text="[                ]\n[                ]",
                                  bg='black', fg=self.COLORS['green'],
                                  font=('Consolas', 9), anchor='w', justify=tk.LEFT)
        self.clcd_disp.pack(fill=tk.X, padx=(40, 5), pady=1)

        led_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg'])
        led_frame.pack(fill=tk.X, padx=5, pady=2)
        for ch, label in [('g', 'LED G'), ('b', 'LED B')]:
            tk.Label(led_frame, text=label, bg=self.COLORS['bg'],
                     fg=self.COLORS['fg'], font=('Consolas', 9), width=8, anchor='e').pack(side=tk.LEFT)
            var = tk.DoubleVar(value=0)
            var.trace_add('write', lambda *a, ch_=ch: self._on_scale_change(f'LED_{ch_.upper()}', int(getattr(self, f'_led2_{ch_}_var').get())))
            setattr(self, f'_led2_{ch}_var', var)
            tk.Scale(led_frame, from_=0, to=999, orient=tk.HORIZONTAL,
                     variable=var, length=100, bg=self.COLORS['card'],
                     fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                     troughcolor=self.COLORS['bg'], font=('Consolas', 7), showvalue=0).pack(side=tk.LEFT, padx=2)

        rgb_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg'])
        rgb_frame.pack(fill=tk.X, padx=5, pady=1)
        for ch, color, label in [('r', '#f38ba8', 'RGB R'), ('g', '#a6e3a1', 'RGB G'), ('b', '#89b4fa', 'RGB B')]:
            tk.Label(rgb_frame, text=label, bg=self.COLORS['bg'],
                     fg=color, font=('Consolas', 9), width=8, anchor='e').pack(side=tk.LEFT)
            var = tk.DoubleVar(value=0)
            var.trace_add('write', lambda *a, ch_=ch: self._on_scale_change(f'LED_RGB_{ch_.upper()}', int(getattr(self, f'_led3_{ch_}_var').get())))
            setattr(self, f'_led3_{ch}_var', var)
            tk.Scale(rgb_frame, from_=0, to=999, orient=tk.HORIZONTAL,
                     variable=var, length=100, bg=self.COLORS['card'],
                     fg=self.COLORS['fg'], highlightbackground=self.COLORS['bg'],
                     troughcolor=self.COLORS['bg'], font=('Consolas', 7), showvalue=0).pack(side=tk.LEFT, padx=2)

        btn_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=5, pady=3)
        self.buzzer_btn = tk.Button(btn_frame, text="BUZZER OFF", width=10,
                                    command=self._toggle_buzzer,
                                    bg=self.COLORS['card'], fg=self.COLORS['red'],
                                    font=('Consolas', 9))
        self.buzzer_btn.pack(side=tk.LEFT, padx=3)
        self.laser_btn = tk.Button(btn_frame, text="LASER OFF", width=10,
                                   command=self._toggle_laser,
                                   bg=self.COLORS['card'], fg=self.COLORS['red'],
                                   font=('Consolas', 9))
        self.laser_btn.pack(side=tk.LEFT, padx=3)
        self._buzzer_state = 0
        self._laser_state = 0

        ir_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg'])
        ir_frame.pack(fill=tk.X, padx=5, pady=3)
        tk.Label(ir_frame, text="IR TX:", bg=self.COLORS['bg'],
                 fg=self.COLORS['accent'], font=('Consolas', 9, 'bold')).pack(side=tk.LEFT)
        for n in range(1, 10):
            tk.Button(ir_frame, text=str(n), width=2,
                      command=lambda v=n: self._ir_tx(v),
                      bg=self.COLORS['card'], fg=self.COLORS['accent'],
                      font=('Consolas', 9)).pack(side=tk.LEFT, padx=1)

        log_frame = tk.LabelFrame(self.root, text="시리얼 로그 (ASCII)",
                                  fg=self.COLORS['accent'], bg=self.COLORS['bg'],
                                  font=('Consolas', 10, 'bold'))
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 5))

        log_top_frame = tk.Frame(log_frame, bg=self.COLORS['bg'])
        log_top_frame.pack(fill=tk.X)
        self.test_log = tk.Text(log_frame, height=5, bg='black', fg=self.COLORS['green'],
                                font=('Consolas', 9), state=tk.DISABLED)
        self.test_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 2))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=5, bg='black', fg=self.COLORS['green'],
            font=('Consolas', 9), insertbackground=self.COLORS['fg'])
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        status_frame = tk.Frame(self.root, bg=self.COLORS['card'])
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.status_label = tk.Label(
            status_frame, text="포트 선택 후 연결하세요 | 10Hz | 수신: 0 패킷 | 오류: 0",
            bg=self.COLORS['card'], fg=self.COLORS['fg'],
            font=('Consolas', 9), anchor='w')
        self.status_label.pack(fill=tk.X, padx=5, pady=3)

    def _refresh_ports(self):
        ports = scan_serial_ports()
        self.port_combo['values'] = ports
        if ports and not self.port_combo.get():
            self.port_combo.set(ports[0])

    def _toggle_connection(self):
        if self._connected:
            self.ctrl.disconnect()
            self._connected = False
            self.conn_btn.config(text="연결", bg=self.COLORS['green'])
            self.conn_status.config(text="\u26d4 연결 끊김", fg=self.COLORS['red'])
            return
        port_str = self.port_combo.get().strip()
        if not port_str:
            return
        dev = port_str.split(' ')[0]
        if self.ctrl.connect(dev):
            self._connected = True
            self.conn_btn.config(text="종료", bg=self.COLORS['red'])
            self.conn_status.config(text=f"{dev}", fg=self.COLORS['green'])

    def _send_manual(self):
        line = self.cmd_entry.get().strip()
        if line:
            self.ctrl.send_cmd(line)

    def _on_scale_change(self, key, val):
        if not self._connected or self._updating:
            return
        self.ctrl.send_cmd(f"{key}={val}")

    def _toggle_buzzer(self):
        self._buzzer_state = 0 if self._buzzer_state else 1
        self.ctrl.send_cmd(f"BUZZER={self._buzzer_state}")
        self.buzzer_btn.config(text=f"BUZZER {'ON' if self._buzzer_state else 'OFF'}",
                               fg=self.COLORS['green'] if self._buzzer_state else self.COLORS['red'])

    def _toggle_laser(self):
        self._laser_state = 0 if self._laser_state else 1
        self.ctrl.send_cmd(f"LASER={self._laser_state}")
        self.laser_btn.config(text=f"LASER {'ON' if self._laser_state else 'OFF'}",
                              fg=self.COLORS['green'] if self._laser_state else self.COLORS['red'])

    def _ir_tx(self, val):
        self.ctrl.send_cmd(f"IR_TX={val}")

    def _send_clcd(self):
        text = self.clcd_entry.get()[:32]
        line1 = text[:16] if len(text) >= 16 else text
        line2 = text[16:32] if len(text) > 16 else ''
        self.clcd_disp.config(text=f"[{line1:<16}]\n[{line2:<16}]")
        self.ctrl.send_cmd(f"CLCD={text}")

    def _on_status(self, data):
        pass

    def _on_log(self, msg):
        self.root.after(0, lambda: self._append_log(msg))

    def _append_log(self, msg):
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)

    def _on_response(self, line):
        pass

    def _start_sensor_update(self):
        def loop():
            data = None
            with self.ctrl.lock:
                if self.ctrl.latest:
                    data = dict(self.ctrl.latest)
            if data:
                for key, val_str in data.items():
                    if key in self.sensor_labels:
                        self.sensor_labels[key].config(text=val_str)
            pkt = 0
            with self.ctrl.lock:
                pkt = self.ctrl.packet_count
            port_display = self.ctrl.serial_port or "미연결"
            self.status_label.config(
                text=f"{port_display} | {self.ctrl.baud}bps | 수신: {pkt} 패킷")
            self.root.after(100, loop)
        self.root.after(100, loop)

    def _start_auto_test(self):
        if not self._connected:
            messagebox.showwarning("알림", "먼저 연결하세요")
            return
        self.test_btn.config(text="\u23f3 테스트 실행 중...", state=tk.DISABLED)
        self.test_log.config(state=tk.NORMAL)
        self.test_log.delete('1.0', tk.END)
        self.test_log.config(state=tk.DISABLED)

        def run():
            def prog(msg, ok):
                self.root.after(0, lambda: self._test_progress(msg, ok))
            def done(passed, failed, results):
                self.root.after(0, lambda: self._test_done(passed, failed, results))
            self.ctrl.auto_test(progress_cb=prog, done_cb=done)

        th = threading.Thread(target=run, daemon=True)
        th.start()

    def _test_progress(self, msg, ok):
        self.test_log.config(state=tk.NORMAL)
        if msg is not None:
            self.test_log.insert(tk.END, msg)
        if ok is True:
            self.test_log.insert(tk.END, "\u2713 PASS\n", 'pass')
            self.test_log.tag_config('pass', foreground=self.COLORS['green'])
        elif ok is False:
            self.test_log.insert(tk.END, "\u2717 FAIL\n", 'fail')
            self.test_log.tag_config('fail', foreground=self.COLORS['red'])
        self.test_log.see(tk.END)
        self.test_log.config(state=tk.DISABLED)

    def _test_done(self, passed, failed, results):
        self.test_log.config(state=tk.NORMAL)
        sep = "\u2500" * 50 + "\n"
        self.test_log.insert(tk.END, sep)
        if failed == 0:
            self.test_log.insert(tk.END, f"\u2705 전체 통과: {passed}/{passed + failed}\n", 'pass')
        else:
            self.test_log.insert(tk.END, f"\u26a0\ufe0f  {passed} 통과, {failed} 실패\n", 'fail')
            for desc, cmd, ok, msg in results:
                if not ok:
                    self.test_log.insert(tk.END, f"  \u2717 {desc}: {msg}\n", 'fail')
        self.test_log.tag_config('pass', foreground=self.COLORS['green'])
        self.test_log.tag_config('fail', foreground=self.COLORS['red'])
        self.test_log.see(tk.END)
        self.test_log.config(state=tk.DISABLED)
        self.test_btn.config(text="\u25b6 자동 테스트 실행 (26개)", state=tk.NORMAL)
        messagebox.showinfo("테스트 완료",
                            f"{'전체 통과' if failed == 0 else '일부 실패'}\n"
                            f"{passed} 통과, {failed} 실패 (총 {passed + failed}개)")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.ctrl.disconnect()
        self.root.destroy()


def _bind_mousewheel(canvas):
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)


def main():
    parser = argparse.ArgumentParser(description='RPi Controller — STM32F103 (ASCII v1)')
    parser.add_argument('--serial-port', default=None, help='시리얼 포트')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--auto-test', action='store_true', help='CLI 자동 테스트')
    args = parser.parse_args()

    if args.auto_test:
        port = args.serial_port
        if not port:
            ports = scan_serial_ports()
            if not ports:
                print("[ERROR] 사용 가능한 COM 포트가 없습니다")
                return
            print("사용 가능한 포트:")
            for i, p in enumerate(ports):
                print(f"  [{i}] {p}")
            try:
                sel = int(input("선택: "))
                port = ports[sel].split(' ')[0]
            except (ValueError, IndexError):
                print("[ERROR] 잘못된 선택")
                return
        ctrl = RPiController(serial_port=port, baud=args.baud)
        if not ctrl.connect():
            return
        time.sleep(0.5)
        ctrl.auto_test()
        ctrl.disconnect()
        print("\n테스트 완료")
    else:
        ctrl = RPiController(serial_port=args.serial_port, baud=args.baud)
        gui = ControllerGUI(ctrl)
        gui.run()


if __name__ == '__main__':
    main()
