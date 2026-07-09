![](Pytorch_005.png)

---

## ML 도구의 전체 계층 구조

```
사용자 / 비즈니스 레이어
    ├── ChatGPT, Claude, Gemini 등 (완성된 AI 서비스)

AI 플랫폼 / MLOps 레이어 (모델 개발~배포 통합 관리)
    ├── AWS SageMaker           — AWS의 완전관리형 ML 플랫폼
    ├── Microsoft Azure AI      — Azure OpenAI + AI Foundry + ML Studio
    ├── Databricks              — 데이터+AI 통합 플랫폼 (Spark 기반)
    ├── NVIDIA AI Enterprise    — GPU 인프라 + CUDA + Triton + NeMo
    └── Google Vertex AI        — GCP의 ML 플랫폼

애플리케이션 레이어
    ├── 🤗 Hugging Face Transformers  (사전학습 모델 바로 사용)
    ├── LangChain / LlamaIndex        (LLM 앱 개발)
    └── Keras                         (고수준 API, 멀티백엔드)

프레임워크 레이어 (모델 학습/정의)
    ├── PyTorch     — 연구·LLM·동적 그래프 (Meta)
    ├── TensorFlow  — 프로덕션·모바일·정적 그래프 (Google)
    └── JAX         — 고성능·함수형·TPU (Google DeepMind)

전통 ML / 전처리
    └── scikit-learn  — 회귀·분류·군집·전처리

빅데이터 / 분산 처리
    └── Apache Spark MLlib  — 대용량 데이터 분산 ML

모델 교환 / 추론
    └── ONNX  — 프레임워크 간 모델 변환 표준 포맷

인프라 레이어 (GPU / 컴퓨팅)
    ├── NVIDIA CUDA + cuDNN  — GPU 가속 기반
    ├── NVIDIA Triton Inference Server  — 고성능 모델 서빙
    └── Docker / Kubernetes  — 컨테이너 오케스트레이션
```

---

## 추가된 항목 설명

### AWS SageMaker

```
SageMaker = AWS의 완전관리형 ML 플랫폼
    ├── 데이터 준비 (SageMaker Data Wrangler)
    ├── 모델 학습 (분산 학습, 자동 하이퍼파라미터 튜닝)
    ├── 모델 배포 (SageMaker Inference, Serverless)
    └── MLOps (파이프라인, 모니터링, A/B 테스트)
```

- **내부에서 PyTorch/TensorFlow 둘 다 지원**
- 코드 없이 AutoML 가능 (SageMaker Autopilot)
- 주로 **기업 프로덕션 환경**에서 사용

### Microsoft Azure AI

```
Azure AI = Microsoft의 AI 플랫폼 스택
    ├── Azure OpenAI Service  — GPT-4/5 등 API
    ├── Azure AI Foundry      — 통합 AI 개발 스튜디오
    ├── Azure ML Studio       — 노코드 ML (드래그 앤 드롭)
    └── Azure AI Search + Bot — RAG + 챗봇
```

- **OpenAI 모델을 Azure에서 독점 제공** (기업용)
- Copilot 생태계와 통합
- 주로 **Microsoft 기반 기업**에서 사용

### Databricks

```
Databricks = "데이터 + AI 통합 플랫폼"
    ├── Apache Spark 기반 (빅데이터 처리)
    ├── MLflow 포함 (모델 실험 추적, 레지스트리)
    ├── Unity Catalog (데이터 거버넌스)
    └── Model Serving (LLM 배포)
```

- **원래는 빅데이터 플랫폼**이었으나, AI 기능을 통합
- MLflow가 사실상 **ML 실험 추적의 표준**
- 데이터 엔지니어링 + ML을 한 곳에서

### NVIDIA AI Enterprise

```
NVIDIA AI Enterprise = GPU 인프라 + AI 소프트웨어 묶음
    ├── CUDA + cuDNN + TensorRT  (GPU 가속)
    ├── Triton Inference Server   (모델 서빙)
    ├── NeMo                      (LLM 학습/파인튜닝)
    ├── Riva                      (음성 AI)
    └── TAO Toolkit               (전이학습)
```

