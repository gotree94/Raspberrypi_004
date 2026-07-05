# STM32F103 차량 시뮬레이터 — 단계별 개발 가이드

## 개요

이 문서는 NUCLEO STM32F103 차량 시뮬레이터(`simulator_stm32.py`)와 RPi 컨트롤러(`rpi_controller.py`)를
**빈 파일에서 시작하여 한 단계씩 구현**하는 가이드입니다.

각 Stage는 독립적으로 실행·검증 가능하며, 이전 Stage의 결과물 위에 쌓아갑니다.

---

## Stage 0 — 프로젝트 준비 및 ICD 문서

### 목표
디렉토리 구조 생성, ICD 문서 초안 작성, 개발 환경 확인.

### 구현
1. 작업 디렉토리 확인:
   ```
   D:\github\Raspberrypi_004\Chapter\Chapter01\1-2\
   ```
2. `ICD_SIMULATOR.md` — 통신 프로토콜 규격 문서 (385줄 완성본은 최종 Stage 참조)
3. 필요한 라이브러리:
   ```
   pip install pyserial  # (선택) 풍부한 COM 포트 정보
   ```

### 검증
```
python -c "import tkinter; import serial; print('OK')"
# pyserial 미설치 시: python -c "import tkinter; print('OK (pyserial 없음)')"
```

### 파일 구조 (Stage 0)
```
1-2/
├── ICD_SIMULATOR.md
└──  (simulator_stm32.py, rpi_controller.py는 1~15 Stage에서 작성)
```

---

## Stage 1 — Core Engine + Serial 기본 구조

### 목표
- `SimulatorEngine` 클래스: 센서·액추에이터 상태 보관소
- `CommsHandler` 클래스: 시리얼 포트 송수신 기본 구조
- CLI `--headless` 모드: GUI 없이 엔진 + 시리얼만 구동
- `main()`: 인자 파싱 + 엔진/커뮤니케이션 연결

### 구현 상세

#### 1-a. SimulatorEngine 뼈대

```python
class SimulatorEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.sensors = {}          # {'CDS': {'val': 500, 'min': 0, 'max': 999, 'rate': 10}, ...}
        self.joy = {'x': 500, 'y': 500}
        self.gps_center_lat = 37.5600
        self.gps_center_lng = 127.0000
        self.gps_radius = 0.001
        self.gps_theta = 0.0
        self.fuel = 1000
        self.acc_x = self.acc_y = 0.0
        self.acc_z = 980.0
        self.rpm = 550
        self.act = {}               # {'WHEEL1': 0, ..., 'BUZZER': 0, ...}

    def update_sensors(self):
        # 10Hz tick마다 호출: 센서값 갱신 (1~5 Stage에서 채움)
        pass

    def get_status_line(self):
        # S,CDS=450,HALL=320,... 형태 문자열 반환
        return "S," + ",".join([...])

    def process_command(self, line):
        # C,WHEEL1=500,... 처리 → "R,OK" 또는 "R,ERR=..."
        return "R,OK"
```

#### 1-b. CommsHandler 뼈대

```python
class CommsHandler:
    def __init__(self, engine, serial_port=None, baud=115200):
        self.engine = engine
        self.serial_port = serial_port
        self.baud = baud
        self.ser = None
        self.running = True
        self.tx_count = self.rx_count = 0
        self.callback = None

    def start(self):
        # 시리얼 열기 + 읽기 스레드 시작
        self.ser = serial.Serial(self.serial_port, self.baud, timeout=1)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        buf = ''
        while self.running:
            data = self.ser.read(1024)
            if data:
                buf += data.decode('utf-8', errors='ignore')
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    resp = self.engine.process_command(line)
                    if resp:
                        self.ser.write((resp + '\n').encode())
                        self.tx_count += 1

    def send_status(self, line):
        if self.ser and self.ser.is_open:
            self.ser.write((line + '\n').encode())
            self.tx_count += 1

    def stop(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
```

#### 1-c. main() + headless 모드

```python
def main():
    parser = argparse.ArgumentParser(...)
    parser.add_argument('--serial-port')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()

    engine = SimulatorEngine()
    comms = CommsHandler(engine, serial_port=args.serial_port, baud=args.baud)

    if args.headless:
        comms.start()
        print(f"[Headless] 시작: {args.serial_port}")
        try:
            while True:
                time.sleep(0.1)
                engine.update_sensors()
                comms.send_status(engine.get_status_line())
        except KeyboardInterrupt:
            comms.stop()
    else:
        # Stage 8에서 GUI로 대체
        print("GUI 모드는 Stage 8부터 구현")
```

#### 1-d. 포트 스캐너

```python
def scan_serial_ports():
    ports = []
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            ports.append({'device': p.device, 'description': f"{p.device} ({p.description})"})
        return ports
    except ImportError:
        pass
    if sys.platform.startswith('win'):
        for i in range(256):
            try:
                s = socket.socket()
                s.connect((f'COM{i}', 0))
                s.close()
                ports.append({'device': f'COM{i}', 'description': f'COM{i}'})
            except:
                pass
    else:
        for pat in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyAMA*', '/dev/ttyS*']:
            for path in glob.glob(pat):
                if os.path.exists(path):
                    ports.append({'device': path, 'description': path})
    return ports
```

