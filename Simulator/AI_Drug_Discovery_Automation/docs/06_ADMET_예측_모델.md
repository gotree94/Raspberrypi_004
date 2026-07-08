# 6. ADMET 예측 모델

## 6.1 개요

`src/admet/` 모듈은 머신러닝 모델을 기반으로 ADMET(흡수·분포·대사·배설·독성) 특성을 예측합니다.

## 6.2 지원 모델

| 모델 | 설명 |
|------|------|
| Random Forest | 기본 모델, 높은 해석 가능성 |
| XGBoost | 고성능 부스팅 모델 |
| Neural Network | PyTorch 기반 심층 신경망 |
| Ensemble | 모든 모델의 앙상블 예측 |

## 6.3 ADMET 예측

```python
from src.admet.predictor import ADMETPredictor

predictor = ADMETPredictor()

result = predictor.predict("CC(=O)Oc1ccccc1C(=O)O")

# 6개 카테고리 예측
print(result.predictions["physicochemical"])
print(result.predictions["absorption"])
print(result.predictions["distribution"])
print(result.predictions["metabolism"])
print(result.predictions["excretion"])
print(result.predictions["toxicity"])

# 종합 점수
print(f"Aggregate Score: {result.aggregate_score}")
```

## 6.4 약물성 필터

```python
from src.admet.filters import apply_filters

mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
results = apply_filters(mol, ["lipinski", "veber", "ghose", "pfizer"])

for filter_name, passed in results.items():
    print(f"{filter_name}: {'PASS' if passed else 'FAIL'}")
```
