#!/usr/bin/env python3
"""
Raspberry Pi 4 컨트롤러 — STM32F103 시뮬레이터 검증 도구
시리얼 포트로 연결하여 10Hz 데이터 수신 및 명령 전송

사용법:
    python rpi_controller.py                           # 포트 선택 후 연결
    python rpi_controller.py --serial-port COM3        # COM3 직접 연결
    python rpi_controller.py --serial-port COM3 --auto-test  # 자동 테스트
"""

import threading
import time
import sys
import argparse
import os

# ============================================================
# ANSI 색상
# ============================================================
class Color:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    CLR = '\033[2J\033[H'

    @staticmethod
    def ok(s): return f"{Color.GREEN}{s}{Color.RESET}"
    @staticmethod
    def err(s): return f"{Color.RED}{s}{Color.RESET}"
    @staticmethod
    def info(s): return f"{Color.CYAN}{s}{Color.RESET}"
    @staticmethod
    def hl(s): return f"{Color.YELLOW}{s}{Color.RESET}"


# ============================================================
# 포트 스캐너 (시뮬레이터 모듈 재사용)
# ============================================================
def scan_serial_ports():
    import glob, socket
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
            p = f'COM{i}'
            try:
                s = socket.socket()
                s.connect((p, 0))
                s.close()
                ports.append(p)
            except:
                pass
    else:
        for pat in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyAMA*', '/dev/ttyS*']:
            for path in glob.glob(pat):
                if os.path.exists(path):
                    ports.append(path)
    return ports


