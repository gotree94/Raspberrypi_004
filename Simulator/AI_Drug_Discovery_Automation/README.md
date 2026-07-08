# AI Drug Discovery Automation Platform

**실제 AI/ML 기술을 활용한 신약 개발 전 과정 자동화 플랫폼**

AlphaFold 단백질 구조 예측, RDKit 분자 모델링, ML 기반 ADMET 예측, VAE/GAN 분자 생성, AutoDock Vina 도킹 자동화를 통합한 종단간(end-to-end) 신약 개발 자동화 시스템입니다.

![](AI_Drug_Discovery_Lab.png)

---

## 주요 기능 (Key Features)

| 모듈 | 기술 | 설명 |
|------|------|------|
| **AlphaFold 통합** | AlphaFold2/3 | 단백질 아미노산 서열 → 3D 구조 예측 (Docker/Colab/Local) |
| **분자 모델링** | RDKit | 분자 처리, 지문(Fingerprint) 계산, 기술자(Descriptor) 추출 |
| **가상 스크리닝** | 유사도 검색 + Pharmacophore | 화합물 라이브러리에서 히트 발굴 |
| **ADMET 예측** | ML 모델 (RF/XGB/DNN) | 흡수·분포·대사·배설·독성 예측 및 약물성 필터링 |
| **분자 생성** | VAE / GA / RL | 새로운 약물 후보 분자 *de novo* 설계 및 최적화 |
| **분자 도킹** | AutoDock Vina | 단백질-리간드 결합 친화도 예측 및 자세 분석 |
| **파이프라인** | DAG 워크플로우 + 상태 관리 | 종단간 자동화, 체크포인트/재시작, 병렬 실행 |
| **REST API** | FastAPI | 모든 기능을 HTTP API로 제공, WebSocket 실시간 모니터링 |
| **시각화** | matplotlib + py3Dmol | 분자 구조, ADMET 차트, 도킹 결과, 파이프라인 진행 |

---

## 프로젝트 구조

```
C:\AI_Drug_Discovery_Automation\
├── README.md
├── requirements.txt
├── docs/                           # 상세 문서 (한글/영문)
│   ├── 01_프로젝트_개요.md
│   ├── 02_시스템_아키텍처.md
│   ├── 03_AlphaFold_통합_가이드.md
│   ├── 04_분자_모델링_파이프라인.md
│   ├── 05_가상_스크리닝.md
│   ├── 06_ADMET_예측_모델.md
│   ├── 07_분자_생성_및_최적화.md
│   ├── 08_분자_도킹_자동화.md
│   ├── 09_자동화_워크플로우.md
│   ├── 10_API_레퍼런스.md
│   └── 11_설치_및_환경_설정.md
├── src/                            # 소스 코드
│   ├── config.py                   # 전역 설정
│   ├── alphafold/                  # AlphaFold 통합
│   │   ├── alphafold_wrapper.py
│   │   ├── alphafold_runner.py
│   │   └── pdb_processor.py
│   ├── molecular/                  # 분자 처리 (RDKit)
│   │   ├── rdkit_utils.py
│   │   ├── fingerprint.py
│   │   └── descriptors.py
│   ├── screening/                  # 가상 스크리닝
│   │   ├── similarity_search.py
│   │   ├── pharmacophore.py
│   │   └── library_manager.py
│   ├── admet/                      # ADMET 예측
│   │   ├── predictor.py
│   │   ├── models.py
│   │   └── filters.py
│   ├── generation/                 # 분자 생성
│   │   ├── vae_model.py
│   │   ├── molecular_optimizer.py
│   │   └── fragment_based.py
│   ├── docking/                    # 분자 도킹
│   │   ├── autodock_vina.py
│   │   ├── preparation.py
│   │   └── scoring.py
│   ├── pipeline/                   # 파이프라인
│   │   ├── orchestrator.py
│   │   ├── workflow_manager.py
│   │   ├── state_manager.py
│   │   └── job_scheduler.py
│   ├── api/                        # REST API
│   │   ├── rest_api.py
│   │   └── websocket.py
│   └── visualization/              # 시각화
│       ├── molecule_viewer.py
│       ├── dashboard.py
│       └── charts.py
├── scripts/                        # 실행 스크립트
│   ├── run_pipeline.py
│   ├── setup_environment.py
│   └── start_api.py
├── notebooks/                      # Jupyter 노트북
├── tests/                          # 테스트
└── data/                           # 데이터 저장소
    ├── compounds/                  # 화합물 라이브러리
    ├── proteins/                   # 단백질 구조 (PDB)
    ├── results/                    # 실행 결과
    ├── models/                     # 사전 학습 모델
    └── configs/                    # 설정 파일
```

