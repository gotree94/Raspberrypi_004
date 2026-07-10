"""
check_odometry.py
CSV 엔코더 펄스 기반 조향각 검증
"""

import csv
import math
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

CSV_PATH = r"C:\Users\Administrator\Desktop\Self-Driving\case1\slam_data_20260629_124940.csv"

def load_data(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def parse_float(v):
    try:
        return float(v) if v.strip() else float('nan')
    except:
        return float('nan')

def analyze_scans(rows):
    scans = defaultdict(lambda: {
        'start_L': [], 'start_R': [],
        'end_L': [], 'end_R': [],
        'steer_odom': [], 'timestamps': [],
        'gz': None, 'dist_or_yaw_list': []
    })

    current_scan = None
    for r in rows:
        msg = r['msg_type'].strip()
        sidx = r['scan_index'].strip()

        if msg == 'STEP':
            # STEP은 0° 측정 전 IMU 데이터
            timestamps = r['timestamp']
            current_scan = sidx
            continue

        if msg == 'S':
            angle = parse_float(r['dist_or_yaw'])
            L = parse_float(r['pulse_L_or_ax'])
            R = parse_float(r['pulse_R_or_ay'])

            scans[sidx]['timestamps'].append(r['timestamp'])
            scans[sidx]['dist_or_yaw_list'].append(angle)
            scans[sidx]['start_L'].append(L)
            scans[sidx]['start_R'].append(R)

        if msg == 'ROT':
            ax = parse_float(r['pulse_L_or_ax'])
            ay = parse_float(r['pulse_R_or_ay'])
            az = parse_float(r['az'])
            gz = parse_float(r['gz'])
            print(f"  ROT detected! scan={sidx}, yaw={r['dist_or_yaw']}, IMU(ax={ax:.3f}, ay={ay:.3f}, az={az:.3f}, gz={gz:.3f})")

    print("=" * 60)
    print("Odometry-based Steering Analysis per Scan")
    print("=" * 60)
    print(f"{'Scan':>5} | {'StartL':>7} {'StartR':>7} | {'EndL':>7} {'EndR':>7} | {'dL':>6} {'dR':>6} | {'Steer':>7} | {'Dir'}")
    print("-" * 60)

    results = []
    for sidx in sorted(scans.keys(), key=int):
        s = scans[sidx]
        if len(s['start_L']) < 2:
            continue

        start_L = s['start_L'][0]
        start_R = s['start_R'][0]
        end_L = s['start_L'][-1]
        end_R = s['start_R'][-1]

        dL = end_L - start_L
        dR = end_R - start_R

        denom = abs(dL) + abs(dR)
        if denom > 0.1:
            steer = (dR - dL) / denom
            steer = np.clip(steer, -1.0, 1.0)
        else:
            steer = 0.0

        if abs(steer) < 0.15:
            interp = "STRAIGHT"
        elif steer > 0:
            interp = "RIGHT"
        else:
            interp = "LEFT"

        results.append({
            'scan': int(sidx), 'steer': steer,
            'dL': dL, 'dR': dR,
            'start_L': start_L, 'start_R': start_R,
            'end_L': end_L, 'end_R': end_R,
            'samples': len(s['start_L']),
            'interp': interp
        })

        print(f"  {sidx:>3} | {start_L:7.1f} {start_R:7.1f} | {end_L:7.1f} {end_R:7.1f} | {dL:+6.1f} {dR:+6.1f} | {steer:+7.3f} | {interp}")

    print("-" * 60)
    return results

def plot_results(results):
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    scans = [r['scan'] for r in results]
    steers = [r['steer'] for r in results]

    colors = ['g' if abs(s) < 0.15 else ('r' if s > 0 else 'b') for s in steers]
    axes[0].bar(scans, steers, color=colors, width=0.6)
    axes[0].axhline(0, color='gray', linestyle='-', linewidth=0.5)
    axes[0].axhline(0.15, color='gray', linestyle='--', linewidth=0.5)
    axes[0].axhline(-0.15, color='gray', linestyle='--', linewidth=0.5)
    axes[0].set_ylabel('Steering (-1~+1)')
    axes[0].set_title('Odometry Steering per Scan')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(['Straight(+-0.15)', 'Steering'], loc='upper right')

    dL = [r['dL'] for r in results]
    dR = [r['dR'] for r in results]
    axes[1].bar([s - 0.15 for s in scans], dL, width=0.3, label='Delta L', alpha=0.7)
    axes[1].bar([s + 0.15 for s in scans], dR, width=0.3, label='Delta R', alpha=0.7)
    axes[1].axhline(0, color='gray', linestyle='-', linewidth=0.5)
    axes[1].set_xlabel('Scan Index')
    axes[1].set_ylabel('Pulse Change')
    axes[1].set_title('L/R Wheel Pulse Changes')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = r"C:\Users\Administrator\Desktop\Self-Driving\case1\odometry_analysis.png"
    plt.savefig(out_path, dpi=150)
    print(f"\nChart saved: {out_path}")
    plt.close()

def main():
    print("CSV 로드 중...")
    rows = load_data(CSV_PATH)
    print(f"  Total {len(rows)} rows")

    types = {}
    for r in rows:
        t = r['msg_type'].strip()
        types[t] = types.get(t, 0) + 1
    print(f"  Message types: {types}")

    results = analyze_scans(rows)
    plot_results(results)

    # 종합 통계
    print("\nSummary:")
    steers = np.array([r['steer'] for r in results])
    print(f"  Mean steering: {np.mean(steers):+.4f}")
    print(f"  Max LEFT:  {np.min(steers):+.4f}")
    print(f"  Max RIGHT: {np.max(steers):+.4f}")
    print(f"  Straight(|s|<0.15): {np.mean(np.abs(steers) < 0.15)*100:.0f}%")
    print(f"  LEFT  (s<=-0.15):   {np.mean(steers <= -0.15)*100:.0f}%")
    print(f"  RIGHT (s>=0.15):    {np.mean(steers >= 0.15)*100:.0f}%")

    diffs = np.abs(np.diff(steers))
    print(f"\nSmoothness (adjacent scan diff):")
    print(f"  Mean diff: {np.mean(diffs):.3f}")
    print(f"  Max diff:  {np.max(diffs):.3f}")
    if np.max(diffs) > 0.8:
        print(f"  WARNING: Abrupt change detected - possible sensor noise")
    else:
        print(f"  OK: Smooth changes - sensor data reliable")

if __name__ == "__main__":
    main()
