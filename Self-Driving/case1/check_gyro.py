"""
Check gyro steering from MPU6050 gz
Compare with wheel pulse direction
"""
import csv
import numpy as np

path = r"C:\Users\Administrator\Desktop\Self-Driving\case1\slam_data_20260629_124940.csv"

with open(path, encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Parse gz from STEP messages
# Also get pulse start/end for each scan
step_gz = []
scan_pulses = {}

current_scan = None
for r in rows:
    mt = r['msg_type'].strip()
    si = r['scan_index'].strip()

    if mt == 'STEP':
        gz = float(r['gz']) if r['gz'].strip() else 0.0
        step_gz.append({'scan': si, 'gz': gz})
        current_scan = si
        scan_pulses[si] = {}

    elif mt == 'S':
        if current_scan not in scan_pulses:
            scan_pulses[current_scan] = {}
        s = scan_pulses[current_scan]
        if 'first_L' not in s:
            s['first_L'] = float(r['pulse_L_or_ax'])
            s['first_R'] = float(r['pulse_R_or_ay'])
        s['last_L'] = float(r['pulse_L_or_ax'])
        s['last_R'] = float(r['pulse_R_or_ay'])

print("=" * 70)
print("Steering Ground Truth: MPU6050 gz vs Wheel Pulses")
print("=" * 70)
print(f"{'Scan':>5} | {'gz':>8} | {'dL':>8} {'dR':>8} | {'PulseDir':>10} | {'Steer(gz)':>10}")
print("-" * 70)

for s in step_gz:
    si = s['scan']
    p = scan_pulses.get(si, {})
    if 'first_L' not in p:
        continue
    dL = p['last_L'] - p['first_L']
    dR = p['last_R'] - p['first_R']

    gz = s['gz']
    # Normalize gz to -1..+1 scale
    gz_norm = np.clip(gz / 3.0, -1.0, 1.0)

    if abs(dL) + abs(dR) < 0.1:
        pulse_dir = "STOP"
    elif dL > 0 and dR < 0:
        pulse_dir = "RIGHT"
    elif dL < 0 and dR > 0:
        pulse_dir = "LEFT"
    else:
        pulse_dir = "???"

    steer_label = "RIGHT" if gz > 0.3 else ("LEFT" if gz < -0.3 else "STRAIGHT")

    print(f"  {si:>3} | {gz:+8.2f} | {dL:+8.1f} {dR:+8.1f} | {pulse_dir:>10} | {steer_label:>10}")

print("-" * 70)

# Compare agreement
print("\nAgreement between gz direction and pulse direction:")
agree = 0
total = 0
for s in step_gz:
    si = s['scan']
    p = scan_pulses.get(si, {})
    if 'first_L' not in p:
        continue
    dL = p['last_L'] - p['first_L']
    dR = p['last_R'] - p['first_R']
    gz = s['gz']
    if abs(dL) + abs(dR) < 0.1:
        continue
    if abs(gz) < 0.3:
        continue
    gz_right = gz > 0
    pulse_right = dL > 0 and dR < 0
    if gz_right == pulse_right:
        agree += 1
    total += 1
    match = "MATCH" if gz_right == pulse_right else "MISMATCH"
    dL_val = p['last_L'] - p['first_L']
    dR_val = p['last_R'] - p['first_R']
    print(f"  Scan {si}: gz={gz:+.2f}, dL={dL_val:+.1f}, dR={dR_val:+.1f} -> {match}")

print(f"\n  Agree: {agree}/{total} ({agree / total * 100:.0f}%)")

# gz statistics
gz_vals = np.array([s['gz'] for s in step_gz])
print(f"\ngz statistics (MPU6050 gyro Z):")
print(f"  Range: {gz_vals.min():+.2f} ~ {gz_vals.max():+.2f} deg/s")
print(f"  Mean:  {gz_vals.mean():+.4f}")
print(f"  Std:   {gz_vals.std():.4f}")
print(f"  |gz|<0.3 (straight): {np.mean(np.abs(gz_vals) < 0.3) * 100:.0f}%")
print(f"  |gz|>1.0 (strong):   {np.mean(np.abs(gz_vals) > 1.0) * 100:.0f}%")
