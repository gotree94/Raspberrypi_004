# 에이전트 프로토콜 정의

## 1. AlphaFold Agent (`alphafold_agent.py`)

### Port: 50061

### 명령어

| 명령어 | 파라미터 | 설명 | 응답 예 |
|---|---|---|---|
| `PREDICT` | `<sequence>` | 단백질 구조 예측 | `PREDICT_SUCCESS:pLDDT=87.3` |
| `STATUS` | - | 모터/센서 상태 조회 | `SUCCESS:{"motors":{...},"sensors":{...}}` |
| `CONFIDENCE` | - | pLDDT 점수 조회 | `SUCCESS:92.1` |
| `RESET` | - | 초기화 | `SUCCESS:RESET_DONE` |

### Computational Motors

| Motor ID | 이름 | 실행 시간 (모의) |
|---|---|---|
| M1 | MSA Build (Multiple Sequence Alignment) | 3-8초 |
| M2 | Template Search | 2-5초 |
| M3 | Model Inference (5 models) | 5-15초 |
| M4 | Relaxation (AMBER) | 2-4초 |
| M5 | Confidence Scoring | 1-2초 |

### AI Sensors

| Sensor ID | 이름 | 범위 | 설명 |
|---|---|---|---|
| S1 | pLDDT | 0-100 | 예측 신뢰도 (LDDT) |
| S2 | PAE | 0-30 | Predicted Aligned Error |
| S3 | Coverage | 0-100% | MSA coverage |
| S4 | Seq Length | 50-2000 | 입력 서열 길이 |

---

## 2. Docking Agent (`docking_agent.py`)

### Port: 50062

### 명령어

| 명령어 | 파라미터 | 설명 | 응답 예 |
|---|---|---|---|
| `DOCK` | `<smiles>` | 분자 도킹 실행 | `DOCK_SUCCESS:-9.8` |
| `SCORE` | - | 현재 최고 점수 조회 | `SUCCESS:-9.8` |
| `STATUS` | - | 상태 조회 | `SUCCESS:{"motors":{...},"sensors":{...}}` |
| `RESET` | - | 초기화 | `SUCCESS:RESET_DONE` |

### Computational Motors

| Motor ID | 이름 | 실행 시간 (모의) |
|---|---|---|
| M1 | Protein Preparation | 2-4초 |
| M2 | Ligand Preparation | 1-3초 |
| M3 | Grid Generation | 3-6초 |
| M4 | Docking Simulation | 5-20초 |
| M5 | Scoring & Ranking | 1-2초 |

### AI Sensors

| Sensor ID | 이름 | 범위 | 설명 |
|---|---|---|---|
| S1 | Best Affinity | -15~0 kcal/mol | 최고 결합 친화도 |
| S2 | Avg Affinity | -12~0 kcal/mol | 평균 결합 친화도 |
| S3 | RMSD | 0-10 Å | 도킹 자세 RMSD |
| S4 | H-Bonds | 0-10 | 수소 결합 수 |

---

## 3. ADMET Agent (`admet_agent.py`)

### Port: 50063

### 명령어

| 명령어 | 파라미터 | 설명 | 응답 예 |
|---|---|---|---|
| `PREDICT` | `<smiles>` | ADMET 속성 예측 | `PREDICT_SUCCESS:QED=0.78,LogP=2.3` |
| `FILTER` | `<smiles>` | 약물성 필터 통과 여부 | `FILTER_SUCCESS:PASS` |
| `STATUS` | - | 상태 조회 | `SUCCESS:{"motors":{...},"sensors":{...}}` |
| `RESET` | - | 초기화 | `SUCCESS:RESET_DONE` |

### Computational Motors

| Motor ID | 이름 | 실행 시간 (모의) |
|---|---|---|
| M1 | Absorption Prediction | 1-3초 |
| M2 | Distribution Prediction | 1-3초 |
| M3 | Metabolism Prediction | 2-4초 |
| M4 | Excretion Prediction | 1-2초 |
| M5 | Toxicity Prediction | 2-5초 |

### AI Sensors

| Sensor ID | 이름 | 범위 | 설명 |
|---|---|---|---|
| S1 | QED Score | 0-1 | Quantitative Estimate of Drug-likeness |
| S2 | LogP | -2~10 | 옥탄올-물 분배계수 |
| S3 | Solubility | -10~2 logS | 수용해도 |
| S4 | BBB Score | 0-1 | Blood-Brain Barrier 투과성 |
| S5 | hERG Risk | 0-100% | hERG 독성 위험도 |
| S6 | LD50 | 1-5000 mg/kg | 급성 독성 |

---

## 4. Molecule Generator (`molecule_generator.py`)

### Port: 50064

### 명령어

| 명령어 | 파라미터 | 설명 | 응답 예 |
|---|---|---|---|
| `GENERATE` | `<property>` | 신규 분자 생성 | `GENERATE_SUCCESS:CC(=O)Oc1ccccc1C(=O)O` |
| `OPTIMIZE` | `<smiles>` | 기존 분자 최적화 | `OPTIMIZE_SUCCESS:CC(=O)Oc1ccccc1C` |
| `STATUS` | - | 상태 조회 | `SUCCESS:{"motors":{...},"sensors":{...}}` |
| `RESET` | - | 초기화 | `SUCCESS:RESET_DONE` |

### Computational Motors

| Motor ID | 이름 | 실행 시간 (모의) |
|---|---|---|
| M1 | VAE Encoding | 2-4초 |
| M2 | Latent Space Sampling | 1-2초 |
| M3 | Molecular Decoding | 2-5초 |
| M4 | Property Filtering | 1-3초 |
| M5 | Reinforcement Optimization | 3-8초 |

### AI Sensors

| Sensor ID | 이름 | 범위 | 설명 |
|---|---|---|---|
| S1 | QED Score | 0-1 | 약물 유사도 |
| S2 | SA Score | 1-10 | 합성 가능성 (1=쉬움) |
| S3 | LogP | -2~10 | 지용성 |
| S4 | Molecular Weight | 100-1000 Da | 분자량 |
| S5 | HBD/HBA | 0-15 | 수소 결합 공여/수용체 |

---

## 5. Virtual Screener (`virtual_screener.py`)

### Port: 50065

### 명령어

| 명령어 | 파라미터 | 설명 | 응답 예 |
|---|---|---|---|
| `SCREEN` | `<smiles>` | 유사도 기반 스크리닝 | `SCREEN_SUCCESS:hits=42` |
| `FILTER` | `<criteria>` | 속성 기반 필터링 | `FILTER_SUCCESS:remaining=128` |
| `STATUS` | - | 상태 조회 | `SUCCESS:{"motors":{...},"sensors":{...}}` |
| `RESET` | - | 초기화 | `SUCCESS:RESET_DONE` |

### Computational Motors

| Motor ID | 이름 | 실행 시간 (모의) |
|---|---|---|
| M1 | Library Loading | 2-5초 |
| M2 | Fingerprint Calculation | 3-8초 |
| M3 | Similarity Search | 4-10초 |
| M4 | Pharmacophore Matching | 3-6초 |
| M5 | Hit Clustering | 2-4초 |

### AI Sensors

| Sensor ID | 이름 | 범위 | 설명 |
|---|---|---|---|
| S1 | Library Size | 1K-10M | 라이브러리 크기 |
| S2 | Hit Count | 0-10K | 히트 수 |
| S3 | Hit Rate | 0-100% | 히트율 |
| S4 | Diversity Score | 0-1 | 히트 다양성 |
| S5 | Enrichment Factor | 1-100 | 농축 인자 |