### 검증
```
# 문법 검사
python -c "import ast; ast.parse(open('simulator_stm32.py').read()); print('OK')"

# headless 모드 실행 (연결 없이 엔진만 구동)
python simulator_stm32.py --headless --serial-port COM1
# → "Connecting..." 후 SerialException 발생 (당연함, 포트가 없으므로)
# → Ctrl+C로 종료
```

---

## Stage 2 — 센서 Random Walk 시뮬레이션

### 목표
8개 기본 센서(CDS, HALL, TEMP, HUMI_T, HUMI_H, ROT, US_DIST, IR_RX)에
분당 변화율 기반 random walk 구현.

### 구현 상세

#### 2-a. sensors 딕셔너리 초기화

```python
self.sensors = {
    'CDS':     {'val': 500, 'min': 0,   'max': 999, 'rate': 10},
    'HALL':    {'val': 500, 'min': 0,   'max': 999, 'rate': 15},
    'TEMP':    {'val': 500, 'min': 0,   'max': 999, 'rate': 5},
    'HUMI_T':  {'val': 500, 'min': 0,   'max': 999, 'rate': 7},
    'HUMI_H':  {'val': 500, 'min': 0,   'max': 999, 'rate': 11},
    'ROT':     {'val': 0,   'min': 0,   'max': 100, 'rate': 0},   # 수동 조작
    'US_DIST': {'val': 500, 'min': 0,   'max': 999, 'rate': 18},
    'IR_RX':   {'val': 0,   'min': 0,   'max': 9,   'rate': 0},   # 버튼 입력
}
```

#### 2-b. update_sensors() — random walk

```python
def update_sensors(self):
    with self.lock:
        for key, s in self.sensors.items():
            if s['rate'] > 0 and key not in ('ROT', 'IR_RX'):
                delta = (random.random() - 0.5) * 2 * s['rate'] / 600
                s['val'] = max(s['min'], min(s['max'], s['val'] + delta))
```

**변화율 공식**: `분당 rate / 600틱(10Hz×60초) = 1틱당 변화량`
- `random.random()`은 0~1, `-0.5`로 -0.5~+0.5, `×2` = -1~+1 범위 보정
- 예: `rate=10` → 1틱당 최대 ±0.0167, 분당 최대 ±10

#### 2-c. get_status_line() — 센서 값을 S 패킷으로

```python
def get_status_line(self):
    with self.lock:
        return "S," + ",".join([
            f"CDS={self.sensors['CDS']['val']:.0f}",
            f"HALL={self.sensors['HALL']['val']:.0f}",
            ...
        ])
```

### 검증
```python
# 엔진만 생성해서 100틱(10초) 후 값 변화 확인
engine = SimulatorEngine()
for _ in range(100):
    engine.update_sensors()
    print(engine.get_status_line())
    time.sleep(0.1)
# → CDS, HALL 등이 500 부근에서 ±랜덤하게 움직이는지 확인
# → ROT는 항상 0, IR_RX는 항상 0
```

---

## Stage 3 — 조이스틱 패턴 시뮬레이션

### 목표
JOY_X(중앙 500, ±7), JOY_Y(중앙 500, ±11)의 5-step-up/5-step-down 왕복 패턴.

### 구현 상세

```python
# 초기화
self.joy = {'x': 500, 'y': 500}
self.joy_dir_x = 1
self.joy_dir_y = 1
self.joy_count_x = 0
self.joy_count_y = 0
self.joy_step_x = 7
self.joy_step_y = 11
self.joy_cycles_x = 5
self.joy_cycles_y = 5
```

#### update_sensors()에 추가

```python
def update_sensors(self):
    with self.lock:
        # 1. random walk (Stage 2 코드)
        ...
        # 2. 조이스틱
        if self.joy_count_x < self.joy_cycles_x:
            self.joy['x'] += self.joy_step_x * self.joy_dir_x
            self.joy_count_x += 1
        else:
            self.joy_dir_x *= -1
            self.joy_count_x = 0
            self.joy['x'] += self.joy_step_x * self.joy_dir_x
            self.joy_count_x += 1
        # Y도 동일 패턴 (step=11, cycles=5)
        ...
        self.joy['x'] = max(0, min(999, self.joy['x']))
        self.joy['y'] = max(0, min(999, self.joy['y']))
```

**패턴 설명**:
- 10Hz = 100ms/틱
- 5회 증가(500→535 for X) → 방향 반전 → 5회 감소(535→500)
- 총 10틱 = 1초 주기, 분당 60사이클 왕복

### 검증
```python
engine = SimulatorEngine()
last_x = -1
for _ in range(20):
    engine.update_sensors()
    line = engine.get_status_line()
    # JOY_X=값 확인
    print(line.split(',')[7])  # JOY_X=
    time.sleep(0.1)
# → 500, 507, 514, 521, 528, 535, 528, 521, 514, 507, 500, ...
```

---

## Stage 4 — GPS 궤적 시뮬레이션

### 목표
사용자 설정 중심점 기준 반경 0.001° 원형 궤도, 1분 1바퀴.

### 구현 상세

