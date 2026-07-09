# PyTorch vs TensorFlow 비교 실험: Fashion-MNIST

동일한 조건에서 PyTorch와 TensorFlow(Keras)로 Fashion-MNIST 분류 모델을 각각 구현하고, 정확도·속도·코드 길이를 비교합니다.

<br>

---

<br>

## 1. 실험 개요

| 항목 | 값 |
|:---|:---|
| **데이터셋** | Fashion-MNIST (28×28 흑백, 10클래스) |
| **모델 구조** | 입력(784) → Dense(128, ReLU) → Dense(64, ReLU) → Dense(10) |
| **에폭** | 10 |
| **배치 크기** | 64 |
| **옵티마이저** | Adam (lr=0.001) |
| **손실 함수** | CrossEntropyLoss (from logits) |
| **평가 지표** | 최종 테스트 정확도, 총 학습 시간, 파라미터 수 |

<br>

---

<br>

## 2. 실험 코드

### 2-A. PyTorch 버전

`compare_pytorch.py`

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import time

# ----------------------
# 1. 하이퍼파라미터
# ----------------------
BATCH_SIZE = 64
EPOCHS = 10
LR = 0.001

# ----------------------
# 2. 데이터 로드
# ----------------------
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

train_dataset = datasets.FashionMNIST(root='./data', train=True, download=True, transform=transform)
test_dataset  = datasets.FashionMNIST(root='./data', train=False, download=True, transform=transform)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader  = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

# ----------------------
# 3. 모델 정의
# ----------------------
class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(784, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 10)
        )

    def forward(self, x):
        return self.net(x)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = MLP().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=LR)

# ----------------------
# 4. 학습
# ----------------------
total_params = sum(p.numel() for p in model.parameters())
print(f"Device: {device}")
print(f"Params: {total_params:,}")
print(f"Train samples: {len(train_dataset)}, Test samples: {len(test_dataset)}")
print(f"{'Epoch':>6} | {'Train Loss':>10} | {'Train Acc':>9} | {'Test Acc':>8} | {'Time':>6}")
print("-" * 48)

start_time = time.time()
for epoch in range(1, EPOCHS + 1):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    epoch_start = time.time()

    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

    train_acc = 100 * correct / total
    avg_loss = running_loss / len(train_loader)

    # 테스트 정확도
    model.eval()
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            test_total += labels.size(0)
            test_correct += (predicted == labels).sum().item()
    test_acc = 100 * test_correct / test_total

    epoch_time = time.time() - epoch_start
    print(f"{epoch:6d} | {avg_loss:10.4f} | {train_acc:8.2f}% | {test_acc:7.2f}% | {epoch_time:5.1f}s")

total_time = time.time() - start_time
print("-" * 48)
print(f"Total time: {total_time:.1f}s | Final test acc: {test_acc:.2f}%")
```

<br>

### 2-B. TensorFlow (Keras) 버전

`compare_tensorflow.py`

```python
import tensorflow as tf
import time

# ----------------------
# 1. 하이퍼파라미터
# ----------------------
BATCH_SIZE = 64
EPOCHS = 10
LR = 0.001

# ----------------------
# 2. 데이터 로드
# ----------------------
(x_train, y_train), (x_test, y_test) = tf.keras.datasets.fashion_mnist.load_data()

# 정규화: [0,255] → [-1, 1]
x_train = (x_train.astype('float32') - 127.5) / 127.5
x_test  = (x_test.astype('float32') - 127.5) / 127.5

# 채널 차원 추가 (Conv2D용) → 여기서는 Flatten 후 Dense만 사용
# x_train = x_train[..., tf.newaxis]
# x_test  = x_test[..., tf.newaxis]

train_dataset = tf.data.Dataset.from_tensor_slices((x_train, y_train))
train_dataset = train_dataset.shuffle(10000).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

test_dataset = tf.data.Dataset.from_tensor_slices((x_test, y_test))
test_dataset = test_dataset.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

