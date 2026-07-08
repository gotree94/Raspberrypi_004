# 3. AlphaFold 통합 가이드

## 3.1 개요

AlphaFold 통합 모듈(`src/alphafold/`)은 단백질 아미노산 서열로부터 3차원 구조를 예측합니다.

## 3.2 지원 백엔드

| 백엔드 | 설명 | 필요 조건 |
|--------|------|-----------|
| `local` | 로컬 AlphaFold2 실행 | AlphaFold 설치, 모델 파라미터 |
| `docker` | Docker AlphaFold2 | Docker, GPU |
| `colab` | Google Colab 노트북 (기본값) | 인터넷 연결 |
| `alphafold3` | AlphaFold3 (설치된 경우) | AlphaFold3 바이너리 |

## 3.3 사용 예시

```python
from src.alphafold import AlphaFoldWrapper

wrapper = AlphaFoldWrapper(backend="colab")
result = wrapper.predict_structure(
    sequence="MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF",
)
print(f"pLDDT: {result.plddt}")
print(f"PDB path: {result.pdb_path}")
```

## 3.4 PDB 처리

```python
from src.alphafold.pdb_processor import PDBProcessor

processor = PDBProcessor()
structure = processor.load_pdb("output.pdb")
chain_a = processor.extract_chain(structure, "A")
plddt_scores = processor.get_plddt_scores(structure)
```

## 3.5 설정

```yaml
# config.yaml
alphafold:
  backend: colab
  num_models: 5
  use_amber_relax: true
  max_template_date: "2024-01-01"
  timeout_minutes: 60
```
