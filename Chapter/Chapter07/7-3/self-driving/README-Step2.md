# 자율주행 학습 파이프라인 사용법

모든 스크립트는 커맨드라인 인자를 통해 유연하게 설정할 수 있습니다.

---

## 전체 파이프라인 순서

```
1. generate_training_data2.py  → 학습용 영상 생성
2. preprocess.py               → 4개 필터로 전처리
3. train.py                    → 모델 학습
4. test_inference.py           → 추론 및 GT 비교
5. result_analysis.py          → 학습 곡선 분석
```

---

## 1. 학습 데이터 생성 (`generate_training_data2.py`)

TEST2.mp4에서 프레임을 추출하고, 4개 모델의 앙상블로 예측한 각도를 저장합니다.

### 사용법

```bash
python generate_training_data2.py <angle_shift> [output_folder]
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `angle_shift` | O | 각도 시프트 값 (정수, +/-) |
| `output_folder` | X | 출력 폴더명 (기본값: `video`) |

### 예시

```bash
python generate_training_data2.py -10                        # video/ 폴더에 -10도 시프트
python generate_training_data2.py -10 video_shifted_m10      # video_shifted_m10/ 폴더에 -10도 시프트
python generate_training_data2.py +5 video_shifted_p5        # video_shifted_p5/ 폴더에 +5도 시프트
python generate_training_data2.py 0 video_no_shift           # video_no_shift/ 폴더에 시프트 없음
```

### 출력

- `video/train_000001_090.png` 형식의 학습 이미지
- 원본 + 좌우 반전 이미지 동시 생성
- 각도: `앙상블 예측값 + angle_shift`

---

## 2. 전처리 (`preprocess.py`)

학습 이미지를 4개 필터(Invert, Otsu, Adaptive, Invert+CLAHE)로 전처리합니다.

### 사용법

```bash
python preprocess.py <input_folder> [output_folder]
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `input_folder` | O | 입력 폴더명 (generate_training_data2.py의 출력) |
| `output_folder` | X | 출력 폴더명 (기본값: `processed_<input_folder>`) |

### 예시

```bash
python preprocess.py video                                  # processed_video/ 생성
python preprocess.py video_shifted_m10                      # processed_video_shifted_m10/ 생성
python preprocess.py video_shifted_m10 processed_m10        # processed_m10/ 생성
```

### 출력 구조

```
processed_video_shifted_m10/
├── filter_invert/
├── filter_invert_resized/
├── filter_otsu/
├── filter_otsu_resized/
├── filter_adaptive/
├── filter_adaptive_resized/
├── filter_invert_clahe/
└── filter_invert_clahe_resized/
```

---

## 3. 모델 학습 (`train.py`)

전처리된 이미지로 DAVE-2 모델을 학습합니다.

### 사용법

```bash
python train.py <source> <processed_folder>
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `source` | O | 학습할 필터 (`invert`, `otsu`, `adaptive`, `invert_clahe`, `all`) |
| `processed_folder` | O | 전처리된 데이터 폴더명 |

### 예시

```bash
python train.py invert_clahe processed_video_shifted_m10              # 1개 필터만 학습
python train.py all processed_video_shifted_m10                       # 4개 필터 전체 학습
```

### 출력

- `model-<timestamp>_<filter>/` 폴더 생성
- `lane_navigation_best.pt`: 최적 가중치
- `lane_navigation_final.pt`: 최종 가중치
- `lane_navigation_final.torchscript`: TorchScript 모델
- `history.pickle`: 학습 기록

### 하이퍼파라미터 (코드 내 상수)

| 항목 | 값 |
|------|-----|
| Batch Size | 100 |
| Epochs | 10 |
| Learning Rate | 1e-3 |
| Steps per Epoch | 300 |
| Validation Steps | 200 |

---

## 4. 추론 및 GT 비교 (`test_inference.py`)

학습된 모델로 TEST2.mp4를 추론하고 Ground Truth와 비교합니다.

### 사용법

```bash
python test_inference.py <model_keyword> [gt_folder] [output_folder]
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `model_keyword` | O | 모델 폴더 키워드 (타임스탬프 등) |
| `gt_folder` | X | Ground Truth 폴더 (기본값: `video`) |
| `output_folder` | X | 결과 출력 폴더 (기본값: `test2_results_<keyword>`) |

### 예시

```bash
python test_inference.py 20260715_224033                                     # 기본 GT 사용
python test_inference.py 20260715_224033 video_shifted_m10                    # 시프트된 GT 사용
python test_inference.py 20260715_224033 video_shifted_m10 results_m10        # 결과 폴더 지정
```

### 출력

- `prediction_vs_gt_chart.png`: 예측 vs GT 비교 차트
- `error_distribution.png`: 오차 분포 히스토그램
- `scatter_vs_gt.png`: 산점도

---

## 5. 학습 곡선 분석 (`result_analysis.py`)

4개 모델의 학습 곡선을 비교 분석합니다.

### 사용법

```bash
python result_analysis.py <model_keyword> [output_folder]
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `model_keyword` | O | 모델 폴더 키워드 |
| `output_folder` | X | 결과 출력 폴더 (기본값: `test2_results_<keyword>`) |

### 예시

```bash
python result_analysis.py 20260715_224033                           # 기본 위치에 저장
python result_analysis.py 20260715_224033 test2_results_m10          # 결과 폴더 지정
```

### 출력

- `training_comparison.png`: 4개 모델 학습 곡선 비교
- 콘솔에 Best Val Loss / MAE 요약 테이블

---

## 전체 실행 예시 (시프트 -10도 적용)

```bash
# 1. 데이터 생성
python generate_training_data2.py -10 video_shifted_m10

# 2. 전처리
python preprocess.py video_shifted_m10

# 3. 학습
python train.py all processed_video_shifted_m10

# 4. 추론
python test_inference.py 20260715_224033 video_shifted_m10 results_shifted

# 5. 분석
python result_analysis.py 20260715_224033 results_shifted
```

---

## 참고사항

- 모든 모델은 `data_generator/` 폴더 내에 저장됩니다
- 모델 폴더명 형식: `model-<YYYYMMDD_HHMMSS>_<filter>`
- GPU(CUDA) 사용 가능 시 자동 감지하여 사용
- 학습 데이터는 원본 + 좌우 반전으로 2배 증강됩니다