---

## 기존 프로젝트와의 차별성

| 항목 | 기존 프로젝트 (시뮬레이터) | 본 프로젝트 (실제 AI) |
|------|------------------------|---------------------|
| AlphaFold | pLDDT 랜덤 생성 + tkinter GUI | 실제 AlphaFold2/3 바이너리/Colab 실행 |
| 분자 처리 | SMILES 길이만 계산 | RDKit 전체 기능 (지문, 기술자, 부분구조) |
| ADMET | 랜덤값 반환 | ML 모델 (RF/XGB/DNN) 기반 예측 |
| 분자 생성 | 미리 정의된 15개 분자 중 선택 | VAE 학습 모델로 *de novo* 생성 |
| 도킹 | 랜덤 친화도 생성 | 실제 AutoDock Vina 실행 |
| 파이프라인 | 단순 TCP 명령어 | DAG 워크플로우 + 상태 관리 + API |
| 통신 | TCP 소켓 (커스텀 프로토콜) | REST API (FastAPI) + WebSocket |

---

## 빠른 시작 (Quick Start)

### 1. Conda 환경 설정

```bash
conda create -n drug_discovery python=3.10
conda activate drug_discovery
```

### 2. RDKit 설치

```bash
conda install -c conda-forge rdkit
```

### 3. 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 설정

```bash
python scripts/setup_environment.py
```

### 5. API 서버 실행

```bash
python scripts/start_api.py
# http://localhost:8000/docs  (Swagger UI)
```

### 6. 전체 파이프라인 실행

```bash
python scripts/run_pipeline.py --target "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF" --workflow full
```

---

## 사용 예시

```python
from src.alphafold import AlphaFoldWrapper
from src.molecular.rdkit_utils import MolFromSMILES, calculate_all_descriptors
from src.admet.predictor import ADMETPredictor
from src.docking.autodock_vina import VinaDocker

# AlphaFold로 단백질 구조 예측
wrapper = AlphaFoldWrapper(backend="colab")
result = wrapper.predict_structure("MVLSPADKTNVKAAW...")
print(f"pLDDT: {result.plddt}")

# 분자 분석
mol = MolFromSMILES("CC(=O)Oc1ccccc1C(=O)O")
descriptors = calculate_all_descriptors(mol)

# ADMET 예측
predictor = ADMETPredictor()
admet_result = predictor.predict("CC(=O)Oc1ccccc1C(=O)O")

# 분자 도킹
docker = VinaDocker()
dock_result = docker.dock_smiles("CC(=O)Oc1ccccc1C(=O)O", exhaustiveness=16)
```

---

## 라이선스

MIT License

## 참고 문헌

- Jumper et al. "Highly accurate protein structure prediction with AlphaFold." Nature 2021
- Abramson et al. "Accurate structure prediction of biomolecular interactions with AlphaFold 3." Nature 2024
- Landrum, G. "RDKit: Open-Source Cheminformatics Software"
- Trott & Olson. "AutoDock Vina: improving the speed and accuracy of docking." J. Comput. Chem. 2010
- Gómez-Bombarelli et al. "Automatic chemical design using a data-driven continuous representation of molecules." ACS Cent. Sci. 2018
