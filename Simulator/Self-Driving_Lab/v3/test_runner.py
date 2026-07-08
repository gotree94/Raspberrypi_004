"""
test_runner.py — 4-DOF 자동화 시스템 Full Function Test Runner (v3)

v3 특징:
  - 장비 시뮬레이터를 자동 실행 (별도 수동 실행 불필요)
  - TCP readiness 폴링 후 자동 테스트 진행
  - 종료 시 실행된 프로세스 자동 정리

사용법:
    python test_runner.py              # 장비 자동 실행 → 전체 통합 테스트 (T1~T6)
    python test_runner.py --auto       # 대기 없이 자동 실행
    python test_runner.py --unit       # 개별 장비 단위 테스트 (T7)
    python test_runner.py T3           # 특정 테스트만 실행
    python test_runner.py T3 --auto    # 장비 실행 후 T3만 실행
    python test_runner.py --list       # 테스트 목록 출력
"""
import sys
import json
import socket
import time
import os
import subprocess
import atexit
import signal

HOST = '127.0.0.1'

DEVICES = [
    {"name": "Plate Hotel",      "file": "plate_hotel.py",    "port": 50052},
    {"name": "Liquid Handler",   "file": "liquid_handler.py", "port": 50051},
    {"name": "Centrifuge",       "file": "centrifuge.py",     "port": 50054},
    {"name": "Plate Reader",     "file": "plate_reader.py",   "port": 50053},
]

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⏭️ SKIP"

_processes = []


def tcp_send(port, message, timeout=10):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((HOST, port))
        s.sendall(message.encode('utf-8'))
        resp = s.recv(1024).decode('utf-8')
        s.close()
        return resp
    except socket.timeout:
        return None
    except ConnectionRefusedError:
        return None


def launch_devices():
    print(f"\n{'='*60}")
    print("장비 시뮬레이터 자동 실행")
    print(f"{'='*60}")

    for dev in DEVICES:
        script = dev['file']
        if not os.path.exists(script):
            print(f"  {FAIL} {script} 파일을 찾을 수 없습니다.")
            continue
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        _processes.append(proc)
        print(f"  🚀 {dev['name']} (PID {proc.pid}) — {script}")

    if _processes:
        print(f"\n  장비 {len(_processes)}개 실행 중. 연결 대기 중...")
    else:
        print(f"\n  {FAIL} 실행된 장비가 없습니다.")


def wait_for_devices(timeout=30):
    remaining = list(DEVICES)
    for elapsed in range(timeout):
        still_waiting = []
        for dev in remaining:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            try:
                s.connect((HOST, dev['port']))
                s.close()
                print(f"  {PASS} {dev['name']} (Port {dev['port']}) — 연결 성공 ({elapsed + 1}s)")
            except:
                still_waiting.append(dev)
            finally:
                try: s.close()
                except: pass
        remaining = still_waiting
        if not remaining:
            print(f"\n  모든 장비 연결 완료 ({elapsed + 1}초 소요)")
            return True
        if elapsed < timeout - 1:
            time.sleep(1)
    for dev in remaining:
        print(f"  {FAIL} {dev['name']} (Port {dev['port']}) — {timeout}초 내 연결 실패")
    return False


def terminate_devices():
    global _processes
    if not _processes:
        return
    print(f"\n  장비 프로세스 정리 중...")
    alive = 0
    for proc in _processes:
        if proc.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.kill(proc.pid, signal.SIGTERM)
                alive += 1
            except:
                pass
    if alive:
        time.sleep(0.5)
    _processes = [p for p in _processes if p.poll() is None]
    if _processes:
        print(f"  ⚠️  {len(_processes)}개 프로세스가 종료되지 않았습니다.")
    else:
        print(f"  ✅ 모든 장비 프로세스 종료 완료")


atexit.register(terminate_devices)


def check_device_alive(port, name):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((HOST, port))
        s.close()
        return True
    except Exception:
        return False


def ensure_devices_running():
    for dev in DEVICES:
        if not check_device_alive(dev['port'], dev['name']):
            print(f"  {FAIL} {dev['name']} (Port {dev['port']}) — 연결 불가")
            print(f"  → python test_runner.py --auto 로 자동 실행하세요.")
            return False
    return True