# ----------------------
# 3. 모델 정의
# ----------------------
model = tf.keras.Sequential([
    tf.keras.layers.Flatten(input_shape=(28, 28)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dense(10)   # no softmax — from_logits=True 로 처리
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=LR),
    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    metrics=['accuracy']
)

total_params = model.count_params()
print(f"Device: {'GPU' if tf.config.list_physical_devices('GPU') else 'CPU'}")
print(f"Params: {total_params:,}")
print(f"Train samples: {len(x_train)}, Test samples: {len(x_test)}")
print()

# ----------------------
# 4. 학습
# ----------------------
start_time = time.time()
history = model.fit(
    train_dataset,
    validation_data=test_dataset,
    epochs=EPOCHS,
    verbose=1
)
total_time = time.time() - start_time

# ----------------------
# 5. 최종 결과
# ----------------------
test_loss, test_acc = model.evaluate(test_dataset, verbose=0)
print(f"\nTotal time: {total_time:.1f}s | Final test acc: {test_acc * 100:.2f}%")
```

<br>

---

<br>

## 3. 실행 방법

### 배치 파일 (Windows)

`run_comparison.bat`

```batch
@echo off
echo ===== PyTorch vs TensorFlow Comparison =====
echo.

echo [1/2] Running PyTorch...
python compare_pytorch.py > pytorch_result.txt 2>&1
type pytorch_result.txt
echo.

echo [2/2] Running TensorFlow...
python compare_tensorflow.py > tensorflow_result.txt 2>&1
type tensorflow_result.txt
echo.

echo ===== Done! Check pytorch_result.txt and tensorflow_result.txt =====
pause
```

### 직접 실행

```bash
python compare_pytorch.py
python compare_tensorflow.py
```

<br>

---

<br>

## 4. 결과 기록표

실험 후 아래 표를 채워서 비교해보세요.

| 항목 | PyTorch | TensorFlow |
|:---|:---:|:---:|
| **모델 파라미터 수** | | |
| **최종 테스트 정확도** | | |
| **총 학습 시간 (10 epoch)** | | |
| **코드 라인 수** (공백/주석 제외) | | |
| **GPU 사용 여부** | | |
| **CPU만 사용 시 시간** | | |

<br>

---

<br>

## 5. 심화 비교 (선택)

기본 MLP 대신 **CNN**으로도 비교해보려면 아래 코드 조각을 교체하세요.

### PyTorch CNN 모델

```python
class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(64 * 5 * 5, 128),
            nn.ReLU(),
            nn.Linear(128, 10)
        )

    def forward(self, x):
        return self.net(x)
```

### TensorFlow CNN 모델

```python
model = tf.keras.Sequential([
    tf.keras.layers.Reshape((28, 28, 1), input_shape=(28, 28)),
    tf.keras.layers.Conv2D(32, kernel_size=3, activation='relu'),
    tf.keras.layers.MaxPooling2D(2),
    tf.keras.layers.Conv2D(64, kernel_size=3, activation='relu'),
    tf.keras.layers.MaxPooling2D(2),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(10)
])
```

> **참고:** CNN을 사용하려면 PyTorch는 데이터 shape가 `(batch, 1, 28, 28)`이어야 하고, TensorFlow는 `(batch, 28, 28, 1)`이어야 합니다. 위 코드에서는 이미 ToTensor() / reshape에서 자동 처리됩니다.

<br>

---

<br>

## 6. 예상 결과 (참고)

동일 조건에서 일반적으로 나타나는 경향:

| 항목 | PyTorch | TensorFlow (Keras) |
|:---|:---:|:---:|
| 학습 정확도 | 비슷 (~88-90%) | 비슷 (~88-90%) |
| 코드 간결성 | 수동 루프 필요 | `model.fit()`으로 더 짧음 |
| 디버깅 용이성 | Pythonic, 자유도 높음 | Keras는 추상화 높음 |
| 속도 (GPU) | 비슷 | 비슷 |
| 속도 (CPU) | 비슷 | 비슷 |

결론: **성능 차이는 거의 없고, API 스타일과 생태계의 차이**가 선택 기준입니다.
