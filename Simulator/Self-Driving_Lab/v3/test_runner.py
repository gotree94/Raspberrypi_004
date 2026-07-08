"""
test_runner.py — 4-DOF 자동화 시스템 Full Function Test Runner

사용법:
    python test_runner.py           # 전체 통합 테스트 (T1~T6 순차 실행)
    python test_runner.py --unit    # 개별 장비 단위 테스트 (T7)
    python test_runner.py T3        # 특정 테스트만 실행
    python test_runner.py --list    # 테스트 목록 출력
"""
import sys
import json
import socket
import time
import os

HOST = '127.0.0.1'
DEVICE_PORTS = {
    "plate_hotel": 50052,
    "liquid_handler": 50051,
    "centrifuge": 50054,
    "plate_reader": 50053
}

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⏭️ SKIP"


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


def check_device_alive(port, name):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((HOST, port))
        s.close()
        print(f"  {PASS} {name} (Port {port}) — 연결 가능")
        return True
    except Exception:
        print(f"  {FAIL} {name} (Port {port}) — 연결 실패! 장비가 실행 중인지 확인하세요.")
        return False


def test_plate_hotel_unit():
    print("\n--- [T7.1] Plate Hotel Unit Test ---")
    if not check_device_alive(50052, "Plate Hotel"):
        return

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
    if not check_device_alive(50051, "Liquid Handler"):
        return

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
    if not check_device_alive(50054, "Centrifuge"):
        return

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
    if not check_device_alive(50053, "Plate Reader"):
        return

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
                cmd = step['cmd'].split(':')[0] + f":{current_rpm}"
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


def main():
    if "--list" in sys.argv:
        list_tests()
        return

    if "--unit" in sys.argv:
        print("=" * 60)
        print("T7 — 개별 장비 단위 테스트")
        print("=" * 60)
        print("\n⚠️  모든 장비가 실행 중이어야 합니다.")
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

    specific = [a for a in sys.argv[1:] if a in test_plan_map]
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
        return

    print("=" * 60)
    print("통합 Closed-Loop 테스트 (T1 ~ T6)")
    print("=" * 60)
    print("⚠️  모든 장비(orchestrator 제외)가 실행 중이어야 합니다.\n")
    input("엔터를 누르면 테스트를 시작합니다...")

    for tid, path in sorted(test_plan_map.items()):
        if os.path.exists(path):
            run_closed_loop_plan(path)
            time.sleep(2)

    print("\n" + "=" * 60)
    print("통합 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