- **하드웨어(GPU) + 소프트웨어를 함께 제공**
- PyTorch/TensorFlow 모두 위에서 동작
- 주로 **자체 GPU 인프라를 운영하는 기업** 대상

---

## 전체 흐름 예시

### 시나리오: 기업의 LLM 파인튜닝 프로젝트

```
1. Databricks 에서 데이터 전처리 (Spark로 수백 GB 정제)
2. NVIDIA AI Enterprise (NeMo) 로 PyTorch 기반 LLM 파인튜닝
3. ONNX 로 모델 변환
4. SageMaker 또는 Azure AI 에 배포
5. Triton Inference Server 로 추론 (NVIDIA GPU)
```

### 각 레이어의 역할

| 레이어 | 예시 | 하는 일 |
|:---|:---|:---|
| **인프라** | NVIDIA CUDA, K8s | GPU 할당, 컨테이너 실행 |
| **프레임워크** | PyTorch, TensorFlow | 모델 학습 코드 |
| **ML 플랫폼** | SageMaker, Azure, Databricks | 위 모든 것을 **관리·자동화** |
| **애플리케이션** | Hugging Face, LangChain | 사전학습 모델 활용 |
| **사용자** | ChatGPT, Claude | 완성된 제품 |

### 언제 무엇을 쓰나?

| 상황 | 추천 조합 |
|:---|:---|
| "GPU 없는데 클라우드에서 ML 하고 싶다" | **SageMaker** 또는 **Azure AI** |
| "이미 Spark 쓰는데 ML도 추가하고 싶다" | **Databricks** |
| "자체 GPU 서버 있는데 최대 성능 내고 싶다" | **NVIDIA AI Enterprise** |
| "스타트업인데 빠르게 MVP 만들고 싶다" | **Hugging Face + Keras** |
| "연구 논문 구현해야 한다" | **PyTorch + JAX** |



![](Pytorch_004.png)


---

## 1장: 파이토치 기초 - 텐서와 동적 계산 그래프
첫 번째 이미지는 파이토치의 가장 기초가 되는 텐서(Tensor)의 개념과, <br> 
파이토치를 다른 프레임워크와 차별화시키는 '동적 계산 그래프(Dynamic Computational Graph)'의 원리를 설명합니다.

1. 계산기처럼 사용하는 텐서 수학: <br>
   코드를 직접 입력하는 것처럼 텐서 $A$, $B$를 정의하고 연산하는 과정을 시각화하여, <br>
   파이토치가 얼마나 직관적이고 쉬운지 보여줍니다.
2. 하드웨어 가속: <br>
   데이터를 CPU 텐서에서 GPU 텐서로 이동시키는 과정을 직관적으로 표현하여, 대규모 계산을 위한 하드웨어 활용 능력을 강조합니다.
3. 동적 계산 그래프 (Dynamic Graph): <br>
   requires_grad=True로 설정된 텐서들이 연산을 거치며 어떻게 실시간으로 노드(Tensor)와 엣지(연산, grad_fn)로 이루어진 계산 이력(History)을 <br>
   구축하는지 보여줍니다. 이 이력은 나중에 자동미분에 활용됩니다.

![](Pytorch_001.png)

## 2장: 학습 메커니즘 - 자동미분과 최적화 루프

두 번째 이미지는 파이토치가 구축된 계산 그래프를 어떻게 활용하여 학습(Learning)을 진행하는지 보여줍니다. <br> 
자동미분 엔진과 이를 최적화에 연결하는 전체 루프를 시각화했습니다.

1. 자동미분 엔진:
   * 단일 변수: 간단한 함수 $y = f(x)$에서 점의 기울기($dy/dx$)를 계산하는 기초적인 자동미분을 시각화합니다.
   * 다변수 그래디언트: 여러 변수($x$, $z$)에 대한 손실 함수(Loss function)의 지형도(3D 맵)를 보여주고, <br>
     각 변수에 대한 편미분값들이 어떻게 그래디언트 벡터($\nabla y$)로 합쳐져 최적의 방향을 제시하는지 표현합니다.
