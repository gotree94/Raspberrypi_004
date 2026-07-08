# Full Function Test Scenarios — 4-DOF Closed-Loop Automation System

> **목적:** 4대 장비(Plate Hotel · Liquid Handler · Centrifuge · Plate Reader)의
> 모든 기능과 Closed-Loop 최적화 알고리즘을 체계적으로 검증.
>
> **실행:** `test_runner.py` 개별 테스트 / `orchestrator.py` + 각 `test_plan_*.json` 통합 테스트

---

## Test Suite 개요

| Suite ID | 이름 | 난이도 | 소요 시간 | 검증 목표 |
|:---:|---|:---:|:---:|---|
| **T1** | 정상 Closed-Loop | 하 | ~40s | 목표 흡광도 0.8, RPM 자동 수렴 |
| **T2** | 고흡광도 목표 | 중 | ~40s | 목표 1.2(고RPM 필요), 수렴 실패 시나리오 포함 |
| **T3** | 저흡광도 목표 | 중 | ~40s | 목표 0.3(저RPM), RPM 하한(1000) 도달 |
| **T4** | Tight Tolerance | 상 | ~60s | Tolerance ±0.01, 수렴까지 최대 5회 |
| **T5** | 슬롯/볼륨 변경 | 하 | ~40s | 호텔 Slot 1~4, 분주량 10~300 µL |
| **T6** | 극한값 스트레스 | 상 | ~50s | 최대 RPM(4000) + 최대 분주(300µL) |
| **T7** | 개별 장비 단위 테스트 | - | ~20s | 각 장비 개별 명령어 정합성 검증 |

---

## T1 — 정상 Closed-Loop (Normal Operation)

**테스트 파일:** `test_plan_01_normal.json`

| 항목 | 값 |
|---|---|
| 목표 흡광도 | 0.8 |
| Tolerance | ±0.05 |
| 초기 RPM | 2000 |
| 최대 iteration | 5 |
| 호텔 슬롯 | 3 |
| 분주량 | 50 µL |

**예상 결과:** 2~3회 Cycle 내 목표 수렴. 최종 RPM 2500~3000 범위.

**검증 포인트:**
- [ ] 각 장비 TCP 응답 정상 수신
- [ ] 흡광도 오차 점진적 감소
- [ ] RPM 증감 폭(±500/±400) 올바른 방향
- [ ] 수렴 시 루프 조기 종료

---

## T2 — 고흡광도 목표 (High Target — RPM Upper Limit)

**테스트 파일:** `test_plan_02_high_target.json`

| 항목 | 값 |
|---|---|
| 목표 흡광도 | 1.2 |
| Tolerance | ±0.05 |
| 초기 RPM | 2000 |
| 최대 iteration | 5 |

**예상 결과:** RPM이 4000까지 상승하나 흡광도 물리 모델 상한(1.1+noise)에 도달하지 못해 **최대 횟수 초과**.

**검증 포인트:**
- [ ] RPM 4000 도달 시 클램핑 확인 (`min(current + 500, 4000)`)
- [ ] 최대 횟수 초과 시 `[실패]` 메시지 출력
- [ ] 루프 중단 후 상태 READY 복귀

---

## T3 — 저흡광도 목표 (Low Target — RPM Lower Limit)

**테스트 파일:** `test_plan_03_low_target.json`

| 항목 | 값 |
|---|---|
| 목표 흡광도 | 0.3 |
| Tolerance | ±0.05 |
| 초기 RPM | 2000 |
| 최대 iteration | 5 |

**예상 결과:** RPM이 1000까지 감소. 물리 모델상 ~0.275 근처로 수렴 가능.

**검증 포인트:**
- [ ] RPM 1000 도달 시 클램핑 확인 (`max(current - 400, 1000)`)
- [ ] 저RPM에서 Plate Reader 흡광도 0.2~0.3 범위 출력
- [ ] 최종 수렴 또는 최대 횟수 초과 모두 정상 처리

---

## T4 — Tight Tolerance (정밀 수렴)

**테스트 파일:** `test_plan_04_tight.json`

| 항목 | 값 |
|---|---|
| 목표 흡광도 | 0.8 |
| Tolerance | ±0.01 |
| 초기 RPM | 3000 |
| 최대 iteration | 5 |

**예상 결과:** Tolerance가 좁아 5회 내 수렴 실패 가능성 높음.

**검증 포인트:**
- [ ] Tolerance ±0.01로 정밀 제어 시도
- [ ] 흡광도가 목표 근처에서 진동(overshoot)하는 현상 관찰
- [ ] Tight tolerance에서도 시스템 비정상 종료 없음

---

## T5 — 슬롯/볼륨 변경 테스트

**테스트 파일:** `test_plan_05_slot_volume.json`

| 항목 | 값 |
|---|---|
| 목표 흡광도 | 0.8 |
| Tolerance | ±0.05 |
| 호텔 슬롯 | 4 |
| 분주량 | 150 µL |

**예상 결과:** 슬롯 4번 eject + 150 µL 분주 → 더 많은 시약이 흡광도에 영향.

