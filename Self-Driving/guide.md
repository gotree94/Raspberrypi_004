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
```


# 1단계: 데이터 준비

```
python prepare_data.py
```

# 2단계: 모델 학습

```
python train_model.py
```

```
python train_model.py
2026-07-10 11:00:53.460757: I tensorflow/core/util/port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
2026-07-10 11:00:54.400263: I tensorflow/core/util/port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
==================================================
Self-Driving Steering Model Training (CPU)
==================================================

[1/4] 데이터 로드 중...
  학습: 278 samples
  검증: 70 samples
  이미지 shape: (80, 160, 3)

[2/4] 데이터 증강 설정...

[3/4] 모델 빌드 중...
C:\ProgramData\anaconda3\Lib\site-packages\keras\src\layers\convolutional\base_conv.py:113: UserWarning: Do not pass an `input_shape`/`input_dim` argument to a layer. When using Sequential models, prefer using an `Input(shape)` object as the first layer in the model instead.
  super().__init__(activity_regularizer=activity_regularizer, **kwargs)
2026-07-10 11:00:58.300783: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: SSE3 SSE4.1 SSE4.2 AVX AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
Model: "sequential"
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Layer (type)                         ┃ Output Shape                ┃         Param # ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ conv2d (Conv2D)                      │ (None, 40, 80, 16)          │           1,216 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout (Dropout)                    │ (None, 40, 80, 16)          │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ conv2d_1 (Conv2D)                    │ (None, 20, 40, 24)          │           9,624 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout_1 (Dropout)                  │ (None, 20, 40, 24)          │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ conv2d_2 (Conv2D)                    │ (None, 10, 20, 32)          │           6,944 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout_2 (Dropout)                  │ (None, 10, 20, 32)          │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ conv2d_3 (Conv2D)                    │ (None, 10, 20, 48)          │          13,872 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout_3 (Dropout)                  │ (None, 10, 20, 48)          │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ flatten (Flatten)                    │ (None, 9600)                │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dense (Dense)                        │ (None, 64)                  │         614,464 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout_4 (Dropout)                  │ (None, 64)                  │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dense_1 (Dense)                      │ (None, 32)                  │           2,080 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dense_2 (Dense)                      │ (None, 1)                   │              33 │
└──────────────────────────────────────┴─────────────────────────────┴─────────────────┘
 Total params: 648,233 (2.47 MB)
 Trainable params: 648,233 (2.47 MB)
 Non-trainable params: 0 (0.00 B)

[4/4] 학습 시작 (최대 100 epoch, CPU)...
==================================================
C:\ProgramData\anaconda3\Lib\site-packages\keras\src\trainers\data_adapters\py_dataset_adapter.py:121: UserWarning: Your `PyDataset` class should call `super().__init__(**kwargs)` in its constructor. `**kwargs` can include `workers`, `use_multiprocessing`, `max_queue_size`. Do not pass these arguments to `fit()`, as they will be ignored.
  self._warn_if_super_not_called()
