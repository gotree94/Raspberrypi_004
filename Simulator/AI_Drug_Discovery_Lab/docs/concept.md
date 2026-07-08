# 개념 및 방법론 (Concept & Methodology)

## 1. Self-Driving Lab for Drug Discovery

**Self-Driving Lab (SDL)** 은 실험 설계, 실행, 데이터 수집, 분석을 자동화된 루프로 통합하는 개념입니다. 본 프로젝트는 이 SDL 개념을 **AI 기반 신약 개발 컴퓨테이셔널 워크플로우**에 적용합니다.

### 물리적 SDL → AI Drug Discovery SDL 대응

| 물리적 SDL 컴포넌트 | AI Drug Discovery SDL |
|---|---|
| Liquid Handler | AlphaFold Agent (단백질 구조 예측) |
| Plate Reader | Docking Agent (분자 상호작용 측정) |
| Centrifuge | ADMET Agent (약물성 분석) |
| Plate Hotel | Virtual Screener (화합물 라이브러리 관리) |
| Motor (물리적 구동) | Computational Motor (AI 모델 실행 단계) |
| Sensor (물리적 측정) | AI Sensor (품질 지표) |
| Sample | Molecule (SMILES 구조) |
| Protocol | Workflow Pipeline (JSON 정의) |

## 2. AI Technologies in Drug Discovery

### AlphaFold (단백질 구조 예측)

- **원리**: Multiple Sequence Alignment (MSA) + Transformer 기반 구조 예측
- **입력**: 아미노산 서열 (FASTA)
- **출력**: 3D 좌표 (PDB) + pLDDT/P AE 신뢰도 점수
- **본 시뮬레이션**: 서열 길이와 진화 정보에 기반한 pLDDT 점수 모사
  - pLDDT = max(0, min(100, 95 - len/100 + noise(±3)))

### 분자 도킹 (Molecular Docking)

- **원리**: 단백질-리간드 상호작용 에너지 계산
- **알고리즘**: AutoDock Vina, Glide, Gold
- **입력**: 단백질 구조 (PDB) + 리간드 (SMILES)
- **출력**: 결합 자세 + Binding Affinity (kcal/mol)
- **본 시뮬레이션**: 화합물 특성 기반 친화도 모사
  - Affinity = min(-5, -12 + HBD_count * 0.5 + LogP * 0.3 - rot_bonds * 0.2 + noise)

### ADMET 예측

- **ADMET**: Absorption, Distribution, Metabolism, Excretion, Toxicity
- **도구**: DeepChem, ADMET Predictor, Schrödinger QikProp
- **입력**: 분자 구조 (SMILES)
- **출력**: LogP, 용해도, BBB 투과성, CYP 억제, hERG 독성 등
- **본 시뮬레이션**: Lipinski Rule-of-5 + 분자 기술자 기반 모사

### AI 분자 생성 (Molecule Generation)

- **원리**: VAE, GAN, Reinforcement Learning
- **입력**: 속성 프로파일 (QED, LogP, MW 등)
- **출력**: 신규 분자 구조 (SMILES)
- **본 시뮬레이션**: Fragment-based 조합 + 속성 필터링

## 3. Closed-Loop 최적화 알고리즘

```
Algorithm: Closed-Loop Drug Discovery Optimization

Input:  target_sequence, compound_library, max_iterations
Output: optimized_molecules

1. structure = AlphaFold.predict(target_sequence)
2. hits = VirtualScreener.screen(compound_library, structure, top_n=100)
3. current_rpm = 1.0  (탐색 강도: 0.5=보수, 1.0=중간, 2.0=적극)

for iteration = 1 to max_iterations:
    // 도킹 스크리닝
    for each molecule in hits:
        affinity = DockingAgent.dock(molecule, structure, 
                                     exhaustiveness=current_rpm * 8)
    
    // ADMET 필터링
    filtered = []
    for each molecule in top_hits:
        admet = ADMETAgent.predict(molecule)
        if admet.passes_filter():
            filtered.append(molecule)
    
    // 측정: 평균 결합 친화도
    current_affinity = average([m.affinity for m in filtered])
    
    // 수렴 판단
    if abs(current_affinity - target_affinity) <= tolerance:
        return filtered  // CONVERGED!
    
    // RPM 조정 (탐색 vs 활용 균형)
    if current_affinity < target_affinity:  // 더 강한 결합 필요
        current_rpm = min(current_rpm * 1.2, 2.0)  // 탐색 강화
        new_molecules = MoleculeGenerator.optimize(filtered, 
                                                   strategy="explore")
    else:  // 결합 친화도 충분, 약물성 개선
        current_rpm = max(current_rpm * 0.9, 0.5)
        new_molecules = MoleculeGenerator.optimize(filtered, 
                                                   strategy="exploit")
    
    hits = new_molecules

return best_molecules
```

### RPM의 의미

물리적 원심분리기의 RPM을 차용한 **Computational RPM**은 탐색-활용 균형을 제어합니다:

| RPM | 의미 | 효과 |
|---|---|---|
| 0.5 | 보수적 탐색 (Exploit) | 기존 분자 미세 조정 |
| 1.0 | 균형 (Balanced) | 기본 탐색/활용 |
| 2.0 | 적극적 탐색 (Explore) | 새로운 화학 공간 탐색 |

## 4. Motor-Sensor 매트릭스

| 에이전트 | Computational Motors | AI Sensors |
|---|---|---|
| AlphaFold | MSA Build, Template Search, Model Inference (x5), Relaxation, Confidence Scoring | pLDDT, PAE, Coverage, Seq Length |
| Docking | Protein Prep, Ligand Prep, Grid Gen, Docking, Scoring | Best Affinity, Avg Affinity, RMSD, H-Bonds |
| ADMET | Absorption, Distribution, Metabolism, Excretion, Toxicity | LogP, Solubility, BBB, CYP, hERG, LD50 |
| Mol Generator | VAE Encoder, Latent Sampling, Decoder, Property Filter, Optimization | QED, SA Score, LogP, MW, HBD/HBA |
| Virtual Screener | Library Loading, Fingerprint Calc, Similarity Search, Pharmacophore, Clustering | Library Size, Hit Count, Hit Rate, Diversity |

## 5. 테스트 전략

| 계층 | 테스트 유형 | 설명 |
|---|---|---|
| Unit | Agent 단위 테스트 | 각 에이전트 개별 명령어 테스트 |
| Integration | Closed-Loop 통합 테스트 | T1~T6 워크플로우 실행 |
| Stress | 부하/극한 테스트 | 대량 화합물, 빠른 반복, 타임아웃 |
