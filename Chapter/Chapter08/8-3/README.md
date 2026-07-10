# 8-3 모델 불러와 테스트하기

*  라즈베리파이에서 학습된 모델을 불러와 예측 결과를 테스트 합니다.
*  카메라 영상을 입력으로 받아 모델의 출력 결과를 화면에 표시합니다.

## 모델 불러오기

* 저장왼 PyTorch모델을 불러와 정상적으로 동작하는지 테스트하는 코드를 작성합니다.
* 모델을 불러온 되 더미 입력을 넣어 출력을 확인함으로써 모델 로드가 성공했는지 검증합니다.

* 8_3_1.py

``` python
import torch

MODEL_PATH = ""

def main():
    model = torch.jit.load(MODEL_PATH, map_location="cpu")
    model.eval()
    torch.set_num_threads(1)
    x = torch.zeros(1, 3, 66, 200, dtype=torch.float32)
    with torch.no_grad():
        y = model(x)
    print('model_loaded:', type(model).__name__)
    print("dry_run_output: ", float(y.view(-1)[0].item()))

if __name__ == "__main__":
    main()
```

## 불로온 모델을 이요해서 각도 예측하기

* 8_3_2.py

```python


```