Epoch 1/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 3s 121ms/step - loss: 0.3165 - mae: 0.4642 - val_loss: 0.2461 - val_mae: 0.3829 - learning_rate: 0.0010
Epoch 2/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 100ms/step - loss: 0.2398 - mae: 0.3905 - val_loss: 0.2096 - val_mae: 0.3641 - learning_rate: 0.0010
Epoch 3/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 104ms/step - loss: 0.2147 - mae: 0.3705 - val_loss: 0.1933 - val_mae: 0.3409 - learning_rate: 0.0010
Epoch 4/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 105ms/step - loss: 0.2001 - mae: 0.3765 - val_loss: 0.1793 - val_mae: 0.3295 - learning_rate: 0.0010
Epoch 5/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 110ms/step - loss: 0.1729 - mae: 0.3396 - val_loss: 0.1675 - val_mae: 0.3206 - learning_rate: 0.0010
Epoch 6/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 102ms/step - loss: 0.1808 - mae: 0.3406 - val_loss: 0.1481 - val_mae: 0.2933 - learning_rate: 0.0010
Epoch 7/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 105ms/step - loss: 0.1481 - mae: 0.2997 - val_loss: 0.1428 - val_mae: 0.2925 - learning_rate: 0.0010
Epoch 8/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 106ms/step - loss: 0.1538 - mae: 0.3086 - val_loss: 0.1333 - val_mae: 0.2799 - learning_rate: 0.0010
Epoch 9/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 98ms/step - loss: 0.1409 - mae: 0.2945 - val_loss: 0.1342 - val_mae: 0.2859 - learning_rate: 0.0010
Epoch 10/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 103ms/step - loss: 0.1699 - mae: 0.3376 - val_loss: 0.1090 - val_mae: 0.2489 - learning_rate: 0.0010
Epoch 11/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 105ms/step - loss: 0.1709 - mae: 0.3245 - val_loss: 0.1013 - val_mae: 0.2399 - learning_rate: 0.0010
Epoch 12/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 99ms/step - loss: 0.1245 - mae: 0.2541 - val_loss: 0.1030 - val_mae: 0.2472 - learning_rate: 0.0010
Epoch 13/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 105ms/step - loss: 0.1314 - mae: 0.2867 - val_loss: 0.0963 - val_mae: 0.2317 - learning_rate: 0.0010
Epoch 14/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 97ms/step - loss: 0.1220 - mae: 0.2606 - val_loss: 0.0971 - val_mae: 0.2286 - learning_rate: 0.0010
Epoch 15/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 113ms/step - loss: 0.1511 - mae: 0.2941 - val_loss: 0.0878 - val_mae: 0.2202 - learning_rate: 0.0010
Epoch 16/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 99ms/step - loss: 0.1246 - mae: 0.2732 - val_loss: 0.0927 - val_mae: 0.2276 - learning_rate: 0.0010
Epoch 17/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 102ms/step - loss: 0.1189 - mae: 0.2572 - val_loss: 0.0875 - val_mae: 0.2189 - learning_rate: 0.0010
Epoch 18/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.1105 - mae: 0.2401 - val_loss: 0.0898 - val_mae: 0.2291 - learning_rate: 0.0010
Epoch 19/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 100ms/step - loss: 0.1349 - mae: 0.2660 - val_loss: 0.0851 - val_mae: 0.2185 - learning_rate: 0.0010
Epoch 20/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.1211 - mae: 0.2454 - val_loss: 0.0912 - val_mae: 0.2190 - learning_rate: 0.0010
Epoch 21/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 109ms/step - loss: 0.1132 - mae: 0.2466 - val_loss: 0.0736 - val_mae: 0.2062 - learning_rate: 0.0010
Epoch 22/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 98ms/step - loss: 0.1225 - mae: 0.2595 - val_loss: 0.0890 - val_mae: 0.2278 - learning_rate: 0.0010
Epoch 23/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 99ms/step - loss: 0.1071 - mae: 0.2313 - val_loss: 0.0889 - val_mae: 0.2326 - learning_rate: 0.0010
Epoch 24/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.1006 - mae: 0.2386 - val_loss: 0.0831 - val_mae: 0.2226 - learning_rate: 0.0010
Epoch 25/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 99ms/step - loss: 0.0932 - mae: 0.2222 - val_loss: 0.0676 - val_mae: 0.1857 - learning_rate: 0.0010
Epoch 26/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 99ms/step - loss: 0.1127 - mae: 0.2467 - val_loss: 0.0685 - val_mae: 0.1926 - learning_rate: 0.0010
Epoch 27/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 101ms/step - loss: 0.1158 - mae: 0.2446 - val_loss: 0.0677 - val_mae: 0.1861 - learning_rate: 0.0010
Epoch 28/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 101ms/step - loss: 0.1082 - mae: 0.2357 - val_loss: 0.0665 - val_mae: 0.1854 - learning_rate: 0.0010
Epoch 29/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.1035 - mae: 0.2247 - val_loss: 0.0719 - val_mae: 0.1940 - learning_rate: 0.0010
Epoch 30/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 101ms/step - loss: 0.1000 - mae: 0.2329 - val_loss: 0.0649 - val_mae: 0.1823 - learning_rate: 0.0010
Epoch 31/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 96ms/step - loss: 0.0912 - mae: 0.2210 - val_loss: 0.0693 - val_mae: 0.1994 - learning_rate: 0.0010
Epoch 32/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 102ms/step - loss: 0.0866 - mae: 0.2169 - val_loss: 0.0645 - val_mae: 0.1858 - learning_rate: 0.0010
Epoch 33/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.1155 - mae: 0.2287 - val_loss: 0.0712 - val_mae: 0.2036 - learning_rate: 0.0010
Epoch 34/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 97ms/step - loss: 0.0892 - mae: 0.2209 - val_loss: 0.0606 - val_mae: 0.1818 - learning_rate: 0.0010
Epoch 35/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.0789 - mae: 0.2007 - val_loss: 0.0631 - val_mae: 0.1829 - learning_rate: 0.0010
Epoch 36/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 98ms/step - loss: 0.1185 - mae: 0.2457 - val_loss: 0.0776 - val_mae: 0.2136 - learning_rate: 0.0010
Epoch 37/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 98ms/step - loss: 0.1085 - mae: 0.2444 - val_loss: 0.0659 - val_mae: 0.1830 - learning_rate: 0.0010
Epoch 38/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 101ms/step - loss: 0.0910 - mae: 0.2064 - val_loss: 0.0656 - val_mae: 0.1867 - learning_rate: 0.0010
Epoch 39/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 96ms/step - loss: 0.1239 - mae: 0.2480 - val_loss: 0.0652 - val_mae: 0.1891 - learning_rate: 0.0010
Epoch 40/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 98ms/step - loss: 0.1013 - mae: 0.2298 - val_loss: 0.0651 - val_mae: 0.1880 - learning_rate: 5.0000e-04
Epoch 41/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 93ms/step - loss: 0.0952 - mae: 0.2129 - val_loss: 0.0643 - val_mae: 0.1886 - learning_rate: 5.0000e-04
Epoch 42/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.1036 - mae: 0.2300 - val_loss: 0.0631 - val_mae: 0.1791 - learning_rate: 5.0000e-04
Epoch 43/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.0904 - mae: 0.2215 - val_loss: 0.0642 - val_mae: 0.1851 - learning_rate: 5.0000e-04
Epoch 44/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 92ms/step - loss: 0.0865 - mae: 0.1998 - val_loss: 0.0677 - val_mae: 0.1903 - learning_rate: 5.0000e-04
Epoch 45/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.1065 - mae: 0.2265 - val_loss: 0.0620 - val_mae: 0.1709 - learning_rate: 2.5000e-04
Epoch 46/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.0901 - mae: 0.2048 - val_loss: 0.0607 - val_mae: 0.1707 - learning_rate: 2.5000e-04
Epoch 47/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 101ms/step - loss: 0.0838 - mae: 0.2050 - val_loss: 0.0603 - val_mae: 0.1673 - learning_rate: 2.5000e-04
Epoch 48/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 101ms/step - loss: 0.0840 - mae: 0.1987 - val_loss: 0.0591 - val_mae: 0.1672 - learning_rate: 2.5000e-04
Epoch 49/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 119ms/step - loss: 0.0766 - mae: 0.1930 - val_loss: 0.0551 - val_mae: 0.1641 - learning_rate: 2.5000e-04
Epoch 50/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 108ms/step - loss: 0.0788 - mae: 0.1984 - val_loss: 0.0546 - val_mae: 0.1666 - learning_rate: 2.5000e-04
Epoch 51/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 99ms/step - loss: 0.0909 - mae: 0.2127 - val_loss: 0.0556 - val_mae: 0.1668 - learning_rate: 2.5000e-04
Epoch 52/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.0876 - mae: 0.2020 - val_loss: 0.0603 - val_mae: 0.1789 - learning_rate: 2.5000e-04
Epoch 53/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 96ms/step - loss: 0.1019 - mae: 0.2207 - val_loss: 0.0609 - val_mae: 0.1795 - learning_rate: 2.5000e-04
Epoch 54/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.0855 - mae: 0.2017 - val_loss: 0.0596 - val_mae: 0.1741 - learning_rate: 2.5000e-04
Epoch 55/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 97ms/step - loss: 0.0847 - mae: 0.2117 - val_loss: 0.0608 - val_mae: 0.1773 - learning_rate: 2.5000e-04
Epoch 56/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.0769 - mae: 0.2001 - val_loss: 0.0602 - val_mae: 0.1766 - learning_rate: 1.2500e-04
Epoch 57/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.0845 - mae: 0.2014 - val_loss: 0.0584 - val_mae: 0.1735 - learning_rate: 1.2500e-04
Epoch 58/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 95ms/step - loss: 0.0830 - mae: 0.2024 - val_loss: 0.0561 - val_mae: 0.1685 - learning_rate: 1.2500e-04
Epoch 59/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 96ms/step - loss: 0.0977 - mae: 0.2163 - val_loss: 0.0565 - val_mae: 0.1705 - learning_rate: 1.2500e-04
Epoch 60/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 96ms/step - loss: 0.0987 - mae: 0.2180 - val_loss: 0.0572 - val_mae: 0.1706 - learning_rate: 1.2500e-04
Epoch 61/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 90ms/step - loss: 0.0828 - mae: 0.2035 - val_loss: 0.0584 - val_mae: 0.1736 - learning_rate: 6.2500e-05
Epoch 62/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 96ms/step - loss: 0.0750 - mae: 0.1932 - val_loss: 0.0580 - val_mae: 0.1729 - learning_rate: 6.2500e-05
Epoch 63/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 93ms/step - loss: 0.1001 - mae: 0.2148 - val_loss: 0.0574 - val_mae: 0.1721 - learning_rate: 6.2500e-05
Epoch 64/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.0914 - mae: 0.2111 - val_loss: 0.0567 - val_mae: 0.1702 - learning_rate: 6.2500e-05
Epoch 65/100
9/9 ━━━━━━━━━━━━━━━━━━━━ 1s 94ms/step - loss: 0.0801 - mae: 0.2037 - val_loss: 0.0564 - val_mae: 0.1695 - learning_rate: 6.2500e-05

==================================================
학습 완료!
  소요 시간: 60.8s
  최종 Train Loss: 0.085352
  최종 Val Loss:   0.056408
  최종 Train MAE:  0.203769
  최종 Val MAE:    0.169460
  모델 저장: C:\Users\Administrator\Desktop\Self-Driving\steering_model.keras
  학습 곡선: training_history.png
```

# 3단계: 시뮬레이터 실행

```
python simulator.py
```

```
python simulator.py
모델 로드 완료: C:\Users\Administrator\Desktop\Self-Driving\steering_model.keras
영상: 1045 프레임, 30.0 FPS

=== Self-Driving Simulator ===
  SPACE: 일시정지/재개
  ESC: 종료


영상 끝 — 처음으로 돌아갑니다.

==================================================
시뮬레이션 종료
  실행 시간: 55.0s
  예측 프레임: 525
  GT vs Pred MAE: 0.1678
  GT vs Pred MSE: 0.065981
  결과 저장 완료
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


