# 10. API 레퍼런스

## 10.1 기본 정보

- **기본 URL**: `http://localhost:8000/api`
- **Swagger UI**: `http://localhost:8000/api/docs`
- **형식**: JSON 요청/응답

## 10.2 시스템 엔드포인트

### Health Check
```
GET /api/health
```
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "modules_available": {
    "alphafold": true,
    "molecular": true,
    "admet": true,
    "docking": false
  }
}
```

## 10.3 분자 처리

### 분자 기술자 계산
```
POST /api/molecular/descriptors
Body: {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}
```

### 분자 지문 계산
```
POST /api/molecular/fingerprints
Body: {"smiles": "...", "fingerprint_types": ["morgan", "rdkit"]}
```

### 유사도 계산
```
POST /api/molecular/similarity
Body: {"smiles1": "...", "smiles2": "...", "metric": "tanimoto"}
```

## 10.4 ADMET

### ADMET 예측
```
POST /api/admet/predict
Body: {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}
```

### 약물성 필터
```
POST /api/admet/filter
Body: {"smiles": "...", "filters": ["lipinski", "veber"]}
```

## 10.5 스크리닝

### 유사도 검색
```
POST /api/screening/similarity
Body: {
  "query_smiles": "CCO",
  "library": ["CCO", "c1ccccc1", ...],
  "top_n": 10,
  "threshold": 0.5
}
```

## 10.6 분자 생성

### GA 생성
```
POST /api/generation/ga
Body: {
  "smiles_seeds": ["CCO", "c1ccccc1"],
  "num_samples": 10,
  "temperature": 1.0
}
```

### 단편 기반 설계
```
POST /api/generation/fragment
Body: {
  "core_smiles": ["c1ccccc1"],
  "side_chain_smiles": ["CCO", "CN"],
  "linker": "C"
}
```

## 10.7 도킹

### 분자 도킹
```
POST /api/docking/dock
Body: {
  "smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "receptor_pdbqt": "receptor.pdbqt",
  "center_x": 15.0,
  "center_y": 20.0,
  "center_z": 10.0
}
```

## 10.8 파이프라인

### 파이프라인 실행
```
POST /api/pipeline/run
Body: {"workflow_name": "full_pipeline", "inputs": {...}}
```

### 상태 확인
```
GET /api/pipeline/status/{pipeline_id}
```

### 템플릿 목록
```
GET /api/pipeline/templates
```

## 10.9 AlphaFold

### 구조 예측
```
POST /api/alphafold/predict
Body: {"sequence": "MVLSPAD...", "backend": "colab"}
```

## 10.10 WebSocket

```
WebSocket: ws://localhost:8000/ws

Subscribe: {"type": "subscribe", "topic": "pipeline_{id}"}
Receive: {"type": "stage_update", "data": {...}}
```
