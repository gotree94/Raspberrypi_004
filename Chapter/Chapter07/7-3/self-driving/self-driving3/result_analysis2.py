import os
import sys
import glob as glob_module
import pickle
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

base_dir = os.path.dirname(os.path.abspath(__file__))

if len(sys.argv) < 2:
    print(f"Usage: python {os.path.basename(__file__)} <model_keyword> [output_folder]")
    print(f"  model_keyword: partial model folder name (e.g. 20260715_224033)")
    print(f"  output_folder: output folder (default: test2_results_<keyword>)")
    print(f"")
    print(f"Examples:")
    print(f"  python {os.path.basename(__file__)} 20260715_224033")
    print(f"  python {os.path.basename(__file__)} 20260715_224033 test2_results_m10")
    sys.exit(1)

keyword = sys.argv[1]
output_folder = sys.argv[2] if len(sys.argv) > 2 else f"test2_results_{keyword}"

histories = {}
for d in glob_module.glob(os.path.join(base_dir, f"model-*_{keyword}")):
    folder_name = os.path.basename(d)
    filter_name = folder_name.split("_")[-1]
    path = os.path.join(d, "history.pickle")
    if os.path.exists(path):
        with open(path, "rb") as f:
            histories[filter_name] = pickle.load(f)
        print(f"Loaded: {filter_name} ({folder_name})")
    else:
        print(f"NOT FOUND: {path}")

if not histories:
    raise RuntimeError("No history files found")

epochs = list(range(1, len(next(iter(histories.values()))["train_loss"]) + 1))

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
for name, h in histories.items():
    ax.plot(epochs, h["train_loss"], marker="o", label=name)
ax.set_title("Training Loss")
ax.set_xlabel("Epoch")
ax.set_ylabel("MSE Loss")
ax.legend()
ax.grid(True)

ax = axes[0, 1]
for name, h in histories.items():
    ax.plot(epochs, h["val_loss"], marker="o", label=name)
ax.set_title("Validation Loss")
ax.set_xlabel("Epoch")
ax.set_ylabel("MSE Loss")
ax.legend()
ax.grid(True)

ax = axes[1, 0]
for name, h in histories.items():
    ax.plot(epochs, h["val_mae"], marker="o", label=name)
ax.set_title("Validation MAE (degrees)")
ax.set_xlabel("Epoch")
ax.set_ylabel("MAE (deg)")
ax.legend()
ax.grid(True)

ax = axes[1, 1]
names = list(histories.keys())
best_mae = [min(histories[n]["val_mae"]) for n in names]
best_epoch = [histories[n]["val_mae"].index(min(histories[n]["val_mae"])) + 1 for n in names]
colors = ["#2196F3", "#FF9800", "#4CAF50", "#E91E63"]
bars = ax.bar(names, best_mae, color=colors)
for bar, mae, ep in zip(bars, best_mae, best_epoch):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
            f"{mae:.3f}deg\n(ep {ep})", ha="center", va="bottom", fontsize=9)
ax.set_title("Best Validation MAE")
ax.set_ylabel("MAE (deg)")
ax.grid(axis="y")

plt.tight_layout()
fig_path = os.path.join(base_dir, output_folder, "training_comparison.png")
os.makedirs(os.path.dirname(fig_path), exist_ok=True)
plt.savefig(fig_path, dpi=150)
print(f"\nSaved: {fig_path}")

print("\n" + "=" * 65)
print(f"{'Source':<15} {'Best Val Loss':>14} {'Best MAE':>10} {'@Epoch':>7} {'Final MAE':>10}")
print("-" * 65)
for name, h in histories.items():
    best_vl = min(h["val_loss"])
    best_m = min(h["val_mae"])
    best_e = h["val_mae"].index(best_m) + 1
    final_m = h["val_mae"][-1]
    print(f"{name:<15} {best_vl:>14.4f} {best_m:>9.3f}deg {best_e:>6} {final_m:>9.3f}deg")
print("=" * 65)

best_name = min(histories, key=lambda n: min(histories[n]["val_mae"]))
print(f"\nBest model: {best_name} (MAE={min(histories[best_name]['val_mae']):.3f}deg)")