```python
# 초기화
self.gps_center_lat = 37.5600
self.gps_center_lng = 127.0000
self.gps_radius = 0.001
self.gps_theta = 0.0
self.gps_speed = 2 * math.pi / 600   # 600틱(10Hz×60초) = 1회전
```

#### update_sensors()에 추가

```python
self.gps_theta += self.gps_speed
if self.gps_theta > 2 * math.pi:
    self.gps_theta -= 2 * math.pi
```

#### get_status_line()에 GPS 추가

```python
lat = self.gps_center_lat + self.gps_radius * math.cos(self.gps_theta)
lng = self.gps_center_lng + self.gps_radius * math.sin(self.gps_theta)
# f"GPS_LAT={lat:.4f}, GPS_LNG={lng:.4f}"
```

### 검증
```python
engine = SimulatorEngine()
for _ in range(1200):  # 120초
    engine.update_sensors()
    if _ % 100 == 0:
        print(engine.get_status_line().split(',')[11:13])
        # GPS_LAT, GPS_LNG 값이 원형으로 변하는지 확인
# → 60초 후 (600틱) 같은 위치로 돌아오는지 확인
```

---

## Stage 5 — FUEL / ACC / RPM 시뮬레이션

### 목표
- FUEL: 10Hz마다 감소 (주행 -1, 정차 -0.1), refill 시 1000
- ACC_X/Y/Z: ±진동 + ACC_Z 980 기준
- RPM: 550 기준 ±랜덤

### 구현 상세

```python
# 초기화
self.fuel = 1000
self.fuel_driving = True  # True=주행, False=정차
self.acc_x = 0.0
self.acc_y = 5.0
self.acc_z = 980.0
self.rpm = 550
```

#### update_sensors()에 추가

```python
# 연료
if self.fuel > 0:
    self.fuel -= 0.1 if not self.fuel_driving else 1.0
    self.fuel = max(0, self.fuel)

# 가속도 (랜덤 진동)
self.acc_x = (random.random() - 0.5) * 20
self.acc_y = (random.random() - 0.5) * 20
self.acc_z = 980 + (random.random() - 0.5) * 10

# RPM
self.rpm = max(0, min(999, self.rpm + (random.random() - 0.5) * 20))
```

### 검증
```python
engine = SimulatorEngine()
engine.fuel_driving = True
for i in range(100):
    engine.update_sensors()
    if i % 10 == 0:
        line = engine.get_status_line()
        # FUEL= 값이 1000에서 1씩 감소하는지 확인
        print(line.split(',')[12])  # FUEL=
# → 100틱 후 FUEL ≈ 900 (1000 - 100×1)
```

---

## Stage 6 — 명령 처리 엔진 (Actuator)

### 목표
RPi로부터 `C,WHEEL1=500,CLCD=Hello,...` 명령 수신 시:
1. 각 키를 파싱하고 값 검증
2. `engine.act` 업데이트
3. `R,OK` 또는 `R,ERR=...` 응답 반환

### 액추에이터 키 목록

| 키 | 타입 | 범위 | 검증 |
|----|------|------|------|
| WHEEL1~4 | int | 0~999 | 범위 초과 시 ERR |
| SERVO1~2 | int | 0~999 | 동일 |
| CLCD | str | ~32자 | trim만, ERR 없음 |
| LED_G, LED_B | int | 0~999 | 범위 초과 시 ERR |
| LED_RGB_R/G/B | int | 0~999 | 동일 |
| BUZZER | int | 0,1 | 0/1 아닐 시 ERR |
| LASER | int | 0,1 | 동일 |
| IR_TX | int | 1~9 | 범위 초과 시 ERR |
| 기타 키 | - | - | `Unknown key` ERR |

### 구현 상세

```python
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
        if k in ('WHEEL1','WHEEL2','WHEEL3','WHEEL4'):
            try:
                val = int(v)
                if 0 <= val <= 999:
                    self.act[k] = val
                else:
                    errors.append(f"{k} out of range (0~999)")
            except ValueError:
                errors.append(f"{k} invalid int")
        elif k in ('SERVO1','SERVO2'):
            # WHEEL과 동일한 0~999 검증
        elif k == 'CLCD':
            self.act['CLCD'] = v[:32]
        elif k in ('LED_G','LED_B'):
            # 0~999 검증
        elif k in ('LED_RGB_R','LED_RGB_G','LED_RGB_B'):
            # 0~999 검증
        elif k == 'BUZZER':
            if v in ('0','1'):
                self.act['BUZZER'] = int(v)
            else:
                errors.append("BUZZER must be 0 or 1")
        elif k == 'LASER':
            if v in ('0','1'):
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
```

### 검증
```python
engine = SimulatorEngine()
tests = [
    ("C,WHEEL1=500", "R,OK"),
    ("C,SERVO1=999", "R,OK"),
    ("C,BUZZER=1", "R,OK"),
    ("C,BUZZER=2", "R,ERR=BUZZER must be 0 or 1"),
    ("C,FAKE_KEY=1", "R,ERR=Unknown key: FAKE_KEY"),
    ("C,WHEEL1=1000", "R,ERR=WHEEL1 out of range (0~999)"),
    ("C,INVALID", None),  # = 없으면 무시
]
for cmd, expected in tests:
    resp = engine.process_command(cmd)
    status = "PASS" if resp == expected else f"FAIL (got {resp})"
    print(f"{status}: {cmd} → {resp}")
```