**검증 포인트:**
- [ ] Plate Hotel 4번 슬롯 Eject 명령 전송 및 SUCCESS 수신
- [ ] 150 µL 분주 시뮬레이션 정상 동작
- [ ] 분주량 증가에도 Closed-Loop 알고리즘 정상 작동

---

## T6 — 극한값 스트레스 테스트 (Extreme Values)

**테스트 파일:** `test_plan_06_stress.json`

| 항목 | 값 |
|---|---|
| 목표 흡광도 | 0.7 |
| Tolerance | ±0.05 |
| 초기 RPM | 4000 |
| 호텔 슬롯 | 1 |
| 분주량 | 300 µL |

**예상 결과:** 초기 RPM=4000(최대), 분주량=300 µL(최대)에서도 모든 장비 정상 응답.

**검증 포인트:**
- [ ] Centrifuge 최대 RPM 4000에서 SPIN 정상 동작
- [ ] Liquid Handler 300 µL 분주 정상 처리
- [ ] Plate Hotel Slot 1번 Eject 정상
- [ ] Plate Reader 흡광도 1.0~1.1 범위 스캔 정상

---

## T7 — 개별 장비 단위 테스트

**실행 스크립트:** `test_runner.py --unit`

개별 장비의 TCP 명령어 정합성을 독립적으로 검증.

### 7.1 Plate Hotel 단위 테스트

| 테스트 케이스 | 명령어 | 기대 응답 | 검증 내용 |
|---|---|---|---|
| 정상 Eject Slot 1 | `EJECT:1` | `SUCCESS` | 슬롯 점유 → EMPTY 상태 전환 |
| 정상 Eject Slot 4 | `EJECT:4` | `SUCCESS` | 마지막 슬롯 정상 처리 |
| 범위 이탈 Slot 0 | `EJECT:0` | 오류 | 유효 범위(1~4) 검증 |
| 범위 이탈 Slot 5 | `EJECT:5` | 오류 | 상한 초과 검증 |
| 잘못된 포맷 | `EJECT` | 무시/오류 | 파라미터 누락 처리 |

### 7.2 Liquid Handler 단위 테스트

| 테스트 케이스 | 명령어 | 기대 응답 | 검증 내용 |
|---|---|---|---|
| 정상 분주 50 µL | `DISPENSE:50` | `DISPENSE_SUCCESS` | 기본 분주 |
| 정상 분주 300 µL | `DISPENSE:300` | `DISPENSE_SUCCESS` | 최대 분주량 |
| 최소 분주 1 µL | `DISPENSE:1` | `DISPENSE_SUCCESS` | 최소치 |
| 0 µL 분주 | `DISPENSE:0` | `DISPENSE_SUCCESS` | 0 처리(no-op) |
| 음수 값 | `DISPENSE:-10` | 오류 | 예외 입력 처리 |

### 7.3 Centrifuge 단위 테스트

| 테스트 케이스 | 명령어 | 기대 응답 | 검증 내용 |
|---|---|---|---|
| 정상 Spin 2000 RPM | `SPIN:2000` | `SPIN_SUCCESS` | 기본 회전 |
| 최대 RPM 14000 | `SPIN:14000` | `SPIN_SUCCESS` | 실제 장비 최대치 |
| 저속 1000 RPM | `SPIN:1000` | `SPIN_SUCCESS` | 최소 속도 |
| 0 RPM | `SPIN:0` | `SPIN_SUCCESS` | 0 처리 |

### 7.4 Plate Reader 단위 테스트

| 테스트 케이스 | 명령어 | 기대 응답 | 검증 내용 |
|---|---|---|---|
| 정상 Scan 2000 RPM | `SCAN:2000` | 흡광도 (float) | 0.5~0.6 범위 |
| 고RPM Scan 4000 | `SCAN:4000` | 흡광도 (float) | 1.0~1.1 범위 |
| 저RPM Scan 1000 | `SCAN:1000` | 흡광도 (float) | 0.2~0.3 범위 |

---

## 테스트 실행 방법

### 통합 Closed-Loop 테스트 (T1~T6)

```batch
rem 1. 각 장비 실행 (4개 터미널)
start python liquid_handler.py
start python plate_hotel.py
start python centrifuge.py
start python plate_reader.py

rem 2. 원하는 테스트 JSON 로드 후 orchestrator 실행
python orchestrator.py
rem → GUI에서 "⚙️ JSON 계획서 다시 불러오기" 클릭
rem → "▶️ 실험 시퀀스 가동 시작" 클릭
```

### 개별 장비 단위 테스트 (T7)

```bash
python test_runner.py --unit
```

또는 개별 netcat/TCP 클라이언트로 수동 테스트:

```bash
python -c "
import socket
s = socket.socket()
s.connect(('127.0.0.1', 50051))
s.sendall(b'DISPENSE:50')
print(s.recv(1024).decode())
s.close()
"
```

---

## 테스트 결과 기록

| 날짜 | Suite | 통과/실패 | 비고 |
|---|---|---|---|
| - | - | - | - |
