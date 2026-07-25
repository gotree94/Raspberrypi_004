# TinyML 교육 - 하드웨어 없이 가능한 실습 가이드

## 개요

하드웨어(마이크로컨트롤러 보드) 없이도 TinyML의 핵심 개념과 실습을 충분히 수행할 수 있습니다.
PC/노트북 + 웹 브라우저만으로 전체 파이프라인을 학습할 수 있습니다.

---

## 1. Edge Impulse Studio (웹 기반) - 가장 쉬운 접근

**URL**: https://studio.edgeimpulse.com

브라우저에서 데이터 수집 → 학습 → 배포 전체를 수행할 수 있습니다.

### 실습 가능 항목

| 단계 | 내용 | 하드웨어 필요 |
|------|------|:---:|
| 데이터 수집 | 브라우저 마이크/웹캠으로 직접 수집 | X |
| 데이터 전처리 | MFCC, Spectrogram, Image 등 자동 생성 | X |
| 모델 학습 | 클라우드에서 학습 (무료) | X |
| 모델 테스트 | Live Classification으로 결과 확인 | X |
| 모델 프로파일링 | MCU 타겟별 RAM/ROM/지연시간 추정 | X |
| WebAssembly 배포 | 브라우저에서 바로 모델 실행 | X |

### 실습 예제

```
1. 가속도계 기반 동작 인식
   - 브라우저 마이크로 소리 데이터 수집
   - 또는 샘플 데이터셋 업로드
   → 음성 명령 인식 모델 학습

2. 이미지 분류
   - 웹캠으로 이미지 캡처
   - 또는 공개 데이터셋 활용
   → 이미지 분류 모델 학습

3. 이상 감지 (Anomaly Detection)
   - 정상 데이터만 학습
   → 비정상 감지 모델 학습
```

---

## 2. Edge Impulse Python SDK (PC에서 학습 + 배포)

**장점**: Python으로 모델을 학습하고, MCU 타겟용으로 프로파일링/배포까지 가능

### 환경 설정

```bash
pip install tensorflow edgeimpulse
```

### 실습: MNIST 손글씨 분류 → MCU 배포 시뮬레이션

```python
import tensorflow as tf
from tensorflow import keras
import edgeimpulse as ei

# 1. 데이터 로드
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
x_train = x_train.reshape(-1, 784).astype('float32') / 255.0
x_test = x_test.reshape(-1, 784).astype('float32') / 255.0

# 2. 간단한 신경망 학습
model = keras.Sequential([
    keras.layers.Dense(128, activation='relu', input_shape=(784,)),
    keras.layers.Dense(64, activation='relu'),
    keras.layers.Dense(10, activation='softmax')
])
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(x_train, y_train, epochs=5, batch_size=32)

# 3. MCU 타겟 프로파일링 (하드웨어 없이!)
devices = ei.model.list_profile_devices()
print("사용 가능한 타겟:", devices)

# Cortex-M4F 80MHz 기준으로 프로파일링
profile = ei.model.profile(model=model, device='cortex-m4f-80mhz')
print(profile.summary())
# → RAM, ROM, 추론 시간 등 출력

# 4. C++ 라이브러리로 배포
labels = [str(i) for i in range(10)]
deploy_bytes = ei.model.deploy(
    model=model,
    model_output_type=ei.model.output_type.Classification(labels=labels),
    model_input_type=ei.model.input_type.OtherInput(),
    deploy_target='zip'  # C++ 라이브러리
)

if deploy_bytes:
    with open('my_model_cpp.zip', 'wb') as f:
        f.write(deploy_bytes.getvalue())
    print("C++ 라이브러리 다운로드 완료")
```

### 학습 포인트
- 동일한 모델이 Cortex-M4(MCU)에서 차지하는 RAM/ROM을 시뮬레이션
- 모델 크기와 정확도의 트레이드오프 실험
- 양자화(Quantization) 전후 비교

---

## 3. Renode (MCU 시뮬레이터) - 가장 현실적인 시뮬레이션

**URL**: https://renode.io | **GitHub**: https://github.com/renode/renode

Renode는 실제 MCU 하드웨어를 시뮬레이션하는 오픈소스 프레임워크입니다.
TFLite Micro와 연동되어, **실제 바이너리**를 가상 MCU에서 실행할 수 있습니다.

### 지원 플랫폼
- Arduino Nano 33 BLE Sense (nRF52840)
- LiteX VexRiscv (RISC-V)
- STM32 시리즈
- ESP32 (제한적)

### 빠른 시작 (Google Colab에서 실행)

```python
# Colab에서 Renode + TFLite Micro 실행
# Harvard edX TinyML 코스에서 사용되는 방식

# 1. Renode 설치
!wget https://github.com/renode/renode/releases/download/v1.13.0/renode-1.13.0-linux-portable.zip
!unzip renode-1.13.0-linux-portable.zip

# 2. 매직 원드 데모 실행 (가속도계 제스처 인식)
!git clone https://github.com/antmicro/litex-vexriscv-tensorflow-lite-demo
%cd litex-vexriscv-tensorflow-lite-demo/renode
!./renode litex-vexriscv-tflite.resc -e "start"
```

### 실습 가능 항목

| 실습 | 내용 |
|------|------|
| Magic Wand | 가속도계 제스처 인식 (원, 기울기 등) |
| Person Detection | 사람 감지 (이미지 분류) |
| Speech Detection | 음성 감지 |
| 시리얼 UART 출력 | 가상 센서 데이터 → 추론 결과 확인 |
| 메모리 분석 | MCU 메모리 사용량 실시간 관찰 |

---