---

## Stage 7 — Headless 모드 완성

### 목표
시리얼 연결을 통해 실제로 10Hz S 패킷 송신 + C 명령 수신 + R 응답 처리.
GUI 없이 console-only로 시뮬레이터 구동 가능.

### 구현 상세

Stage 1의 main()을 완성:

```python
def main():
    parser = argparse.ArgumentParser(...)
    parser.add_argument('--serial-port', required=True)
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()

    engine = SimulatorEngine()
    comms = CommsHandler(engine, serial_port=args.serial_port, baud=args.baud)

    if args.headless:
        comms.start()
        print(f"[Headless] STM32F103 시뮬레이터")
        print(f"  포트: {args.serial_port} @ {args.baud}bps")
        try:
            while True:
                time.sleep(0.1)
                engine.update_sensors()
                status = engine.get_status_line()
                comms.send_status(status)
        except KeyboardInterrupt:
            print("\n종료")
        finally:
            comms.stop()
```

### 검증
```
# 실제 포트 또는 가상 포트(com0com)로 연결:
# 터미널 1: python simulator_stm32.py --headless --serial-port COM3
# 터미널 2: python -c "import serial; ser=serial.Serial('COM4',115200,timeout=1); [print(ser.readline().decode().strip()) for _ in range(20)]"
# → S,CDS=... 패킷 20개 수신
```

---

## Stage 8 — Tkinter GUI: 연결 바 + 로그 + 명령창

### 목표
- GUI 창 제목: "NUCLEO STM32F103 차량 시뮬레이터 — Serial"
- 상단 연결 바: COM 포트 드롭다운 + 연결/종료 버튼
- 하단 시리얼 로그(ScrolledText) + 수동 명령 Entry + 전송 버튼
- 상태 표시줄: 포트명, TX/RX 카운트

### 구현 상세

```python
class SimulatorGUI:
    COLORS = {
        'bg': '#1e1e2e', 'fg': '#cdd6f4', 'card': '#313244',
        'accent': '#89b4fa', 'green': '#a6e3a1', 'red': '#f38ba8',
    }

    def __init__(self, engine, comms):
        self.engine = engine
        self.comms = comms
        self.comms.set_callback(self.on_comms)
        self._connected = False

        self.root = tk.Tk()
        self.root.title("NUCLEO STM32F103 차량 시뮬레이터 — Serial")
        self.root.geometry("1000x750")
        self.root.configure(bg=self.COLORS['bg'])

        style = ttk.Style()
        style.theme_use('clam')
        # ... style configure ...

        self._build_ui()

        if self.comms.serial_port:
            self.port_combo.set(self.comms.serial_port)

    def _build_ui(self):
        # 상단: 연결 바
        conn_frame = tk.Frame(self.root, bg=self.COLORS['card'])
        conn_frame.pack(fill=tk.X, padx=10, pady=(10,2))
        # COM 포트 Combobox
        # 새로고침 버튼
        # 연결/종료 버튼
        # 상태 레이블

        # 중앙: 빈 프레임 (센서/액추에이터는 9~11 Stage)

        # 하단: 시리얼 로그
        log_frame = tk.LabelFrame(...)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, ...)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 하단: 수동 명령 입력
        cmd_frame = tk.Frame(...)
        self.cmd_entry = tk.Entry(cmd_frame, ...)
        self.cmd_entry.bind('<Return>', lambda e: self._send_manual_cmd())
        tk.Button(cmd_frame, text="명령 전송", command=self._send_manual_cmd, ...)

        # 하단: 상태 표시줄
        status_frame = tk.Frame(...)
        self.status_label = tk.Label(status_frame, text="포트 선택 후 연결하세요 | TX: 0 | RX: 0", ...)

    def _refresh_ports(self):
        ports = scan_serial_ports()
        self.port_combo['values'] = [p['description'] for p in ports]
        if ports and not self.port_combo.get():
            self.port_combo.set(ports[0]['description'])

    def _toggle_connection(self):
        # 연결/종료 토글
        ...

    def _send_manual_cmd(self):
        line = self.cmd_entry.get().strip()
        if line:
            # comms.ser.write() + engine.process_command() + 로그
            ...

    def on_comms(self, tag, msg):
        if tag == 'log':
            self.root.after(0, lambda: self.log(f"[{tag}] {msg}"))
        # ...

    def log(self, msg):
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
```

### 검증
```
python simulator_stm32.py
# → GUI 창 열림
# → COM 포트 드롭다운에 포트 목록 표시되는지 확인
# → "연결" 버튼 클릭 → 상태 변화
# → 로그 창에 메시지 출력
# → 명령 입력창에 "C,WHEEL1=500" 입력 → 로그 출력
```

---

## Stage 9 — GUI: 센서 표시 패널 (10Hz 갱신)

### 목표
좌측 패널에 17개 센서 값을 10Hz(100ms)로 갱신하는 읽기 전용 레이블 배치.

### 구현 상세

