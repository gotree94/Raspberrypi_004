## ML 도구의 전체 계층 구조

```
사용자 / 비즈니스 레이어
    └── ChatGPT, Claude, Gemini 등 (완성된 AI 서비스)

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

<br>
<br>

### JAX

```
JAX = Google DeepMind의 고성능 수치 연산 라이브러리
    ├── NumPy 호환 API (jax.numpy)
    ├── 자동미분 (grad, jacfwd, jacrev)
    ├── XLA JIT 컴파일 (즉시 최적화)
    ├── vmap (자동 벡터화)
    └── pmap (분산 병렬화)
```

- PyTorch/TensorFlow보다 **한 단계 낮은 수준**의 함수형 프레임워크
- **TPU에서 가장 빠른 성능** (Google TPU 전용)
- 주로 **고성능 연구, 대규모 모델 학습**에 사용
- Flax, Haiku, Elegy 등 상위 래퍼 라이브러리와 함께 사용
- 2026년 기준 급성장 중이지만 생태계는 PyTorch보다 작음

| 비교 | PyTorch | JAX |
|:---|:---|:---|
| 스타일 | 객체지향 (class, nn.Module) | 함수형 (순수 함수) |
| 코드 실행 | 즉시 실행 (eager) | JIT 컴파일 (jit 데코레이터) |
| 학습 곡선 | 중간 | 높음 |
| TPU 지원 | 제한적 | **최적** |

<br>
<br>

### scikit-learn

```
scikit-learn = 전통적인 머신러닝의 표준 라이브러리
    ├── 분류 (SVM, RandomForest, LogisticRegression)
    ├── 회귀 (LinearRegression, Ridge, Lasso)
    ├── 군집 (KMeans, DBSCAN)
    ├── 차원 축소 (PCA, t-SNE)
    └── 전처리 (StandardScaler, OneHotEncoder)
```

- **딥러닝을 하지 않음** — 신경망 기능 없음
- 데이터가 적거나(수천~수만 개) 테이블 형태일 때 가장 강력
- 사이킷런 → 결과가 안 좋으면 → 딥러닝(PyTorch)으로 넘어감
- 대부분의 ML 프로젝트에서 **데이터 전처리용으로 항상 먼저 사용됨**

```
[실제 워크플로우]
1. scikit-learn으로 데이터 전처리 (StandardScaler, PCA)
2. scikit-learn으로 빠른 테스트 (LogisticRegression 등)
3. 결과가 좋으면 → 배포 (사이킷런으로 충분)
4. 결과가 나쁘면 → PyTorch/TensorFlow 딥러닝 시도
```

<br>
<br>

### Apache Spark MLlib

```
Spark MLlib = 대용량 데이터 분산 머신러닝
    ├── 클러스터(여러 대의 서버)에서 작동
    ├── 수백 GB ~ TB 단위 데이터 처리
    ├── 분류/회귀/군집/추천 시스템 지원
    └── Spark ML Pipeline API 제공
```

- **딥러닝이 아니라 빅데이터용 ML**
- 한 대의 PC 메모리에 데이터가 안 들어갈 때 사용
- PyTorch/TensorFlow는 단일 GPU 머신에 최적화
- Spark MLlib는 **수백 대 서버에 분산**해서 데이터 처리 + ML

| 구분 | Spark MLlib | PyTorch |
|:---|:---|:---|
| 데이터 크기 | TB 단위 | GB 단위 (GPU 메모리 한계) |
| 실행 환경 | CPU 클러스터 (수십~수백 대) | 단일 GPU 머신 |
| 주 용도 | 빅데이터 ETL + 전통 ML | 딥러닝 모델 학습 |

<br>
<br>

### ONNX (Open Neural Network Exchange)

```
ONNX = 프레임워크 간 모델 교환 표준 포맷
    ├── PyTorch → ONNX → TensorFlow Lite (모바일)
    ├── PyTorch → ONNX → NVIDIA Triton (GPU 서빙)
    ├── TensorFlow → ONNX → ONNX Runtime (어디서든)
    └── 어떤 프레임워크든 → ONNX → 어떤 환경이든
```

- **모델을 학습하는 도구가 아님** — 학습된 모델을 변환하고 추론만 함
- 한 번 `.onnx` 파일로 저장하면 프레임워크 종속성에서 해방
- ONNX Runtime (Microsoft)이 가장 널리 쓰이는 추론 엔진
- 양자화(INT8, FP16) 등 최적화 기능 내장 → 모바일/엣지에 필수

```
[실전 예: PyTorch 모델 → 모바일 배포]
PyTorch 학습 → torch.onnx.export() → .onnx 파일
                                    ↓
                     onnxruntime-mobile (Android/iOS)
                                    ↓
                         스마트폰에서 즉시 추론
```

<br>
<br>

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

<br>
<br>

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

<br>
<br>

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


<br>
<br>

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

<br>
<br>

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
