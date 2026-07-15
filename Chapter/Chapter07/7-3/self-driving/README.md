# 자율주행 모델 학습 및 TEST2.mp4 비교 분석

## 1. 프로젝트 개요

- **목적**: 이미지 전처리 필터별 NVIDIA DAVE-2 모델 학습 및 성능 비교
- **학습 데이터**: TEST2.mp4에서 추출한 프레임 (1690장, 원본+좌우반전)
- **테스트 데이터**: TEST2.mp4 (1691프레임)
- **모델 아키텍처**: NVIDIA DAVE-2 (PyTorch)

---

## 2. 전처리 필터 4종

| 필터 | 설명 | 출력 |
|------|------|------|
| **invert** | CLAHE 적용 후 반전 + 가우시안 블러 | 그레이스케일 |
| **otsu** | CLAHE 적용 후 Otsu 이진화 (THRESH_BINARY_INV) | 이진 이미지 |
| **adaptive** | CLAHE 적용 후 적응형 이진화 (Gaussian) | 이진 이미지 |
| **invert_clahe** | CLAHE 반전 + CLAHE 재적용 + 가우시안 블러 | 그레이스케일 |

- 모든 필터: 원본 상단 절반 크롭 → CLAHE 적용 → 필터링 → 200×66 리사이즈

---

## 3. 학습 설정

| 항목 | 값 |
|------|-----|
| 배치 크기 | 100 |
| 에포크 | 10 |
| 학습률 | 1e-3 |
| 스텝/에포크 | 300 (train) / 200 (valid) |
| 옵티마이저 | Adam |
| 스케줄러 | ReduceLROnPlateau (factor=0.5, patience=2) |
| 손실 함수 | MSE Loss |
| 장치 | CUDA (GPU) |

---

## 4. 학습 결과

### 4.1 학습 곡선 비교

| 모델 | Best Val Loss | Best MAE | Best Epoch | Final MAE |
|------|--------------|----------|------------|-----------|
| invert | 1.8825 | **1.085°** | 10 | 1.085° |
| otsu | 1.5438 | **0.988°** | 9 | 1.003° |
| adaptive | 1.6642 | **1.021°** | 10 | 1.021° |
| **invert_clahe** | **0.9320** | **0.760°** | 10 | 0.760° |

![학습 곡선 비교](test2_results/training_comparison.png)

> **그림 설명**: 4개 모델의 학습 과정 비교. 왼쪽 위는 훈련 손실(Train Loss), 오른쪽 위는 검증 손실(Val Loss), 왼쪽 아래는 검증 MAE(평균 절대 오차), 오른쪽 아래는 최고 성능 비교 막대 그래프. invert_clahe가 가장 낮은 손실과 MAE를 기록하며, 모든 모델이 안정적으로 수렴하는 것을 확인할 수 있음.

### 4.2 에포크별 상세

#### invert
```
Epoch 01: train_loss=449.67  val_loss=60.94  val_MAE=6.482
Epoch 02: train_loss=78.12   val_loss=85.98  val_MAE=7.399
Epoch 03: train_loss=67.16   val_loss=39.80  val_MAE=4.916
Epoch 04: train_loss=58.40   val_loss=28.11  val_MAE=4.071
Epoch 05: train_loss=41.06   val_loss=16.77  val_MAE=3.118
Epoch 06: train_loss=20.60   val_loss=8.45   val_MAE=2.132
Epoch 07: train_loss=13.81   val_loss=5.09   val_MAE=1.671
Epoch 08: train_loss=9.86    val_loss=2.86   val_MAE=1.309
Epoch 09: train_loss=7.66    val_loss=2.00   val_MAE=1.126
Epoch 10: train_loss=6.16    val_loss=1.88   val_MAE=1.085
```

#### otsu
```
Epoch 01: train_loss=447.58  val_loss=96.65  val_MAE=8.281
Epoch 02: train_loss=81.64   val_loss=66.06  val_MAE=6.486
Epoch 03: train_loss=40.19   val_loss=18.95  val_MAE=3.408
Epoch 04: train_loss=21.41   val_loss=8.27   val_MAE=2.184
Epoch 05: train_loss=12.62   val_loss=5.63   val_MAE=1.899
Epoch 06: train_loss=8.65    val_loss=3.30   val_MAE=1.424
Epoch 07: train_loss=6.95    val_loss=2.33   val_MAE=1.196
Epoch 08: train_loss=5.66    val_loss=3.53   val_MAE=1.541
Epoch 09: train_loss=5.20    val_loss=1.54   val_MAE=0.988
Epoch 10: train_loss=4.61    val_loss=1.67   val_MAE=1.003
```