```python
def _build_ui(self):
    # ... Stage 8 코드 ...
    top = tk.Frame(self.root, bg=self.COLORS['bg'])
    top.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # 왼쪽: 센서 패널
    sensor_frame = tk.LabelFrame(top, text="센서 (10Hz 자동 전송)", ...)
    sensor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))

    self.sensor_labels = {}
    sensors = [
        ('CDS','CDS 조도'), ('HALL','HALL 홀센서'),
        ('TEMP','TEMP 온도'), ('HUMI_T','HUMI_T 온습도 온도'),
        ('HUMI_H','HUMI_H 온습도 습도'), ('ROT','ROT 로터리'),
        ('US_DIST','US_DIST 초음파'), ('JOY_X','JOY_X 조이스틱 X'),
        ('JOY_Y','JOY_Y 조이스틱 Y'), ('IR_RX','IR_RX 수신'),
        ('GPS_LAT','GPS_LAT 위도'), ('GPS_LNG','GPS_LNG 경도'),
        ('FUEL','FUEL 연료'), ('ACC_X','ACC_X 가속도 X'),
        ('ACC_Y','ACC_Y 가속도 Y'), ('ACC_Z','ACC_Z 가속도 Z'),
        ('RPM','RPM'),
    ]
    for i, (key, label) in enumerate(sensors):
        lbl = tk.Label(sensor_frame, text=f"{label} :", anchor='e', ...)
        lbl.grid(row=i, column=0, sticky='e', padx=5, pady=1)
        val = tk.Label(sensor_frame, text="---", anchor='w', ...)
        val.grid(row=i, column=1, sticky='w', padx=5, pady=1)
        self.sensor_labels[key] = val
```

#### 10Hz 갱신 루프

```python
def _start_10hz_loop(self):
    def loop():
        self.engine.update_sensors()
        display = self.engine.get_sensor_display()
        for key, val_str in display.items():
            if key in self.sensor_labels:
                self.sensor_labels[key].config(text=val_str)

        status_line = self.engine.get_status_line()
        self.comms.send_status(status_line)

        port_display = self.comms.serial_port or "미연결"
        self.status_label.config(
            text=f"{port_display} | 115200bps | 10Hz | TX: {self.comms.tx_count} | RX: {self.comms.rx_count}")

        self.root.after(100, loop)
    self.root.after(100, loop)
```

### 검증
```
python simulator_stm32.py
# → 센서 패널에 17개 값이 10Hz로 실시간 갱신되는지 확인
# → CDS, HALL 등이 랜덤하게 변함
# → GPS_LAT, GPS_LNG가 원형 궤도로 천천히 변화
# → FUEL 감소 확인
```

---

## Stage 10 — GUI: 액추에이터 제어 (스케일/버튼)

### 목표
우측 패널에 액추에이터 제어 UI 배치:
- WHEEL1~4: Scale (0~999), trace로 명령 전송
- SERVO1~2: Scale (0~999 → 0~180°), 각도 표시
- CLCD: Entry + 전송 버튼 + 2행 디스플레이
- LED_G/B: 2색 LED Scale
- LED_RGB_R/G/B: 3색 LED Scale

### 구현 상세

```python
# 오른쪽 액추에이터 패널
act_frame = tk.LabelFrame(top, text="액추에이터 제어 (RPi → STM32)", ...)
act_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5,0))

row = 0

# WHEEL1~4
for i in range(1,5):
    tk.Label(act_frame, text=f"WHEEL{i}", ...).grid(row=row, column=0, ...)
    var = tk.DoubleVar(value=0)
    var.trace_add('write', lambda *a, idx=i: self._on_wheel_change(idx))
    tk.Scale(act_frame, from_=0, to=999, orient=tk.HORIZONTAL,
             variable=var, length=160, ...).grid(row=row, column=1, ...)
    val_lbl = tk.Label(act_frame, text="0", ...)
    val_lbl.grid(row=row, column=2, ...)
    self.wheel_scales[i] = (var, val_lbl)
    row += 1

# SERVO1~2 (동일 패턴, 각도 레이블 추가)
# CLCD (Entry + 전송버튼 + Label 2행)

# 2색 LED G, B (Scale)
# 3색 LED R, G, B (Scale)
```

#### trace_add 콜백 (_updating 플래그 사용)

```python
self._updating = False  # __init__에서 선언

def _on_wheel_change(self, i):
    if self._updating:
        return
    val = int(self.wheel_scales[i][0].get())
    self._send_actuator_cmd(f"C,WHEEL{i}={val}")
```

#### 10Hz 루프에서 _updating 동기화

```python
# _start_10hz_loop() loop() 내부:
self._updating = True
with self.engine.lock:
    for i in range(1,5):
        var, lbl = self.wheel_scales[i]
        val = self.engine.act[f'WHEEL{i}']
        var.set(val)
        lbl.config(text=str(val))
    # SERVO, LED도 동일
self._updating = False
```

**`_updating` 플래그가 필요한 이유**:
10Hz 루프가 `var.set(val)`으로 Scale 위치를 프로그램적으로 변경하면
`trace_add('write')` 콜백이 다시 트리거되어 무한 루프가 발생함.
`_updating` 플래그로 엔진→GUI 동기화 중에는 trace 콜백을 무시.

### CLCD 표시 규칙