# ============================================================
# RPi Controller
# ============================================================
class RPiController:
    def __init__(self, serial_port=None, baud=115200):
        self.serial_port = serial_port
        self.baud = baud
        self.ser = None
        self.running = True
        self._read_thread = None
        self.lock = threading.Lock()

        # 최신 센서 데이터
        self.latest = {}
        self.packet_count = 0
        self.error_count = 0
        self.last_status_time = 0
        self.log_buffer = []
        self.max_log = 50

    # --------------------------------------------------------
    # 연결 관리
    # --------------------------------------------------------
    def connect(self, port=None):
        if port:
            self.serial_port = port
        if not self.serial_port:
            print(Color.err("[ERROR] 포트가 지정되지 않음"))
            return False
        try:
            import serial
            self.ser = serial.Serial(self.serial_port, self.baud, timeout=1)
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            return True
        except ImportError:
            print(Color.err("[ERROR] pyserial 필요: pip install pyserial"))
            return False
        except Exception as e:
            print(Color.err(f"[ERROR] 연결 실패: {e}"))
            return False

    def disconnect(self):
        self.running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except:
                pass
        self.add_log(Color.DIM + "연결 종료" + Color.RESET)

    # --------------------------------------------------------
    # 수신 스레드
    # --------------------------------------------------------
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
            parts = line[2].split(',')
            data = {}
            for p in parts:
                if '=' in p:
                    k, v = p.split('=', 1)
                    data[k] = v
            with self.lock:
                self.latest = data
        elif line.startswith('R,'):
            self.add_log(f"{Color.BLUE}[RX]{Color.RESET} {line}")

    # --------------------------------------------------------
    # 명령 전송
    # --------------------------------------------------------
    def send_cmd(self, cmd_str):
        if not self.ser or not self.ser.is_open:
            self.add_log(Color.err("[ERR] 연결되지 않음"))
            return
        full = cmd_str if cmd_str.startswith('C,') else f"C,{cmd_str}"
        try:
            self.ser.write((full + '\n').encode())
            self.add_log(f"{Color.MAGENTA}[TX]{Color.RESET} {full}")
        except Exception as e:
            self.add_log(Color.err(f"[ERR] 전송 실패: {e}"))

    # --------------------------------------------------------
    # 로그
    # --------------------------------------------------------
    def add_log(self, msg):
        with self.lock:
            self.log_buffer.append(msg)
            if len(self.log_buffer) > self.max_log:
                self.log_buffer = self.log_buffer[-self.max_log:]

    # --------------------------------------------------------
    # 자동 테스트
    # --------------------------------------------------------
    def auto_test(self):
        tests = [
            ("WHEEL1=500", "바퀴1 속도 설정"),
            ("WHEEL2=300", "바퀴2 속도 설정"),
            ("WHEEL3=700", "바퀴3 속도 설정"),
            ("WHEEL4=999", "바퀴4 최고 속도"),
            ("WHEEL1=0", "바퀴1 정지"),
            ("SERVO1=0", "서보1 0도"),
            ("SERVO1=500", "서보1 90도"),
            ("SERVO1=999", "서보1 180도"),
            ("SERVO2=250", "서보2 45도"),
            ("CLCD=Hello World!", "CLCD 1행 출력"),
            ("CLCD=Line1\nLine2", "CLCD 2행 출력"),
            ("LED_G=500", "2색 LED G=500"),
            ("LED_B=800", "2색 LED B=800"),
            ("LED_RGB_R=999", "3색 LED R=999"),
            ("LED_RGB_G=500", "3색 LED G=500"),
            ("LED_RGB_B=200", "3색 LED B=200"),
            ("BUZZER=1", "부저 ON"),
            ("BUZZER=0", "부저 OFF"),
            ("LASER=1", "레이저 ON"),
            ("LASER=0", "레이저 OFF"),
            ("IR_TX=5", "IR 송신 5"),
            ("IR_TX=9", "IR 송신 9"),
        ]
        error_tests = [
            ("WHEEL1=1000", "범위 초과 → ERR"),
            ("SERVO3=500", "없는 키 → ERR"),
            ("BUZZER=2", "잘못된 값 → ERR"),
            ("INVALID_KEY=1", "알 수 없는 키 → ERR"),
        ]

        print(Color.CLR)
        print(Color.BOLD + "═══════════════════════════════════════" + Color.RESET)
        print(Color.BOLD + "  STM32F103 시뮬레이터 자동 테스트" + Color.RESET)
        print(Color.BOLD + "═══════════════════════════════════════" + Color.RESET)
        time.sleep(1)

        passed = 0
        failed = 0

        for cmd, desc in tests:
            print(f"\n{Color.CYAN}[TEST]{Color.RESET} {desc} ({Color.YELLOW}{cmd}{Color.RESET})")
            self.send_cmd(cmd)
            time.sleep(0.3)
            # 응답 대기
            found_ok = False
            for _ in range(10):
                with self.lock:
                    for log in reversed(self.log_buffer):
                        if '[RX] R,OK' in log:
                            found_ok = True
                            break
                if found_ok:
                    break
                time.sleep(0.1)
            if found_ok:
                print(f"  {Color.GREEN}✓ PASS{Color.RESET}")
                passed += 1
            else:
                print(f"  {Color.RED}✗ FAIL (응답 없음){Color.RESET}")
                failed += 1

        print(f"\n{Color.BOLD}--- 오류 테스트 ---{Color.RESET}")
        for cmd, desc in error_tests:
            print(f"\n{Color.CYAN}[TEST]{Color.RESET} {desc} ({Color.YELLOW}{cmd}{Color.RESET})")
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
                print(f"  {Color.GREEN}✓ PASS (ERR 수신){Color.RESET}")
                passed += 1
            else:
                print(f"  {Color.RED}✗ FAIL (ERR 없음){Color.RESET}")
                failed += 1

        print(Color.BOLD + "\n═══════════════════════════════════════" + Color.RESET)
        print(f"  결과: {Color.GREEN}{passed} 통과{Color.RESET}, {Color.RED}{failed} 실패{Color.RESET}")
        print(Color.BOLD + "═══════════════════════════════════════" + Color.RESET)
        return failed == 0

    # --------------------------------------------------------
    # 디스플레이 스레드 (실시간 갱신)
    # --------------------------------------------------------
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
            errs = self.error_count

        conn = f"{self.serial_port or '?'} @ {self.baud}bps"

        print(Color.BOLD + f" RPi Controller — STM32F103 Simulator Test"
              + Color.RESET)
        print(f" {Color.info(conn)}  |  "
              + f"수신: {Color.hl(str(pkt))} 패킷  |  "
              + f"오류: {Color.err(str(errs)) if errs else Color.ok('0')}")
        print(Color.DIM + "─" * 58 + Color.RESET)

        if data:
            def v(k):
                return f"{Color.YELLOW}{data.get(k, '---')}{Color.RESET}"
            print(f"  CDS={v('CDS')}  HALL={v('HALL')}  TEMP={v('TEMP')}  HUMI_T={v('HUMI_T')}")
            print(f"  HUMI_H={v('HUMI_H')}  ROT={v('ROT')}  US_DIST={v('US_DIST')}  JOY_X={v('JOY_X')}")
            print(f"  JOY_Y={v('JOY_Y')}  IR_RX={v('IR_RX')}  GPS_LAT={v('GPS_LAT')}  GPS_LNG={v('GPS_LNG')}")
            print(f"  FUEL={v('FUEL')}  ACC_X={v('ACC_X')}  ACC_Y={v('ACC_Y')}  ACC_Z={v('ACC_Z')}  RPM={v('RPM')}")
        else:
            print(f"  {Color.DIM}센서 데이터 대기 중...{Color.RESET}")

        print(Color.DIM + "─" * 58 + Color.RESET)
        print(f"  {Color.BOLD}로그 (최근):{Color.RESET}")
        for log in logs[-6:]:
            print(f"    {log}")

        print(Color.DIM + "─" * 58 + Color.RESET)
        print(f"  {Color.CYAN}명령{Color.RESET}=WHEEL1=500  "
              + f"{Color.GREEN}test{Color.RESET}=자동테스트  "
              + f"{Color.MAGENTA}help{Color.RESET}=도움말  "
              + f"{Color.RED}q{Color.RESET}=종료")

    # --------------------------------------------------------
    # 메인 루프 (인터랙티브)
    # --------------------------------------------------------
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
                    input(Color.DIM + "Enter 키를 누르면 계속..." + Color.RESET)
                elif cmd == 'cls' or cmd == 'clear':
                    os.system('cls' if sys.platform == 'win32' else 'clear')
                else:
                    self.send_cmd(raw)
        except (EOFError, KeyboardInterrupt):
            pass
        self.disconnect()

    def _print_help(self):
        os.system('cls' if sys.platform == 'win32' else 'clear')
        print(Color.BOLD + """
╔══════════════════════════════════════════════════════════════╗
║  RPi Controller — STM32F103 시뮬레이터 검증 도구            ║
╠══════════════════════════════════════════════════════════════╣
║  명령 입력 (C, 생략 가능):                                   ║
║    WHEEL1=500      바퀴 1~4 PWM (0~999)                    ║
║    SERVO1=500      서보 1~2 각도 (0~999 → 0~180°)          ║
║    CLCD=Hello      CLCD 16x2 출력 (최대 32자)              ║
║    BUZZER=1        부저 ON/OFF (0/1)                       ║
║    LASER=1         레이저 ON/OFF (0/1)                     ║
║    LED_G=500       2색 LED G/B (0~999)                     ║
║    LED_RGB_R=999   3색 LED R/G/B (0~999)                   ║
║    IR_TX=5         IR 송신 (1~9)                           ║
║    test            자동 테스트 (26개 항목)                   ║
║    help            이 도움말                                ║
║    q               종료                                     ║
╚══════════════════════════════════════════════════════════════╝
""" + Color.RESET)


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='RPi Controller — STM32F103 테스트')
    parser.add_argument('--serial-port', default=None, help='시리얼 포트')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--auto-test', action='store_true', help='자동 테스트 모드')
    args = parser.parse_args()

    port = args.serial_port
    if not port:
        ports = scan_serial_ports()
        if not ports:
            print(Color.err("[ERROR] 사용 가능한 COM 포트가 없습니다"))
            return
        print("사용 가능한 포트:")
        for i, p in enumerate(ports):
            print(f"  [{i}] {p}")
        try:
            sel = int(input("선택: "))
            port = ports[sel].split(' ')[0]
        except (ValueError, IndexError):
            print(Color.err("잘못된 선택"))
            return

    ctrl = RPiController(serial_port=port, baud=args.baud)
    if not ctrl.connect():
        return

    time.sleep(0.5)  # 초기 데이터 수신 대기

    if args.auto_test:
        ctrl.auto_test()
        ctrl.disconnect()
        print(Color.DIM + "\n테스트 완료" + Color.RESET)
    else:
        try:
            ctrl.run_interactive()
        except KeyboardInterrupt:
            ctrl.disconnect()
            print("\n종료")


if __name__ == '__main__':
    main()
