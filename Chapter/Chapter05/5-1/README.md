# 5-1 PyTorch란 무엇인가?

PyTorch의 특징은 TensorFlow에 비해 다루기 쉽고, 유연합니다. 직관적인 API를 제공하여 PyTorch의 인기가 높아지고 있습니다.
또한 PyTorch는 많은 연구에서 기본 딥러닝 프레임워크로 자리 잡았습니다. 많은 사용자를 확보하고 있습니다.
PyTorch(파이토치)는 파이썬 기반의 오픈소스 머신러닝 라이브러리로 페이스북의 AI 연구팀이 개발했습니다.
추천 시스템 등 다양한 연구 및 애플리케이션 분야에서 널리 활용되고 있습니다.
따라서,
이번 장에서는 파이썬 환경에서 PyTorch를 사용하기 위한 설치 방법 및 기초 활용법을 다룹니다.
파이썬 개발 환경인 Thonny IDE를 사용합니다.

## 라이브러리 설치

```Bash
pip install torch torchvision
```

## PyTorch 불러오기 & 버전 확인

PyTorch에서 가장 중요한 개념 중 하나는 데이터를 다루는 단위인 Tensor(텐서)입니다.

* 5_1_1.py

```Python
import torch

print("PyTorch version: ", torch.__version__)
print("Tensor test: ", torch.tensor([1, 2, 3]))
```

## 계산기처럼 사용하기

* 5_1_2.py

```Python
import torch

a = torch.tenso(3.0)
b = torch.tenso(2.0)
result=a*b+5
print('Result:",  result
```