def test_plate_hotel_unit():
    print("\n--- [T7.1] Plate Hotel Unit Test ---")
    tests = [
        ("EJECT:1",  "정상 Eject Slot 1",      "SUCCESS"),
        ("EJECT:4",  "정상 Eject Slot 4",      "SUCCESS"),
        ("EJECT:0",  "범위 이탈 Slot 0",       None),
        ("EJECT:5",  "범위 이탈 Slot 5",       None),
        ("EJECT",    "파라미터 누락",            None),
    ]
    for cmd, desc, expected in tests:
        resp = tcp_send(50052, cmd)
        if expected:
            ok = resp and expected in resp
        else:
            ok = resp is None or "ERROR" in resp.upper()
        status = PASS if ok else FAIL
        print(f"  {status} {desc}: cmd='{cmd}' → resp='{resp}'")


def test_liquid_handler_unit():
    print("\n--- [T7.2] Liquid Handler Unit Test ---")
    tests = [
        ("DISPENSE:50",   "정상 분주 50 µL",    "DISPENSE_SUCCESS"),
        ("DISPENSE:300",  "최대 분주 300 µL",   "DISPENSE_SUCCESS"),
        ("DISPENSE:1",    "최소 분주 1 µL",     "DISPENSE_SUCCESS"),
        ("DISPENSE:0",    "0 µL 분주(no-op)",   "DISPENSE_SUCCESS"),
        ("DISPENSE:-10",  "음수 값",            None),
    ]
    for cmd, desc, expected in tests:
        resp = tcp_send(50051, cmd, timeout=15)
        if expected:
            ok = resp and expected in resp
        else:
            ok = resp is None or "ERROR" in resp.upper()
        status = PASS if ok else FAIL
        print(f"  {status} {desc}: cmd='{cmd}' → resp='{resp}'")


def test_centrifuge_unit():
    print("\n--- [T7.3] Centrifuge Unit Test ---")
    tests = [
        ("SPIN:2000",   "정상 Spin 2000 RPM",   "SPIN_SUCCESS"),
        ("SPIN:14000",  "최대 Spin 14000 RPM",  "SPIN_SUCCESS"),
        ("SPIN:1000",   "저속 1000 RPM",        "SPIN_SUCCESS"),
        ("SPIN:0",      "0 RPM",                "SPIN_SUCCESS"),
    ]
    for cmd, desc, expected in tests:
        resp = tcp_send(50054, cmd, timeout=15)
        if expected:
            ok = resp and expected in resp
        else:
            ok = resp is None
        status = PASS if ok else FAIL
        print(f"  {status} {desc}: cmd='{cmd}' → resp='{resp}'")


def test_plate_reader_unit():
    print("\n--- [T7.4] Plate Reader Unit Test ---")
    tests = [
        ("SCAN:2000", "정상 Scan 2000 RPM",  lambda r: r and 0.4 < float(r) < 0.8),
        ("SCAN:4000", "고RPM Scan 4000 RPM", lambda r: r and 0.8 < float(r) < 1.2),
        ("SCAN:1000", "저RPM Scan 1000 RPM", lambda r: r and 0.1 < float(r) < 0.4),
    ]
    for cmd, desc, validator in tests:
        resp = tcp_send(50053, cmd, timeout=30)
        try:
            ok = validator(resp)
        except:
            ok = False
        status = PASS if ok else FAIL
        print(f"  {status} {desc}: cmd='{cmd}' → resp='{resp}'")


