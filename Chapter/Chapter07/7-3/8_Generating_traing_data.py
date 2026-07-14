import os
import random
import fnmatch
import numpy as np
import cv2
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import torch

data_dir = os.path.join(os.path.dirname(__file__), "video")
image_paths = []
steering_angles = []

for filename in os.listdir(data_dir):
    if fnmatch.fnmatch(filename, "*.png"):
        image_paths.append(os.path.join(data_dir, filename))
        angle = int(filename[-7:-4])
        steering_angles.append(angle)

X_train, X_valid, y_train, y_valid = train_test_split(
    image_paths, steering_angles, test_size=0.2, random_state=42
)

def my_imread(image_path):
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image

def img_preprocess(image):
    image = image.astype(np.float32) / 255.0
    return image

def image_data_generator(image_paths, steering_angles, batch_size):
    n = len(image_paths)
    while True:
        batch_images = []
        batch_angles = []
        for _ in range(batch_size):
            idx = random.randint(0, n - 1)
            image = my_imread(image_paths[idx])
            angle = steering_angles[idx]
            image = img_preprocess(image)
            batch_images.append(image)
            batch_angles.append(angle)
        yield np.asarray(batch_images), np.asarray(batch_angles, dtype=np.float32)

nrow = 2
ncol = 2
batch_size = nrow * ncol

X_train_batch, y_train_batch = next(image_data_generator(X_train, y_train, batch_size))
X_valid_batch, y_valid_batch = next(image_data_generator(X_valid, y_valid, batch_size))

fig, axes = plt.subplots(nrow, ncol * 2, figsize=(16, 8))

for i in range(nrow):
    for j in range(ncol):
        idx = i * ncol + j
        axes[i][j * 2].imshow(X_train_batch[idx])
        axes[i][j * 2].set_title(f"Train Angle: {y_train_batch[idx]}")
        axes[i][j * 2].axis("off")

        axes[i][j * 2 + 1].imshow(X_valid_batch[idx])
        axes[i][j * 2 + 1].set_title(f"Valid Angle: {y_valid_batch[idx]}")
        axes[i][j * 2 + 1].axis("off")

plt.tight_layout()
plt.show()