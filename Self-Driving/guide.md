# Self-Driving 자율주행 시뮬레이터 프로젝트

PyTorch/TensorFlow를 활용한 엔드투엔드(end-to-end) 자율주행 모델 개발 가이드.

<br>

---

<br>

## 1. 프로젝트 개요

### 1.1 목표

하나의 주행 영상만으로 다음과 같은 파이프라인을 구축합니다:

```
주행 영상 → 프레임 추출 → 차선 감지 → 가상 조향각 생성
    → CNN 모델 학습 → 실시간 자율주행 시뮬레이터
```

### 1.2 철학: End-to-End Learning

NVIDIA가 2016년 발표한 논문 **"End-to-End Learning for Self-Driving Cars"** (arXiv:1604.07316) 방식을 차용했습니다.

**전통적 방식 (규칙 기반):**
```
영상 → 차선 검출 → 차선 위치 계산 → 조향각 계산 ← 규칙(if/else)이 많아짐
```

**End-to-End 방식 (학습 기반):**
```
영상 → [CNN] → 조향각 출력
```

모든 처리를 단일 신경망이 학습합니다. 중간에 사람이 규칙을 정의할 필요가 없습니다.

### 1.3 사용 기술

| 기술 | 용도 |
|:---|:---|
| **Python 3.x** | 전체 구현 언어 |
| **OpenCV 4** | 영상 처리, 차선 검출, 시각화 |
| **TensorFlow 2 / Keras** | CNN 모델 정의 및 학습 |
| **NumPy** | 데이터 배열 처리 |
| **Matplotlib** | 학습 곡선 시각화 |

<br>

---

<br>

## 2. 전체 구조

```
Self-Driving/
├── Self-driving.mp4            # 원본 주행 영상 (1920x1080, 30fps, 1045프레임)
├── prepare_data.py             # 1단계: 데이터 준비
├── train_model.py              # 2단계: 모델 학습
├── simulator.py                # 3단계: 자율주행 시뮬레이터
│
├── training_data/              # (실행 시 생성)
│   ├── frame_0000.npy ~       # 추출된 프레임 이미지 (160x80 RGB)
│   └── metadata.json           # 각 프레임의 조향각 정보
│
├── steering_model.keras        # (실행 시 생성) 학습된 모델
├── training_history.png        # (실행 시 생성) 학습 곡선 그래프
└── simulator_result.png        # (실행 시 생성) 시뮬레이션 결과
```

<br>

---

<br>

## 3. 데이터 준비 (prepare_data.py)

### 3.1 동작 흐름

```
비디오 프레임 읽기
    ↓
Canny Edge Detection (에지 검출)
    ↓
Hough Transform (직선 검출)
    ↓
좌/우 차선 분류 (기울기 기준)
    ↓
차선 중심 계산 → 조향각 산출 (-1 ~ +1)
    ↓
이미지 리사이즈 (160x80) → .npy 저장
    ↓
메타데이터 JSON 저장
```

### 3.2 차선 검출 원리

```python
ROI (Region of Interest): 프레임 하단 1/3 영역만 사용
    이유: 자율주행에 필요한 건 가까운 도로면, 하늘/풍경은 불필요

Canny Edge: 그레이스케일 → Blur → 에지 검출
    임계값: 50~150 (환경에 따라 조정 가능)

HoughLinesP: 에지 픽셀을 직선으로 변환
    threshold=30, minLineLength=20, maxLineGap=50

좌/우 차선 분류:
    기울기(slope) > 0.2  → 우측 차선
    기울기(slope) < -0.2 → 좌측 차선

조향각 계산:
    차선 중심 = (left_x + right_x) / 2
    offset = (차선중심 - 화면중심) / (화면중심/2)
    steering = clamp(offset, -1, 1)
```

### 3.3 조향각의 의미

| 값 | 의미 |
|:---:|:---|
| **0.0** | 직진 |
| **+0.3 ~ +1.0** | 우회전 (값이 클수록 급회전) |
| **-0.3 ~ -1.0** | 좌회전 (값이 작을수록 급회전) |
| **±0.1 미만** | 거의 직진 |

### 3.4 Ground Truth의 한계

이 프로젝트에서는 **실제 조향각 데이터가 없기 때문에** 차선 검출 결과로 가상의 조향각(Ground Truth)을 생성합니다.

```
한계 1: 차선이 없는 도로(교차로, 주차장)에서는 조향각 생성 불가
한계 2: 그림자, 빛 반사, 노면 마크 등에 의해 잘못된 차선 검출 가능
한계 3: 사람이 실제로 조향한 값과 차선 위치 기반 값은 다를 수 있음
```