3. 최적화 루프 및 학습:
   * 순방향 패스(Forward Pass)로 데이터를 처리해 손실을 계산합니다.
   * 역방향 패스(Backward Pass) - 오차 역전파: 1장에서 구축된 동적 계산 그래프를 따라 빛(Error)이 거꾸로 흐르며 각 파라미터의 기울기를 계산하는 과정을 시각화합니다.
   * 최적화 단계(Optimizer Step): Adam, SGD와 같은 다양한 최적화 알고리즘(Optimizers)이 계산된 그래디언트를 이용해 파라미터를 업데이트하여 손실을 최소화하는 과정을 보여줍니다.

![](Pytorch_002.png)

## 3장: 파이토치 생태계 - 복잡한 시스템 구축 및 배포
마지막 이미지는 파이토치의 저수준 기능들이 어떻게 고수준 라이브러리와 연결되어 실제적이고 복잡한 딥러닝 시스템을 구축하는지 보여줍니다.

1. 모듈형 빌딩 블록 (torch.nn): Conv2d, Linear와 같이 미리 구현된 다양한 레이어(Module)를 레고 블록처럼 조립하여 복잡한 신경망 아키텍처를 구성하는 과정을 시각화합니다.
2. 풍부한 생태계 및 확장성:
    * 다양한 데이터 처리: 이미지, 텍스트, 오디오 등 다양한 데이터를 DataLoader를 통해 효율적으로 로드하고 처리하는 과정을 보여줍니다.
    * 사전 학습된 모델 및 도메인: TorchVision, TorchText와 같은 라이브러리를 통해 이미 학습된 고성능 모델(ResNet, BERT 등)을 가져와 <br>
      자신의 작업에 맞게 미세 조정(Transfer Learning)하는 전이 학습 과정을 직관적으로 표현합니다.
    * 커스텀 모듈 및 연구: 자신만의 고유한 신경망 블록을 직접 디자인하여 기존 아키텍처에 완벽하게 통합하는 연구 및 확장 과정을 시각화하여, 파이토치가 유연하고 연구 친화적임을 강조합니다.

![](Pytorch_003.png)



### ML 프레임워크 Top 10 (2026년)

| 순위	| 프레임워크	| 개발사	| 시장 점유율 / 사용 지표	| 주요 강점 | 
|:----:|:----:|:----:|:----:|:----:|
| 1	| PyTorch	| Meta	| 연구 논문 85%, 기업 17,196개, 채용공고 37.7%	| 연구·LLM·동적 그래프 | 
| 2	| TensorFlow	| Google	| 시장 점유율 37.5%, 기업 25,099개	| 프로덕션·모바일·TPU | 
| 3	| JAX	Google|  DeepMind	| 급성장 중, TPU 최적화	| 고성능 연구·함수형 | 
| 4	| scikit-learn	| 커뮤니티	| 전통 ML 표준 라이브러리	| 쉬운 사용성·전통 ML | 
| 5	| Keras 3	| Google	| 멀티백엔드 (PT/TF/JAX)	| 로우코드 프로토타이핑 | 
| 6	| ONNX Runtime	| Microsoft	| npm 다운로드 560만/월	| 크로스플랫폼 추론 | 
| 7	| Apache Spark MLlib	| Apache	| 빅데이터 ML 표준	| 분산 처리·대용량 데이터 | 
| 8	| XGBoost / LightGBM	| 커뮤니티	| 테이블 데이터 최강	| 그래디언트 부스팅 | 
| 9	| Hugging Face Transformers	| Hugging Face	| 허브 모델 87% PyTorch 기반	| NLP/멀티모달 최신 모델 | 
| 10	| LangChain	| LangChain	| LLM 앱 개발 표준	| RAG·에이전트·체인 | 
