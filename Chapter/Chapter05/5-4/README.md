* # 5-4 신경망 기본 구성

* PyTorch를 사용하여 간단한 신경망을 구성하고 학습시키는 방법을 배웁니다.
* nn.Module을 이용한 모델 정의, 순전파와 역전하, 손실 함수 및 옵티마이저 설정 과정을 실습합니다.
이 과정을 통해 인공지능 모델의 기본 구조를 이해하고, 이후 자율주행 모델 학습에 으용양할 수 있는 기반을 마련랍니다.

## Lisnear 레이어로 순전파(Forward)이해

* Pytorch의 가장 기본 신경망 구성 단위인 nn.Linuar를 사용하겨
* 입력 데이터를 모델에 통과시켰을때 어떤 계산이 일어나는지 확인합니다.
* nn.Linear(1,1)은 y = Wx + b 형태의 1차 함수 이며,
* 파라미터(W,b)는 PyTorch가 자동으로 생성하고 초기화 합니다.

* 5_4_1.py

```python
import torch
import torch.nn as nn

x = torch.tensor([[1.0],[2.0],[3.0]])
model = nn.Linear(1, 1)

y = model(x)
w = list(model.parameters())[0].detach()
b = list(model.parameters())[1].detach()

print("x shape:",  x.shape)
print("y shape:",  y.shape)
print("y:", y.detach().view(-1))
print("weight:",  w.view(-1))
print("bias:", b.view(-1))
```

```
x shape: torch.Size([3, 1])
y shape: torch.Size([3, 1])
y: tensor([-0.1180,  0.2978,  0.7137])
weight: tensor([0.4158])
bias: tensor([-0.5339])
```

## 손실함수 + 옵티마이저 + 한 사이클 학습

* 학습의 전체 흐름(순전파 -> 손실계산 -> 역전파 -> 파라미터 갱신)을 보여줍니다.
* 모델은 y = 2x + 1 형태의 관계를 학습하도록 만들어집니다.
* MSELoss()는 예측갑과 정답의 평균제좁오차를 계산하고,
* SGD 옵티마이저가 이를 줄이기 위해 가중치를 업데이트 합니다.

* 5_4_2.py

```python
import torch
import torch.nn as nn 
import torch.optim as optim

x = torch.tensor([[1.0],[2.0],[3.0],[4.0]])
y = torch.tensor([[3.0],[5.0],[7.0],[9.0]])

model = nn.Linear(1,1)
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=0.05)

for epoch in range(200):
  optimizer.zero_grad()
  pred = model(x)
  loss = criterion(pred, y)
  loss.backward()
  optimizer.step()

test = torch.tensor([[5.0]])
print("loss:", loss.item())
print("predict(5):", model(test).item())
```

```
loss: 1.6655063518555835e-05
predict(5): 10.993108749389648
```

## ReLu를 포함한 간단 MLP학습

* 여러개의 입력(feature)을 받아 처리하는 신경망(MLP)을 구성하고 학습합니다.
* nn.Sqeuential()을 사용하여 2-> 8 -> 1 구조로 레이어를 쌓고,
* ReLU()활성함수를 추가해 비선형 모델을 만듭니다.
* 목표 함수는 간단히  y = x1 + x2관계를 학습하도록 설정했습니다.

* 5_4_3.py

```python
import torch
import torch.nn as nn
import torch.optim as optim

torch. manual_seed(0)
x = torch. tensor([[0.0, 1.0], [1.0,0.0], [1.0,2.0],[2.0,3.0], [3.0,4.0]])
y = x.sum(dim=1, keepdim=True)

model = nn.Sequential(
    nn.Linear(2,8),
    nn. ReLU(),
    nn.Linear(8,1)
)

criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.05) 

for epoch in range(300):
    optimizer. zero_grad()
    pred = model(x)
    loss = criterion(pred, y)
    loss.backward()
optimizer.step()

test = torch.tensor([[3.0, 4.0]])
print("loss:",  loss.item())
print("predict([3,4]):",  model(test).item())
```

```
loss: 23.432926177978516
predict([3,4]): -0.6190372705459595
```

## 모델 저장/불러오기(state_dict)와 추론

* 학습된 모델을 저장하고 다시 불러오는 방법을 보여줍니다.
* state_dict는 모델의 파라미터(W,b등)를 사전(dict) 형태로 저장하며,
* 다시 불러오면 삭습된 가중치 상태를 그대로 복원할 수 있습니다.

* 5_4_4.py

```python
import torch
import torch.nn as nn
import torch.optim as optim

x = torch.tensor([[1.0], [2.0], [3.0], [4.0]])
y = torch.tensor([[3.0], [5.0], [7.0], [9.0]])

model = nn.Linear(1, 1)
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=0.05)

for epoch in range(200):
    optimizer. zero_grad()
    pred = model(x)
loss = criterion(pred, y)
loss.backward()
optimizer.step()

before = model(torch.tensor([[5.0]])).item()
torch.save(model.state_dict(),"linear_1x1.pth") 

new_model = nn.Linear(1 ,1)
new_model.load_state_dict(torch.load("linear_1x1.pth"))
after = new_model(torch.tensor([[5.0]])).item()

print("predict before save:", before)
print("predict af ter load:", after)
```

```
predict before save: 8.958409309387207
predict af ter load: 8.958409309387207
```

