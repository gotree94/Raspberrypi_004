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
