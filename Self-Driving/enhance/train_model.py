"""
train_model.py
CNN 모델 학습 — NVIDIA E2E 경량화 × 개선 v2
증강 강화, tanh 출력, LR 스케줄 최적화
"""

import numpy as np
import json
import os
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import tensorflow as tf
from tensorflow import keras

# ===================== 설정 =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "training_data")
MODEL_PATH = os.path.join(BASE_DIR, "steering_model.keras")
BATCH_SIZE = 16
EPOCHS = 120
IMG_WIDTH, IMG_HEIGHT = 160, 80


# ===================== 데이터 로드 =====================

def load_data():
    with open(os.path.join(DATA_DIR, "metadata.json")) as f:
        meta = json.load(f)

    X, y = [], []
    for item in meta["data"]:
        img = np.load(os.path.join(DATA_DIR, item["file"]))
        X.append(img)
        y.append(item["steering"])

    X = np.array(X, dtype=np.float32) / 127.5 - 1.0
    y = np.array(y, dtype=np.float32)

    split = int(len(X) * 0.8)
    indices = np.random.permutation(len(X))
    train_idx, val_idx = indices[:split], indices[split:]

    return X[train_idx], y[train_idx], X[val_idx], y[val_idx]


# ===================== 모델 정의 =====================

def build_model():
    model = keras.Sequential([
        keras.layers.Conv2D(16, (5, 5), strides=(2, 2), padding='same',
                            activation='relu', input_shape=(IMG_HEIGHT, IMG_WIDTH, 3)),
        keras.layers.Dropout(0.1),

        keras.layers.Conv2D(24, (5, 5), strides=(2, 2), padding='same', activation='relu'),
        keras.layers.Dropout(0.1),

        keras.layers.Conv2D(32, (3, 3), strides=(2, 2), padding='same', activation='relu'),
        keras.layers.Dropout(0.1),

        keras.layers.Conv2D(48, (3, 3), strides=(1, 1), padding='same', activation='relu'),
        keras.layers.Dropout(0.1),

        keras.layers.Flatten(),
        keras.layers.Dense(64, activation='relu'),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(32, activation='relu'),

        # tanh로 출력 -1~1 강제 제한 (학습 안정화)
        keras.layers.Dense(1, activation='tanh')
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )

    return model


# ===================== 학습률 스케줄 (Cosine Decay) =====================

def cosine_lr_schedule(epoch, lr):
    """Cosine annealing: 초반 빠른 학습 → 후반 세밀 조정"""
    total_epochs = EPOCHS
    initial_lr = 0.001
    return initial_lr * (1 + np.cos(np.pi * epoch / total_epochs)) / 2


# ===================== 학습 =====================

def main():
    print("=" * 50)
    print("Self-Driving Steering Model Training (CPU) v2")
    print("=" * 50)

    print("\n[1/4] 데이터 로드 중...")
    X_train, y_train, X_val, y_val = load_data()
    print(f"  학습: {len(X_train)} samples")
    print(f"  검증: {len(X_val)} samples")
    print(f"  이미지 shape: {X_train.shape[1:]}")

    print("\n[2/4] 데이터 증강 설정 (강화)...")
    datagen = keras.preprocessing.image.ImageDataGenerator(
        width_shift_range=0.08,
        height_shift_range=0.05,
        brightness_range=[0.7, 1.3],
        rotation_range=3,
        zoom_range=0.05,
        shear_range=0.03,
        fill_mode='nearest',
    )

    print("\n[3/4] 모델 빌드 중...")
    model = build_model()
    model.summary()

    callbacks = [
        keras.callbacks.ModelCheckpoint(MODEL_PATH, save_best_only=True, monitor='val_loss'),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.7, patience=8, min_lr=1e-5),
        keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=20, restore_best_weights=True),
        keras.callbacks.LearningRateScheduler(cosine_lr_schedule),
    ]

    print(f"\n[4/4] 학습 시작 (최대 {EPOCHS} epoch, CPU)...")
    print("=" * 50)
    start_time = time.time()

    history = model.fit(
        datagen.flow(X_train, y_train, batch_size=BATCH_SIZE),
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        callbacks=callbacks,
        verbose=1
    )

    total_time = time.time() - start_time

    print("\n" + "=" * 50)
    print("학습 완료!")
    print(f"  소요 시간: {total_time:.1f}s")
    print(f"  최종 Train Loss: {history.history['loss'][-1]:.6f}")
    print(f"  최종 Val Loss:   {history.history['val_loss'][-1]:.6f}")
    print(f"  최종 Train MAE:  {history.history['mae'][-1]:.6f}")
    print(f"  최종 Val MAE:    {history.history['val_mae'][-1]:.6f}")
    print(f"  모델 저장: {MODEL_PATH}")

    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Val Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss (MSE)')
    plt.legend()
    plt.grid(True)

    plt.subplot(1, 2, 2)
    plt.plot(history.history['mae'], label='Train MAE')
    plt.plot(history.history['val_mae'], label='Val MAE')
    plt.xlabel('Epoch')
    plt.ylabel('MAE')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig("training_history.png")
    print(f"  학습 곡선: training_history.png")


if __name__ == "__main__":
    main()