```python
def _send_clcd(self):
    text = self.clcd_entry.get()[:32]
    line1 = text[:16] if len(text) >= 16 else text
    line2 = text[16:32] if len(text) > 16 else ''
    self.clcd_display.config(text=f"[{line1:<16}]\n[{line2:<16}]")
    self._send_actuator_cmd(f"C,CLCD={text}")
```

### 검증
```
python simulator_stm32.py
# → WHEEL1 스케일 드래그 → 로그에 "C,WHEEL1=xxx" 전송 확인
# → SERVO1 스케일 드래그 → 각도 레이블이 0~180°로 표시
# → CLCD에 "Hello World!" 입력 → 전송 → 2행 디스플레이 확인
```

---

## Stage 11 — GUI: 고급 제어 (부저/레이저/IR/엔코더/GPS/연료)

### 목표
- BUZZER/LASER: 토글 버튼 (ON/OFF, 색상 변경)
- IR TX: 1~9 버튼 그리드 + 즉시 명령 전송
- IR RX: 0~9 버튼 그리드 + sensors['IR_RX']['val'] 직접 설정
- 로터리 엔코더: Scale (0~100) → sensors['ROT']['val'] 직접 설정
- GPS 중심: 위도/경도 Entry + 적용 버튼
- 연료: "연료 채움" 버튼 + 주행/정차 모드 토글

### 구현 상세

```python
# 부저 토글
def _toggle_buzzer(self):
    new = 0 if self.engine.act['BUZZER'] else 1
    self._send_actuator_cmd(f"C,BUZZER={new}")
    self.buzzer_btn.config(text=f"BUZZER {'ON' if new else 'OFF'}",
                           fg=self.COLORS['green'] if new else self.COLORS['red'])

# IR TX 그리드
for n in range(1, 10):
    tk.Button(ir_frame, text=str(n), width=2,
              command=lambda v=n: self._ir_tx(v), ...).pack(side=tk.LEFT, padx=1)

def _ir_tx(self, val):
    self.engine.act['IR_TX'] = val
    self._send_actuator_cmd(f"C,IR_TX={val}")
    self.log(f"[IR TX] 버튼 {val} 전송")

# IR RX 그리드 (0~9)
for n in range(0, 10):
    tk.Button(ir_rx_frame, text=str(n), width=2,
              command=lambda v=n: self._ir_rx(v), ...).pack(side=tk.LEFT, padx=1)

def _ir_rx(self, val):
    with self.engine.lock:
        self.engine.sensors['IR_RX']['val'] = val
    self.log(f"[IR RX] 수신값 설정: {val}")

# 로터리 엔코더
self.rot_var = tk.DoubleVar(value=0)
tk.Scale(rot_frame, from_=0, to=100, orient=tk.HORIZONTAL,
         variable=self.rot_var, ...).pack()
self.rot_var.trace_add('write', lambda *a: self._update_rotary())

def _update_rotary(self):
    val = int(self.rot_var.get())
    with self.engine.lock:
        self.engine.sensors['ROT']['val'] = val

# GPS 중심 설정
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

# 연료
def _refill_fuel(self):
    with self.engine.lock:
        self.engine.fuel = 1000
    self.log("[FUEL] 연료가 가득 채워졌습니다 (1000)")

def _toggle_fuel_mode(self):
    with self.engine.lock:
        self.engine.fuel_driving = not self.engine.fuel_driving
    self.fuel_mode_btn.config(text=f"모드: {'주행' if mode else '정차'}", ...)
```

### 검증
```
python simulator_stm32.py
# → BUZZER OFF 버튼 클릭 → "C,BUZZER=1" 전송, 버튼이 "BUZZER ON"(초록)으로 변경
# → LASER도 동일
# → IR TX 숫자 5 클릭 → "C,IR_TX=5" 전송
# → IR RX 숫자 3 클릭 → 다음 S 패킷에 IR_RX=3 포함
# → ROT 스케일 움직임 → S 패킷의 ROT 값 변화
# → GPS 위도/경도 "37.56" / "127.0" 입력 후 적용 → GPS_LAT/LNG 변경 확인
# → "연료 채움" 클릭 → FUEL=1000
# → "모드: 주행" 클릭 → "모드: 정차"로 변경, 연료 소모 10배 느려짐
```

---

## Stage 12 — RPi Controller: 연결 + 데이터 수신

### 목표
- `RPiController` 클래스: 시리얼 포트 연결, 읽기 스레드, S 패킷 파싱
- 포트 선택 UI (console), `connect()`, `disconnect()`

### 구현 상세

```python
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
        self.error_count = 0
        self.log_buffer = []

    def connect(self, port=None):
        if port:
            self.serial_port = port
        try:
            import serial
            self.ser = serial.Serial(self.serial_port, self.baud, timeout=1)
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            return True
        except Exception as e:
            print(f"[ERROR] 연결 실패: {e}")
            return False

    def _read_loop(self):
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
            except:
                time.sleep(0.1)

    def _process_line(self, line):
        if not line:
            return
        with self.lock:
            self.packet_count += 1
        if line.startswith('S,'):
            parts = line[2:].split(',')
            data = {}
            for p in parts:
                if '=' in p:
                    k, v = p.split('=', 1)
                    data[k] = v
            with self.lock:
                self.latest = data
        elif line.startswith('R,'):
            self.add_log(f"[RX] {line}")

    def send_cmd(self, cmd_str):
        full = cmd_str if cmd_str.startswith('C,') else f"C,{cmd_str}"
        self.ser.write((full + '\n').encode())
        self.add_log(f"[TX] {full}")
```