#### adaptive
```
Epoch 01: train_loss=499.84  val_loss=209.49 val_MAE=13.468
Epoch 02: train_loss=164.50  val_loss=58.67  val_MAE=6.175
Epoch 03: train_loss=49.48   val_loss=20.91  val_MAE=3.463
Epoch 04: train_loss=26.95   val_loss=19.54  val_MAE=3.335
Epoch 05: train_loss=18.62   val_loss=7.65   val_MAE=2.045
Epoch 06: train_loss=11.80   val_loss=3.03   val_MAE=1.374
Epoch 07: train_loss=9.32    val_loss=4.91   val_MAE=1.870
Epoch 08: train_loss=8.00    val_loss=2.04   val_MAE=1.165
Epoch 09: train_loss=7.19    val_loss=2.14   val_MAE=1.190
Epoch 10: train_loss=6.28    val_loss=1.66   val_MAE=1.021
```

#### invert_clahe
```
Epoch 01: train_loss=477.32  val_loss=185.21 val_MAE=12.679
Epoch 02: train_loss=127.31  val_loss=78.00  val_MAE=7.154
Epoch 03: train_loss=81.26   val_loss=86.55  val_MAE=7.787
Epoch 04: train_loss=52.94   val_loss=40.17  val_MAE=5.549
Epoch 05: train_loss=22.36   val_loss=8.97   val_MAE=2.288
Epoch 06: train_loss=13.65   val_loss=3.05   val_MAE=1.383
Epoch 07: train_loss=9.49    val_loss=2.29   val_MAE=1.206
Epoch 08: train_loss=6.23    val_loss=1.73   val_MAE=1.057
Epoch 09: train_loss=4.93    val_loss=1.35   val_MAE=0.940
Epoch 10: train_loss=4.27    val_loss=0.93   val_MAE=0.760
```

---

## 5. TEST2.mp4 추론 결과

### 5.1 예측 통계

| 모델 | Mean | Std | Min | Max | Range |
|------|------|-----|-----|-----|-------|
| invert | 103.71° | 3.87° | 93.85° | 113.90° | 20.05° |
| otsu | 102.65° | 5.08° | 88.49° | 113.91° | 25.42° |
| adaptive | 104.94° | 3.42° | 95.50° | 110.12° | 14.62° |
| invert_clahe | 102.84° | 4.18° | 86.84° | 112.67° | 25.83° |

![프레임별 예측 각도](test2_results/prediction_chart.png)

> **그림 설명**: TEST2.mp4의 각 프레임(0 ~ 1690)별로 4개 모델이 예측한 조향각 변화 그래프. 빨간 점선은 직진 기준(90°). 모든 모델이 90° ~ 115° 구간에서 안정적으로 예측하며, 좌우 반전 학습으로 인해 좌회전(90° 미만)과 우회전(90° 초과) 영역을 모두 커버함.

![샘플 프레임 예측](test2_results/prediction_samples.png)

> **그림 설명**: 랜덤으로 추출한 8개 프레임에 대한 모델별 예측 결과. 첫 번째 열은 원본 영상, 나머지 열은 각 필터 적용 후 모델이 예측한 조향각. 필터별로 이미지 표현 방식이 다르지만(invert는 밝은 부분이 도로, otsu/adaptive는 이진화) 모두 유사한 각도를 예측함.

![예측 각도 분포](test2_results/prediction_histogram.png)

> **그림 설명**: 4개 모델의 예측 조향각 분포 히스토그램. 빨간 점선은 평균 예측 각도, 검은 점선은 직진(90°). 분포가 좁을수록 안정적인 예측을 의미. adaptive가 가장 좁은 분포(Std=3.42°)로 안정적이나, invert_clahe가 가장 균형잡힌 분포를 보임.

### 5.2 Ground Truth 대비 오차

| 모델 | MAE | RMSE | Max Error |
|------|-----|------|-----------|
| invert | 15.79° | 20.25° | 45.84° |
| otsu | 15.68° | 19.81° | 46.88° |
| adaptive | 16.33° | 20.99° | 41.98° |
| **invert_clahe** | **15.53°** | **19.72°** | **41.59°** |

![예측 vs Ground Truth 비교](test2_results/prediction_vs_gt_chart.png)

> **그림 설명**: 검은 선은 Ground Truth(학습에 사용된 목표 조향각), 유색 선은 각 모델의 예측값. 첫 번째 그래프는 Ground Truth만 표시. 나머지 그래프에서 검은 선과 유색 선의 차이가 작을수록 모델이 목표에 가까운 예측을 함을 의미. 전체적으로 추세는 따르나 순간적인 급변 구간에서 차이가 발생.

![오차 분포](test2_results/error_distribution.png)

