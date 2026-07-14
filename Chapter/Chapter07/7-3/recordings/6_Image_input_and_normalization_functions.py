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

image_index = random.randint(0, len(image_paths) - 1)
fig, axes = plt.subplots(1, 2, figsize=(15, 8))

image_orig = my_imread(image_paths[image_index])
image_processed = img_preprocess(image_orig)

axes[0].imshow(image_orig)
axes[0].set_title("Original Image")
axes[0].axis("off")

axes[1].imshow(image_processed)
axes[1].set_title("Normalized Image")
axes[1].axis('off')

plt.tight_layout()
plt.show()