### 포트 선택 (main)

```python
def main():
    port = args.serial_port
    if not port:
        ports = scan_serial_ports()
        if not ports:
            print("사용 가능한 COM 포트가 없습니다")
            return
        for i, p in enumerate(ports):
            print(f"  [{i}] {p}")
        sel = int(input("선택: "))
        port = ports[sel].split(' ')[0]

    ctrl = RPiController(serial_port=port, baud=115200)
    ctrl.connect()
    time.sleep(0.5)
    # 이후 run_interactive() 또는 auto_test()
```

### 검증
```
# 터미널 1: python simulator_stm32.py            # COM3 (가상)
# 터미널 2: python rpi_controller.py --serial-port COM4
# → "[TX]" 없이 S 패킷 10Hz 수신 확인
# → log_buffer에 최근 50개 로그 유지 확인
```

---

## Stage 13 — RPi Controller: 인터랙티브 모드

### 목표
- 실시간 센서 데이터 표시 (clear + print, 0.3초 갱신)
- HELP 화면
- 사용자 명령 입력 → `C,` 접두사 자동 추가 + 전송
- `q`/`quit`/`exit` → 종료

### 구현 상세

```python
def run_interactive(self):
    self._print_help()
    time.sleep(1)

    disp_thread = threading.Thread(target=self._display_loop, daemon=True)
    disp_thread.start()

    try:
        while self.running:
            raw = input().strip()
            if not raw:
                continue
            cmd = raw.lower()
            if cmd in ('q', 'quit', 'exit'):
                break
            elif cmd == 'help':
                self._print_help()
            elif cmd == 'test':
                self.auto_test()
                input("Enter 키를 누르면 계속...")
            elif cmd in ('cls', 'clear'):
                os.system('cls' if sys.platform == 'win32' else 'clear')
            else:
                self.send_cmd(raw)
    except (EOFError, KeyboardInterrupt):
        pass
    self.disconnect()

def _display_loop(self):
    while self.running:
        self._render_display()
        time.sleep(0.3)

def _render_display(self):
    os.system('cls' if sys.platform == 'win32' else 'clear')
    with self.lock:
        data = dict(self.latest)
        pkt = self.packet_count
        logs = list(self.log_buffer)

    print(f" RPi Controller — STM32F103")
    print(f" {self.serial_port} @ {self.baud}bps | 수신: {pkt} 패킷")
    print("─" * 58)

    if data:
        print(f"  CDS={data.get('CDS','---')}  HALL={data.get('HALL','---')}  ...")
    else:
        print("  센서 데이터 대기 중...")

    print("─" * 58)
    print("  로그:")
    for log in logs[-6:]:
        print(f"    {log}")
    print("─" * 58)
    print("  명령=WHEEL1=500  test=자동테스트  help=도움말  q=종료")
```

### 검증
```
# 터미널 1: python simulator_stm32.py            # COM3 (가상)
# 터미널 2: python rpi_controller.py --serial-port COM4
# → 디스플레이에 센서 17개 값 실시간 갱신
# → "WHEEL1=500" 입력 → 로그에 [TX] C,WHEEL1=500 표시
# → "help" → 도움말 출력
# → "q" → 종료
```

---

## Stage 14 — RPi Controller: 자동 테스트 스위트

### 목표
26개 테스트 항목을 순차 실행하여 각 명령의 응답(R,OK / R,ERR)을 검증.

### 테스트 항목

| # | 명령 | 예상 | 설명 |
|---|------|------|------|
| 1~5 | WHEEL1~4 각종값 | R,OK | 정상 범위 바퀴 제어 |
| 6~9 | SERVO1~2 각종값 | R,OK | 정상 범위 서보 제어 |
| 10~11 | CLCD=Hello, CLCD=Line1\nLine2 | R,OK | CLCD 출력 |
| 12~16 | LED_G/B, LED_RGB_R/G/B | R,OK | LED 제어 |
| 17~20 | BUZZER 1/0, LASER 1/0 | R,OK | 부저/레이저 ON/OFF |
| 21~22 | IR_TX=5, IR_TX=9 | R,OK | IR 송신 |
| 23 | WHEEL1=1000 | R,ERR | 범위 초과 오류 |
| 24 | SERVO3=500 | R,ERR | 존재하지 않는 키 |
| 25 | BUZZER=2 | R,ERR | 잘못된 값 |
| 26 | INVALID_KEY=1 | R,ERR | 알 수 없는 키 |

### 구현 상세