이러한 한계를 극복하려면 **실제 차량에서 수집한 조향각 데이터**가 필요합니다.

<br>

---

<br>

## 4. 모델 학습 (train_model.py)

### 4.1 네트워크 아키텍처

NVIDIA E2E 모델을 CPU 환경에 맞게 경량화한 구조입니다.

```
Layer                  Output Shape        Param #
────────────────────────────────────────────────────
Normalization          (80, 160, 3)            3    
Conv2D (5x5, /2)      (40, 80, 16)         1,216
Dropout 0.1                                   
Conv2D (5x5, /2)      (20, 40, 24)         9,624
Dropout 0.1                                   
Conv2D (3x3, /2)      (10, 20, 32)         6,944
Dropout 0.1                                   
Conv2D (3x3, /1)      (10, 20, 48)        13,872
Dropout 0.1                                   
Flatten               (9,600)                   
Dense (64)             64                 614,464
Dropout 0.2                                   
Dense (32)             32                   2,080
Dense (1)               1                      33
────────────────────────────────────────────────────
Total params: ~648,236
```

### 4.2 NVIDIA 원본과의 차이

| 항목 | NVIDIA 원본 (2016) | 이 프로젝트 |
|:---|:---|:---|
| 입력 해상도 | 200x66 (YUV) | 160x80 (RGB) |
| Conv 레이어 | 9층 | 4층 |
| 필터 시작 | 24→36→48→64→64 | 16→24→32→48 |
| Dense 레이어 | 1164→100→50→10 | 64→32→1 |
| 학습 환경 | GPU (Titan X) | CPU |

### 4.3 학습 과정

```python
# 손실 함수: MSE (Mean Squared Error)
# 옵티마이저: Adam (lr=0.001)
# 배치 크기: 32
# 최대 에폭: 100

# 콜백
ModelCheckpoint  → 검증 손실 최저일 때 모델 저장
ReduceLROnPlateau → 5에폭 동안 개선 없으면 학습률 절반
EarlyStopping    → 15에폭 동안 개선 없으면 종료

# 데이터 증강 (ImageDataGenerator)
width_shift_range=0.05   # 좌우 5% 이동
height_shift_range=0.05  # 상하 5% 이동
brightness_range=[0.8, 1.2]  # 밝기 변화
```

### 4.4 CPU 학습 시간 예측

| 데이터 수 | 에폭 | 예상 시간 |
|:---:|:---:|:---:|
| ~300장 | 100 | 5~10분 |
| ~600장 | 100 | 10~20분 |
| ~1000장 | 100 | 20~40분 |

<br>

---

<br>

## 5. 시뮬레이터 (simulator.py)

### 5.1 화면 구성

```
┌─────────────────────────────────────────────────────┐
│                    AI AUTO / HUMAN                    │
│  Steering: +0.321 (+14.4 deg)     GT: +0.315        │
│                                          ┌───────┐  │
│                                          │ GT vs │  │
│                                          │ Pred  │  │
│                                          │ chart │  │
│                                          └───────┘  │
│                                                      │
│                 주행 영상 화면                        │
│                                                      │
│                                                      │
│   ◄═══════════●═══════════►    ← 조향 바            │
│   L           │           R                          │
└─────────────────────────────────────────────────────┘
```

### 5.2 기능

| 키 | 기능 |
|:---:|:---|
| **ESC** | 시뮬레이터 종료 |
| **SPACE** | 일시정지 / 재개 |

### 5.3 화면 요소 설명

| 요소 | 설명 |
|:---|:---|
| **AI AUTO / HUMAN** | 현재 예측 모드 (AI 예측값 / Ground Truth) |
| **Steering** | AI가 예측한 조향각 및 각도(deg) |
| **GT Steering** | 차선 검출로 생성된 원본 조향각 |
| **GT vs Pred 차트** | 최근 100프레임의 GT(노랑)와 예측값(초록) 비교 |
| **조향 바** | 좌(좌회전) / 중앙(직진) / 우(우회전) |

<br>

---

<br>

## 6. 실행 방법

### 6.1 사전 준비

OpenCV와 TensorFlow가 설치되어 있어야 합니다.

```bash
pip install opencv-python numpy tensorflow matplotlib
```

### 6.2 전체 실행

```bash
cd C:\Users\Administrator\Desktop\Self-Driving

# 1단계: 데이터 준비
python prepare_data.py

# 2단계: 모델 학습
python train_model.py

# 3단계: 시뮬레이터 실행
python simulator.py
```