def run_closed_loop_plan(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    print(f"\n{'='*60}")
    print(f"실행: {plan['experiment_name']}")
    print(f"설명: {plan.get('description', '')}")
    print(f"목표: {plan['target']['value']} ±{plan['target']['tolerance']}")
    print(f"초기 RPM: {plan.get('initial_rpm', 2000)} / 최대 반복: {plan.get('max_iterations', 5)}")
    print(f"{'='*60}")

    target = plan['target']['value']
    tolerance = plan['target']['tolerance']
    current_rpm = plan.get('initial_rpm', 2000)
    max_iterations = plan.get('max_iterations', 5)
    seq = plan['sequence']

    for iteration in range(1, max_iterations + 1):
        print(f"\n🔄 [Cycle {iteration}] RPM={current_rpm}")

        for step in seq:
            dev = step['device']
            port = step['port']
            if dev in ("centrifuge", "plate_reader"):
                cmd = f"{step['cmd'].split(':')[0]}:{current_rpm}"
            else:
                cmd = step['cmd']

            print(f"  → {dev}: {cmd}")
            resp = tcp_send(port, cmd, timeout=30)
            if resp is None:
                print(f"  {FAIL} {dev} 응답 없음")
                return False
            print(f"  ← {resp}")

        scan_cmd = f"SCAN:{current_rpm}"
        resp = tcp_send(seq[3]['port'], scan_cmd, timeout=30)
        if resp is None:
            print(f"  {FAIL} Plate Reader 응답 없음")
            return False

        try:
            result_val = float(resp)
        except ValueError:
            print(f"  {FAIL} Plate Reader 응답 변환 실패: '{resp}'")
            return False

        error = result_val - target
        print(f"  📊 측정: {result_val:.4f} / 오차: {error:.4f} / 목표: {target}")

        if abs(error) <= tolerance:
            print(f"  {PASS} 수렴! 최적 RPM = {current_rpm}")
            return True
        else:
            if error < 0:
                adjustment = 500
                current_rpm = min(current_rpm + adjustment, 4000)
            else:
                adjustment = 400
                current_rpm = max(current_rpm - adjustment, 1000)
            print(f"  ↻ RPM 조정: {current_rpm} (오차 방향: {'+' if error < 0 else '-'})")
            time.sleep(1)

    print(f"\n{FAIL} 최대 반복 횟수({max_iterations}) 초과. 수렴 실패.")
    return False


def list_tests():
    print("\n사용 가능한 테스트:")
    print("  T1 — 정상 Closed-Loop (test_plan_01_normal.json)")
    print("  T2 — 고흡광도 목표 (test_plan_02_high_target.json)")
    print("  T3 — 저흡광도 목표 (test_plan_03_low_target.json)")
    print("  T4 — Tight Tolerance (test_plan_04_tight.json)")
    print("  T5 — 슬롯/볼륨 변경 (test_plan_05_slot_volume.json)")
    print("  T6 — 극한값 스트레스 (test_plan_06_stress.json)")
    print("  T7 — 개별 장비 단위 테스트 (--unit)")
    print("\n실행 예: python test_runner.py T3")
    print("         python test_runner.py --auto  # 장비 자동 실행 + 전체 테스트")


def main():
    auto_mode = "--auto" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--auto"]

    if "--list" in args:
        list_tests()
        return

    if "--unit" in args:
        print("=" * 60)
        print("T7 — 개별 장비 단위 테스트")
        print("=" * 60)
        if auto_mode or "--launch" in args:
            launch_devices()
            wait_for_devices()
        elif not ensure_devices_running():
            sys.exit(1)
        test_plate_hotel_unit()
        test_liquid_handler_unit()
        test_centrifuge_unit()
        test_plate_reader_unit()
        return

    test_plan_map = {
        "T1": "test_plan_01_normal.json",
        "T2": "test_plan_02_high_target.json",
        "T3": "test_plan_03_low_target.json",
        "T4": "test_plan_04_tight.json",
        "T5": "test_plan_05_slot_volume.json",
        "T6": "test_plan_06_stress.json",
    }

    specific = [a for a in args if a in test_plan_map]

    if auto_mode:
        launch_devices()
        if not wait_for_devices():
            print(f"\n{FAIL} 장비 연결 실패로 테스트를 중단합니다.")
            sys.exit(1)
    else:
        if not ensure_devices_running():
            print(f"\n  --auto 옵션을 사용하면 장비를 자동 실행합니다.")
            sys.exit(1)

    if specific:
        for tid in specific:
            path = test_plan_map[tid]
            if os.path.exists(path):
                print(f"\n{'='*60}")
                print(f"시작: {tid}")
                print(f"{'='*60}")
                run_closed_loop_plan(path)
            else:
                print(f"{FAIL} 파일 없음: {path}")
    else:
        print("=" * 60)
        print("통합 Closed-Loop 테스트 (T1 ~ T6)")
        print("=" * 60)
        results = []
        for tid, path in sorted(test_plan_map.items()):
            if os.path.exists(path):
                ok = run_closed_loop_plan(path)
                results.append((tid, ok))
                time.sleep(2)

        print(f"\n{'='*60}")
        print("통합 테스트 결과 요약")
        print(f"{'='*60}")
        for tid, ok in results:
            print(f"  {PASS if ok else FAIL} {tid}")


if __name__ == "__main__":
    try:
        main()
    finally:
        if _processes:
            terminate_devices()
