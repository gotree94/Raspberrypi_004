import os
import fnmatch
import random
import numpy as np
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

plt.figure(figsize=(10, 5))
plt.hist(y_train, bins=30, alpha=0.6, label="Training", color="blue", edgecolor="black")
plt.hist(y_valid, bins=30, alpha=0.6, label="Validation", color="red", edgecolor="black")
plt.title('Training vs Validation Steering Angle Distribution')
plt.xlabel("Steering Angle")
plt.ylabel("Frequency")
plt.legend()
plt.grid(True)
plt.show()