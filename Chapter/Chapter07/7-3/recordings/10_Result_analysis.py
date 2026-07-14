import os
import pickle
import glob
import matplotlib.pyplot as plt
import numpy as np

base_dir = os.path.dirname(__file__)

models = {
    "otsu":         "model-20260714_225933",
    "adaptive":     "model-20260714_230654",
    "invert_clahe": "model-20260714_231443",
    "resized":      "model-20260714_232204",
}

histories = {}
for name, folder in models.items():
    path = os.path.join(base_dir, folder, "history.pickle")
    if os.path.exists(path):
        with open(path, "rb") as f:
            histories[name] = pickle.load(f)
        print(f"Loaded: {name} ({folder})")
    else:
        print(f"NOT FOUND: {path}")

if not histories:
    raise RuntimeError("No history files found")

epochs = list(range(1, len(next(iter(histories.values()))["train_loss"]) + 1))

# --- Figure 1: Training Loss ---
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
for name, h in histories.items():
    ax.plot(epochs, h["train_loss"], marker="o", label=name)
ax.set_title("Training Loss")
ax.set_xlabel("Epoch")
ax.set_ylabel("MSE Loss")
ax.legend()
ax.grid(True)

# --- Figure 2: Validation Loss ---
ax = axes[0, 1]
for name, h in histories.items():
    ax.plot(epochs, h["val_loss"], marker="o", label=name)
ax.set_title("Validation Loss")
ax.set_xlabel("Epoch")
ax.set_ylabel("MSE Loss")
ax.legend()
ax.grid(True)

# --- Figure 3: Validation MAE ---
ax = axes[1, 0]
for name, h in histories.items():
    ax.plot(epochs, h["val_mae"], marker="o", label=name)
ax.set_title("Validation MAE (degrees)")
ax.set_xlabel("Epoch")
ax.set_ylabel("MAE (deg)")
ax.legend()
ax.grid(True)

# --- Figure 4: Best MAE comparison ---
ax = axes[1, 1]
names = list(histories.keys())
best_mae = [min(histories[n]["val_mae"]) for n in names]
best_epoch = [histories[n]["val_mae"].index(min(histories[n]["val_mae"])) + 1 for n in names]
colors = ["#2196F3", "#FF9800", "#4CAF50", "#E91E63"]
bars = ax.bar(names, best_mae, color=colors)
for bar, mae, ep in zip(bars, best_mae, best_epoch):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
            f"{mae:.2f}deg\n(ep {ep})", ha="center", va="bottom", fontsize=9)
ax.set_title("Best Validation MAE")
ax.set_ylabel("MAE (deg)")
ax.grid(axis="y")

plt.tight_layout()
fig_path = os.path.join(base_dir, "processed", "training_comparison.png")
plt.savefig(fig_path, dpi=150)
print(f"\nSaved: {fig_path}")

# --- Summary table ---
print("\n" + "=" * 65)
print(f"{'Source':<15} {'Best Val Loss':>14} {'Best MAE':>10} {'@Epoch':>7} {'Final MAE':>10}")
print("-" * 65)
for name, h in histories.items():
    best_vl = min(h["val_loss"])
    best_m = min(h["val_mae"])
    best_e = h["val_mae"].index(best_m) + 1
    final_m = h["val_mae"][-1]
    print(f"{name:<15} {best_vl:>14.2f} {best_m:>9.3f}deg {best_e:>6} {final_m:>9.3f}deg")
print("=" * 65)

best_name = min(histories, key=lambda n: min(histories[n]["val_mae"]))
print(f"\nBest model: {best_name} (MAE={min(histories[best_name]['val_mae']):.3f}deg)")