### 6.3 각 단계별 결과 확인

**prepare_data.py 실행 후:**
- `training_data/` 폴더에 `frame_0000.npy` ~ 파일들 생성
- `metadata.json`에 각 프레임의 조향각 기록
- 실행 중 실시간으로 차선 검출 결과 확인 가능 (ESC로 중단)

**train_model.py 실행 후:**
- `steering_model.keras` — 학습된 모델 파일
- `training_history.png` — 학습 곡선 (loss, MAE)

**simulator.py 실행 후:**
- 모델이 실시간으로 조향각 예측
- GT와 예측값 비교 그래프 표시
- ESC 누르면 최종 통계 출력

<br>

---

<br>

## 7. 결과 해석

### 7.1 학습이 잘 된 경우

```
Val Loss (MSE): 0.01 ~ 0.05  (낮을수록 좋음)
Val MAE:        0.05 ~ 0.15  (조향각 오차 0.1 = 약 4.5도)
```

학습 곡선에서 Train Loss와 Val Loss가 함께 감소하면 정상입니다.

### 7.2 과적합 (Overfitting)

```
Train Loss: 계속 감소 → 0.001
Val Loss:  감소하다가 다시 증가 ← 과적합 신호
```

EarlyStopping이 자동으로 중단시킵니다.

### 7.3 예측이 부정확한 경우

원인과 해결 방법:

| 현상 | 원인 | 해결 |
|:---|:---|:---|
| 모든 예측이 0에 가까움 | 차선 검출 실패로 조향각 대부분이 0 | Canny 임계값 조정 |
| 좌/우 편향 | 데이터 불균형 (우회전만 많음) | 좌회전 구간 추가 또는 데이터 균형 |
| 예측이 튐(noisy) | 모델이 너무 큼 / 데이터 부족 | Dropout 증가 / 데이터 증강 강화 |

### 7.4 시뮬레이터 화면 해석

- **GT(노랑선)와 Pred(초록선)가 비슷한 궤적** → 모델이 잘 학습됨
- **Pred가 GT를 따라가지 못함** → 학습 부족 또는 데이터 문제
- **조향 바가 중앙에 계속 고정** → 모델이 직진만 예측 (학습 실패)

<br>

---

<br>

## 8. 심화: 더 나은 모델을 위한 방향

### 8.1 실제 조향각 데이터 수집

가장 큰 한계는 **가상 조향각**입니다. 더 나은 결과를 위해:

```
방법 1: 게임 시뮬레이터 사용 (예: CARLA, AirSim)
방법 2: USB 게임핸들로 수동 주행 → 조향각 기록
방법 3: 실제 차량에 카메라 + OBD2 + 조향각 센서 장착
```

### 8.2 CNN → Transformer 도입

최근 연구에서는 CNN 대신 Vision Transformer(ViT)가 더 좋은 성능을 보입니다.

### 8.3 이미지 해상도 향상

CPU 환경이 아니라 GPU를 사용할 수 있다면 입력 해상도를 높여 더 세밀한 특징 학습이 가능합니다.

### 8.4 데이터 증강 다양화

```python
datagen = ImageDataGenerator(
    rotation_range=5,        # 회전
    zoom_range=0.05,         # 확대/축소
    width_shift_range=0.1,  # 좌우 이동
    height_shift_range=0.05, # 상하 이동
    brightness_range=[0.7, 1.3],  # 밝기 변화
    shear_range=0.05,         # 전단 변환
)
```

### 8.5 시계열 고려 (RNN/LSTM)

단일 프레임이 아닌 **연속된 프레임(시퀀스)** 을 입력으로 사용하면 조향각 예측이 더 부드러워집니다.

```python
model = Sequential([
    TimeDistributed(Conv2D(32, (3,3)), input_shape=(10, 80, 160, 3)),
    TimeDistributed(Flatten()),
    LSTM(64),
    Dense(1)
])
```

<br>

---

<br>

## 9. 참고 자료

| 자료 | 링크 |
|:---|:---|
| NVIDIA DAVE-2 논문 | https://arxiv.org/abs/1604.07316 |
| OpenCV 문서 | https://docs.opencv.org/ |
| TensorFlow Keras | https://www.tensorflow.org/guide/keras |

<br>

---

<br>

## 10. 라이선스

이 프로젝트는 학습/교육 목적으로 자유롭게 사용, 수정, 배포할 수 있습니다.

---

*문서 생성일: 2026-07-10*