## 4. Wokwi (브라우저 기반 시뮬레이터)

**URL**: https://wokwi.com

ESP32, Arduino, STM32를 브라우저에서 시뮬레이션합니다.
TFLite Micro도 지원됩니다.

### 실습 예제

```
1. TinyML 코사인 예측기
   - ESP32에서 TFLite 모델 실행
   - 양자화(quantization) 과정 확인
   - 메모리 사용량 관찰

2. 가속도계 기반 동작 인식
   - 가상 MPU6050 센서 연동
   - 제스처 분류 결과 확인

3. 오디오 분류
   - 가상 마이크 입력
   - 키워드 인식 모델 실행
```

### 장점
- 코드를 바로 편집하고 실행
- GPIO, 센서 시뮬레이션
- 회로도 시각화
- 하드웨어 구매 불필요

---

## 5. tinyml-edge-inspector (브라우저 전용)

**GitHub**: https://github.com/Zhaosiqiang/tinyml-edge-inspector

센서 데이터 시뮬레이션 → 이상 감지 → MCU용 C 코드 생성까지 브라우저에서 수행합니다.

### 기능

| 기능 | 설명 |
|------|------|
| 센서 시뮬레이션 | 온도, 전압, ADC 등 가상 센서 데이터 생성 |
| 이상 감지 알고리즘 | EMA, Z-Score, Threshold, Linear Model 4가지 |
| C 코드 생성 | ARM Cortex-M용 자동 코드 생성 |
| 메모리 추정 | RAM/ROM 사용량 계산 |
| 지연시간 추정 | Cortex-M4 @ 48MHz 기준 |

### 실습

```bash
git clone https://github.com/Zhaosiqiang/tinyml-edge-inspector.git
cd tinyml-edge-inspector
npm install
npm run dev
# http://localhost:5173 접속
```

---

## 6. Qualcomm Device Cloud (클라우드 MCU)

**URL**: https://www.qualcomm.com/developer/software/qualcomm-device-cloud

물리적 하드웨어 없이 클라우드의 실제 Qualcomm 보드에서 추론을 실행할 수 있습니다.

- 무료 5,000분 제공
- Edge Impulse CLI 연동
- RB3 Gen 2 보드에서 AI 추론 테스트

---

## 추천 교육 커리큘럼 (하드웨어 없음)

### Part 1: TinyML 기초 (2주)

```
실습 1: Edge Impulse Studio 워크숍
  - https://studio.edgeimpulse.com 에서 계정 생성
  - 가속도계 샘플 프로젝트로 동작 인식
  - WebAssembly로 브라우저에서 추론 실행
  학습: 데이터 수집 → 전처리 → 학습 → 배포 전체 흐름

실습 2: Python SDK로 모델 프로파일링
  - TensorFlow로 간단한 모델 학습
  - ei.model.profile()로 MCU 타겟 분석
  - 양자화 전후 정확도/크기 비교
  학습: MCU 제약 조건 이해
```

### Part 2: 시뮬레이션 실습 (2주)

```
실습 3: Renode에서 TFLite Micro 실행
  - Magic Wand 제스처 인식 데모
  - 가상 가속도계 데이터로 추론 확인
  - UART 출력으로 결과 관찰
  학습: 실제 MCU 바이너리 실행 과정 이해

실습 4: Wokwi에서 ESP32 TinyML
  - TFLite 모델을 ESP32 시뮬레이터에서 실행
  - 양자화된 모델의 int8 연산 확인
  - 메모리 arena 크기 실험
  학습: 메모리 제약에서의 모델 최적화
```

### Part 3: 응용 프로젝트 (2주)

```
실습 5: tinyml-edge-inspector로 이상 감지
  - 센서 데이터 시뮬레이션
  - 4가지 알고리즘 비교
  - C 코드 생성 및 메모리 분석
  학습: 산업용 이상 감지 개념

실습 6: Edge Impulse + Python으로 이미지 분류
  - 공개 데이터셋으로 이미지 분류 모델 학습
  - 모델 크기 vs 정확도 실험
  - C++ 라이브러리 배포
  학습: 임베디드 배포 파이프라인
```

---

## 도구 비교표

| 도구 | 난이도 | 실습 가능 항목 | 브라우저 | 비용 |
|------|:---:|---------------|:---:|:---:|
| Edge Impulse Studio | 하 | 데이터수집, 학습, 배포, 테스트 | O | 무료 |
| Edge Impulse Python SDK | 중 | 학습, 프로파일링, 배포 | X | 무료 |
| Renode | 중상 | 실제 바이너리 실행, 센서 시뮬레이션 | X | 무료 |
| Wokwi | 중 | MCU 시뮬레이션, 회로 설계 | O | 무료 |
| tinyml-edge-inspector | 하 | 센서 시뮬레이션, 이상감지, C코드 생성 | O | 무료 |
| Qualcomm Device Cloud | 중 | 실제 클라우드 하드웨어 추론 | O | 무료 5000분 |

---

## 참고 자료

- [Edge Impulse 공식 문서](https://docs.edgeimpulse.com)
- [Renode TinyML 교육 사례](https://www.zephyrproject.org/using-renode-for-education-research-and-demonstration/)
- [Harvard edX TinyML 코스 (무료)](https://www.edx.org/course/tiny-machine-learning)
- [TensorFlow Lite Micro + Renode 튜토리얼](https://blog.tensorflow.org/2020/06/running-and-testing-tf-lite-on-microcontrollers.html)
- [Edge Impulse WebAssembly 가이드](https://docs.edgeimpulse.com/hardware/deployments/run-webassembly-browser)