```python
def auto_test(self):
    tests = [
        ("WHEEL1=500", "바퀴1 속도 설정"),
        ...
    ]
    error_tests = [
        ("WHEEL1=1000", "범위 초과"),
        ...
    ]

    passed = 0
    failed = 0

    for cmd, desc in tests:
        print(f"\n[TEST] {desc} ({cmd})")
        self.send_cmd(cmd)
        time.sleep(0.3)
        found_ok = False
        for _ in range(10):  # 최대 1초 대기
            with self.lock:
                for log in reversed(self.log_buffer):
                    if '[RX] R,OK' in log:
                        found_ok = True
                        break
            if found_ok:
                break
            time.sleep(0.1)
        if found_ok:
            print(f"  ✓ PASS")
            passed += 1
        else:
            print(f"  ✗ FAIL (R,OK 없음)")
            failed += 1

    for cmd, desc in error_tests:
        print(f"\n[TEST] {desc} ({cmd})")
        self.send_cmd(cmd)
        time.sleep(0.3)
        found_err = False
        for _ in range(10):
            with self.lock:
                for log in reversed(self.log_buffer):
                    if '[RX] R,ERR' in log:
                        found_err = True
                        break
            if found_err:
                break
            time.sleep(0.1)
        if found_err:
            print(f"  ✓ PASS (ERR 수신)")
            passed += 1
        else:
            print(f"  ✗ FAIL (R,ERR 없음)")
            failed += 1

    print(f"\n결과: {passed} 통과, {failed} 실패")
    return failed == 0
```

### 검증
```
python rpi_controller.py --serial-port COM4 --auto-test
# → 26개 테스트 순차 실행
# → 26/26 통과 (100%)
# → 오류 테스트에서 R,ERR 메시지 내용도 확인
```

---

## Stage 15 — 최종 통합 및 종단간 검증

### 목표
가상 시리얼 포트(com0com/socat)를 사용하여 시뮬레이터 ↔ 컨트롤러를
실제로 연결하고 전체 26개 자동 테스트를 통과.

### Windows (com0com)

```bash
# 1. com0com 설치 후 Setup Command Prompt에서:
install portname=COM3 portname=COM4

# 2. 터미널 1 — 시뮬레이터 (GUI)
python simulator_stm32.py --serial-port COM3

# 3. 터미널 2 — 컨트롤러 (자동 테스트)
python rpi_controller.py --serial-port COM4 --auto-test
```

### Linux (socat)

```bash
# 1. 가상 시리얼 페어 생성
socat -d -d PTY,link=/tmp/ttyV0,raw,echo=0 PTY,link=/tmp/ttyV1,raw,echo=0 &

# 2. 터미널 1 — 시뮬레이터 (헤드리스)
python simulator_stm32.py --headless --serial-port /tmp/ttyV0

# 3. 터미널 2 — 컨트롤러 (자동 테스트)
python rpi_controller.py --serial-port /tmp/ttyV1 --auto-test
```

### 최종 검증 체크리스트

- [ ] Stage 1~11: `simulator_stm32.py` 전체 876줄 문법 통과
- [ ] Stage 12~14: `rpi_controller.py` 전체 428줄 문법 통과
- [ ] 10Hz S 패킷 수신: `tail -f` 또는 컨트롤러로 10초간 100±5 패킷 확인
- [ ] 26개 자동 테스트: 26/26 통과
  - 22개 정상 명령 → R,OK
  - 4개 오류 명령 → R,ERR=...
- [ ] GUI 센서 패널: 17개 레이블 10Hz 갱신
- [ ] GUI 액추에이터: WHEEL/SERVO/LED Scale → C 명령 전송
- [ ] GUI 부저/레이저 버튼: 토글 + 명령 전송
- [ ] GUI IR TX/RX: 버튼 그리드 동작
- [ ] GUI GPS 중심 설정: 적용 버튼 후 좌표 변화
- [ ] GUI 연료 채움/모드: 연료 1000 리필 + 주행/정차 전환
- [ ] GUI 로터리 엔코더: ROT 값 변화
- [ ] GUI 연결 해제 후 재연결: 정상 동작
- [ ] --headless 모드: console-only 10Hz 전송
- [ ] ICD 문서: 385줄, 프로토콜/핀맵/시뮬레이터/컨트롤러/테스트 정확성

### 알려진 이슈

| 이슈 | 원인 | 해결 |
|------|------|------|
| GUI Scale 무한루프 | `trace_add('write')` + `var.set()` 충돌 | `_updating` 플래그 |
| Windows COM 포트 스캔 느림 | socket.connect() 256회 시도 | pyserial 설치 권장 |
| 컨트롤러 Windows 입력 | `input()` blocking | 별도 display thread로 우회 |
| HEARTBEAT 없음 | ICD에 미정의 | 추후 `H` 패킷 추가 가능 |

---

## 최종 파일 구조

```
1-2/
├── ICD_SIMULATOR.md          # 385줄 — 통신 명세 + 전체 설명
├── SIMULATOR_DEV_GUIDE.md    # ← 본 문서
├── simulator_stm32.py        # 876줄 — STM32F103 차량 시뮬레이터
│                             #   SimulatorEngine     (1~6)
│                             #   CommsHandler        (1~7)
│                             #   SimulatorGUI        (8~11)
│                             #   main()              (1, 7)
├── rpi_controller.py         # 428줄 — RPi 컨트롤러 검증 도구
│                             #   RPiController       (12~14)
│                             #   main()              (12)
├── README.md                 # 기존 하드웨어 조립 문서
└── 1-2-F*.png                # 기존 이미지
```