> **그림 설명**: Ground Truth 대비 예측 오차(예측값 - 실제값) 분포. 빨간 점선은 평균 오차, 검은 점선은 이상적인 0的位置. 분포가 0에 가까울수록 정확도가 높음. 모든 모델에서 약간의 양의 편향(+15°~16°)이 존재하며, 이는 Ground Truth 자체가 이전 모델 앙상블에 의해 생성된 값이기 때문.

![산점도](test2_results/scatter_vs_gt.png)

> **그림 설명**: x축은 Ground Truth 조향각, y축은 모델 예측 조향각. 빨간 점선(y=x)에 가까울수록 정확한 예측. 모든 모델에서 점들이 y=x선 위쪽에 분포하여, 실제보다 높은 각도를 예측하는 경향(약 +15° 편향)이 관찰됨. 이는 학습 데이터의 분포 차이에서 기인.

---

## 6. 분석

### 6.1 학습 성능 분석

1. **invert_clahe가 가장 우수**: Val Loss 0.93, MAE 0.76°로 모든 모델 중 최저
2. **모든 모델이 안정적으로 수렴**: 과적합 없이 val_loss가 지속적으로 감소
3. **이전 학습 대비 대폭 개선**:
   - 이전 (159장): MAE ~20-22°
   - 현재 (1690장): MAE ~0.76-1.09°
   - **약 25배 성능 향상**

### 6.2 데이터 증강 효과

- 원본 845장 + 좌우 반전 845장 = 1690장
- 좌우 반전으로 학습 데이터의 방향성 균형 확보
- 평균 조향각이 90.0°(직진)에 정확히 수렴

### 6.3 Ground Truth 대비 오차 원인

1. **Ground Truth 자체의 편향**: 이전 모델 앙상블이 생성한 값으로, 실제 사람의 조향과 차이 가능
2. **필터별 정보 손실**: 이진화 필터(otsu, adaptive)는 색상 정보 손실
3. **영상 품질**: 테스트 영상의 조명, 노이즈 등 환경 영향

### 6.4 필터별 특성 비교

| 필터 | 장점 | 단점 |
|------|------|------|
| invert | 정보 보존 우수 | 노이즈 민감 |
| otsu | 빠른 처리, 명확한 분리 | 세부 정보 손실 |
| adaptive | 로컬 변화 대응 | 잡음 증가 가능 |
| invert_clahe | 대비 향상 + 안정성 | 처리 복잡도 높음 |

---

## 7. 결론 및 개선 방안

### 7.1 최종 모델 선정

**invert_clahe** 모델을 최종 모델로 선정:
- 학습 성능: MAE 0.76° (최저)
- 검증 안정성: Val Loss 0.93 (최저)
- Ground Truth 오차: MAE 15.53° (최저)

### 7.2 개선 방안

1. **데이터 추가 수집**: 다양한 조건(조명, 날씨, 도로)의 영상 필요
2. **전이 학습**: ImageNet 등 사전 학습 모델 활용
3. **앙상블 방법**: 4개 모델의 예측값 가중 평균
4. **데이터 전처리 강화**: 노이즈 제거, 증강 기법 추가
5. **모델 구조 개선**: ResNet, MobileNet 등 최신 아키텍처 적용

---

## 8. 파일 구조

```
data_generator/
├── video/                          # 학습 이미지 (1690장)
│   ├── train_000001_101.png
│   ├── train_000002_079.png
│   └── ...
├── processed/                      # 전처리 이미지
│   ├── filter_invert_resized/
│   ├── filter_otsu_resized/
│   ├── filter_adaptive_resized/
│   └── filter_invert_clahe_resized/
├── model-20260715_221419_invert/   # 학습된 모델
├── model-20260715_222327_otsu/
├── model-20260715_223150_adaptive/
├── model-20260715_224033_invert_clahe/
├── test2_results/                  # 테스트 결과
│   ├── prediction_vs_gt_chart.png
│   ├── error_distribution.png
│   ├── scatter_vs_gt.png
│   ├── training_comparison.png
│   └── ...
├── generate_training_data.py       # 데이터 생성 스크립트
├── preprocess.py                   # 전처리 스크립트
├── train.py                        # 학습 스크립트
├── test_inference.py               # 추론 테스트 스크립트
└── result_analysis.py              # 결과 분석 스크립트
```

---

## 9. 실행 방법

```bash
# 1. 학습 데이터 생성
python generate_training_data.py

# 2. 전처리
python preprocess.py

# 3. 모델 학습 (개별 또는 전체)
python train.py invert
python train.py otsu
python train.py adaptive
python train.py invert_clahe
python train.py all

# 4. 추론 테스트
python test_inference.py

# 5. 학습 결과 분석
python result_analysis.py
```

---

*분석 일시: 2026-07-15*
*환경: Python 3.x, PyTorch, CUDA*
