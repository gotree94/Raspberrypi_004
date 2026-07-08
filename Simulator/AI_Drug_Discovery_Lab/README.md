# AI Drug Discovery Automation Lab

**AI 기반 신약 개발 자동화 시스템**: AlphaFold 단백질 구조 예측부터 가상 스크리닝, ADMET 예측, 분자 생성까지 Closed-Loop 자동화

![](AI_Drug_Discovery_Lab.png)

## 개요

본 프로젝트는 Self-Driving Lab 개념을 AI 기반 신약 개발 파이프라인에 적용한 시스템입니다. 각각의 AI 에이전트가 독립적인 TCP 서버로 동작하며, 오케스트레이터가 이들을 조율하여 Closed-Loop 약물 발견 워크플로우를 자동으로 실행합니다.

```
Target Protein → AlphaFold 예측 → 분자 도킹 → ADMET 필터 → 분자 생성 → 재도킹 (Closed-Loop)
```

## 시스템 구성

| 에이전트 | 포트 | 역할 | AI 기술 |
|---|---|---|---|
| AlphaFold Agent | 50061 | 단백질 3차 구조 예측 | DeepMind AlphaFold2 |
| Docking Agent | 50062 | 분자 도킹 시뮬레이션 | AutoDock Vina / Glide |
| ADMET Agent | 50063 | 약물성/독성 예측 | DeepChem / RDKit |
| Molecule Generator | 50064 | 신규 분자 생성 | VAE / GAN / Reinforcement Learning |
| Virtual Screener | 50065 | 가상 스크리닝 | 유사도 검색 / Pharmacophore |
| Orchestrator | 50060 | 중앙 워크플로우 조정 | Closed-Loop 최적화 |

## 핵심 개념

### Motor-Sensor 아키텍처
각 AI 에이전트는 물리적 장비 대신 **컴퓨테이셔널 모터(Computational Motor)** 와 **AI 센서(AI Sensor)** 로 구성됩니다:

- **Computational Motor**: AI 모델의 실행 단계 (예: MSA 구축, Model Inference, Docking)
- **AI Sensor**: 결과의 품질 지표 (예: pLDDT 점수, 결합 친화도, ADMET 속성)

### Closed-Loop 최적화
1. **AlphaFold**가 표적 단백질 구조 예측
2. **Docking Agent**가 화합물 라이브러리와 도킹
3. **ADMET Agent**가 상위 히트의 약물성 평가
4. **Molecule Generator**가 ADMET 결과 기반 최적화
5. 최적화된 분자 → 재도킹 (반복)

## 실행 방법

```bash
cd AI_Drug_Discovery_Lab

# 전체 시스템 자동 실행 + 통합 테스트
python src/test_runner.py --auto

# 특정 테스트만 실행
python src/test_runner.py T3 --auto

# 개별 에이전트 실행 (수동)
python src/alphafold_agent.py
python src/docking_agent.py
python src/admet_agent.py
python src/molecule_generator.py
python src/virtual_screener.py
python src/orchestrator.py
```

## 테스트 시나리오

| ID | 시나리오 | 설명 |
|---|---|---|
| T1 | Normal Discovery | 일반적인 신약 개발 워크플로우 |
| T2 | High Affinity Target | 높은 결합 친화도가 필요한 표적 |
| T3 | ADMET-First Filter | 약물성 우선 필터링 |
| T4 | Multi-Objective Optimization | 친화도 + ADMET 동시 최적화 |
| T5 | Multi-Target Screening | 여러 표적에 대한 선택성 스크리닝 |
| T6 | Stress / Edge Cases | 극한 조건에서의 시스템 안정성 |

## 디렉토리 구조

```
AI_Drug_Discovery_Lab/
├── README.md                    # 본 문서
├── docs/
│   ├── architecture.md          # 시스템 아키텍처
│   ├── concept.md               # 개념 및 방법론
│   └── protocols.md             # 프로토콜 정의
├── src/
│   ├── alphafold_agent.py       # AlphaFold 예측 에이전트
│   ├── docking_agent.py         # 분자 도킹 에이전트
│   ├── admet_agent.py           # ADMET 예측 에이전트
│   ├── molecule_generator.py    # 분자 생성 에이전트
│   ├── virtual_screener.py      # 가상 스크리닝 에이전트
│   ├── orchestrator.py          # 중앙 워크플로우 조정
│   └── test_runner.py           # 통합 테스트 러너
├── tests/
│   ├── test_plan_01_normal.json
│   ├── test_plan_02_high_affinity.json
│   ├── test_plan_03_admet_filter.json
│   ├── test_plan_04_multi_obj.json
│   ├── test_plan_05_multi_target.json
│   └── test_plan_06_stress.json
└── data/
    └── (실행 결과 저장)
```

## 의존성

- Python 3.10+
- 표준 라이브러리만 사용 (tkinter, socket, json, threading)

> **참고**: 실제 AlphaFold, AutoDock Vina, DeepChem 등의 외부 도구는 본 시뮬레이션에 포함되지 않습니다. 각 에이전트는 실제 AI 도구의 동작을 모사한 시뮬레이터로, TCP/IP 명령어 프로토콜과 Closed-Loop 자동화 개념을 검증하기 위한 목적입니다.
