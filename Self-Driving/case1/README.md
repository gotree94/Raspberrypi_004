# Case1: LiDAR + IMU + Wheel Sensor 데이터 분석

## 파일

- `slam_data_20260629_124940.csv` — 4051행, 8열

---

## 1. 컬럼 구조

```csv
timestamp, msg_type, scan_index, dist_or_yaw, pulse_L_or_ax, pulse_R_or_ay, az, gz
```

### msg_type 별 의미

| msg_type | 설명 | dist_or_yaw | pulse_L_or_ax | pulse_R_or_ay | az | gz |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **STEP** | 스캔 시작 + IMU | 10.3 (고정) | **ax** (MPU6050) | **ay** (MPU6050) | az | gz |
| **S** | LiDAR 측정 | **스캔 각도** (0~180°, 2° step) | **L Wheel Pulse** | **R Wheel Pulse** | - | - |
| **ROT** | 90° 회전 감지 | yaw (≈-90°) | ax | ay | - | - |

- `scan_index`: 44회 (STEP 44개, S 4004개, ROT 3개)
- ROT 발생 시점: scan 11, 22, 33 (약 11초 간격)

---

## 2. 센서 구성

| 센서 | 모델 | 데이터 | 비고 |
|:---|:---|:---|:---|
| **IMU** | MPU6050 | ax, ay, az, gz | 6축, gz = Z축 각속도(°/s) |
| **2D LiDAR** | - | 0~180°, 2° step, 91포인트/scan | 전방 180° 거리 측정 |
| **Wheel Sensor** | Line Tracer | L/R pulse 값 | 바퀴 회전 감지, **아날로그 위치값** |

### MPU6050 gz 통계 (STEP 메시지 44개)

| 항목 | 값 |
|:---|---:|
| Range | -2.04 ~ +2.25 °/s |
| Mean ± Std | -0.10 ± 1.00 |
| \|gz\| < 0.3 (직진) | 27% |
| \|gz\| > 1.0 (강한 회전) | 39% |

---

## 3. Wheel Pulse 기반 조향각 분석

### 방법

각 scan의 첫 S 메시지와 마지막 S 메시지의 pulse 값을 비교:

```python
dL = last_L - first_L
dR = last_R - first_R
steering = (dR - dL) / (|dR| + |dL|)  # 항상 ±1.0
```

### 결과

- **44개 scan 모두 steering = ±1.0** (중간값 없음, 항상 극값)
- dL과 dR은 항상 반대 부호를 가짐

| dL 부호 | dR 부호 | 해석 | 발생 비율 |
|:---:|:---:|:---|:---:|
| + | - | L증가 R감소 | 34% |
| - | + | L감소 R증가 | 66% |

### 한계

- **IMU gz와의 방향 일치율: 53%** (동전 던지기 수준)
- 라인트레이서 센서는 **아날로그 절대 위치값**을 출력하므로, 누적 엔코더가 아님
- `dL/dR`이 실제 주행 거리/방향과 선형 관계가 없음
- **연속 조향각 GT로 부적합**

---

## 4. IMU gz 기반 조향각

### 장점

- MPU6050이 직접 측정한 **실제 회전 각속도**
- **연속값** (-1~+1로 정규화 가능)
- 자이로 특성상 드리프트는 있지만 단기 정확도 높음

### 사용법

```python
# prepare_data.py의 steering GT를 gz로 대체
gz_norm = np.clip(gz / 3.0, -1.0, 1.0)
```

### 한계

- **STEP 메시지당 1회** (약 1초 간격, 44샘플) → 샘플 수 적음
- 비디오(30fps)와 시간 동기화 필요
- CSV 데이터는 dashcam 비디오와 **다른 차량/환경**에서 수집됨

---

## 5. Lane Detection vs IMU gz 비교

| 지표 | Lane Detection | IMU gz |
|:---|---:|---:|
| Source | Dashcam 비디오 | MPU6050 센서 |
| Samples | 200+ | 44 |
| Mean | +0.057 | -0.035 |
| Std | 0.40 | 0.33 |
| Straight 비율 | 29% | 39% |
| Auto-correlation (lag1) | **0.73** | **0.10** |

### Auto-correlation 차이의 의미

- **Lane (0.73)**: 프레임 간 강한 상관관계 → 실제 도로 주행의 **부드러운 곡선**
- **gz (0.10)**: 거의 무작위 → 급격한 좌우 교대 운동 (실내 시험 트랙?)

---

## 6. 결론

### 사용 가능성

| 활용 방안 | 가능? | 이유 |
|:---|---:|:---|
| 연속 조향각 GT (Wheel Pulse) | ❌ | 항상 ±1.0, IMU와 불일치 47% |
| 연속 조향각 GT (IMU gz) | ✅ | 실제 물리 측정, 연속값 |
| Lane Detection GT 대체 | ❌ | 데이터셋이 다름 (차량/환경 상이) |
| 모델 검증용 방향 일치 확인 | ✅ | "예측 방향 vs gz 방향" 비교 가능 |

### 최종 판단

1. **현재 비디오 기반 프로젝트**에는 Lane Detection GT가 최선 (부드럽고, 프레임 많고, 실제 도로)
2. CSV (case1) 데이터는 **별도 분석용**으로 보관
3. **최적의 해결책:** USB 게임핸들 + 시뮬레이터로 실제 조향각 GT 직접 수집

---

## 7. 관련 스크립트

| 파일 | 설명 |
|:---|:---|
| `check_odometry.py` | Wheel pulse 기반 조향각 분석 |
| `check_gyro.py` | IMU gz 기반 조향각 + pulse 비교 |
| `check_sensors.py` | msg_type 별 데이터 구조 확인 |

### 사용법

```powershell
python check_odometry.py    # pulse 기반 분석
python check_gyro.py        # gz 기반 분석 + 일치율
python check_sensors.py     # 센서 종류 확인
```
