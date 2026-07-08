import sys
import random
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket
import time
import math

MOTOR_SPECS = {
    "MONOCHROMATOR": {"type": "Stepper", "range": "200~999 nm", "step": 1, "unit": "nm"},
    "FILTER_WHEEL":  {"type": "DC", "positions": 6, "unit": "position"},
    "STAGE_X":       {"type": "Stepper", "resolution": 0.01, "range": "0~120 mm", "unit": "mm"},
    "STAGE_Y":       {"type": "Stepper", "resolution": 0.01, "range": "0~80 mm", "unit": "mm"}
}

SENSOR_SPECS = {
    "PMT":               {"type": "Photomultiplier tube", "range": "0~4.0 OD"},
    "PLATE_PRESENT":     {"type": "Photoelectric", "range": "present/absent"},
    "CHAMBER_TEMP":      {"type": "PT1000", "range": "20~45 °C"},
    "MONO_HOME":         {"type": "Optical", "range": "homed/not_homed"},
    "CAL_REFERENCE":     {"type": "Stable photodiode", "range": "reference signal"}
}

ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
COLS = list(range(1, 13))


class PlateReaderV3(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔬 Microplate Reader Simulator v3 — BioTek Synergy H1")
        self.geometry("1100x750")
        self.wavelength = 450
        self.filter_pos = 1
        self.stage_x = 0.0
        self.stage_y = 0.0
        self.plate_present = True
        self.chamber_temp = 37.0
        self.pmt_signal = 0.0
        self.mono_homed = True
        self.cal_reference = 1.000
        self.scanning = False
        self.current_well = (0, 0)
        self.well_values = {}
        self.initUI()
        threading.Thread(target=self.start_server, daemon=True).start()
        self.env_tick()
        self.log("[System] Server listening on Port 50053...")
        self.log(f"[System] Motors: {len(MOTOR_SPECS)} total")
        self.log(f"[System] Sensors: {len(SENSOR_SPECS)} total")

    def initUI(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left = ttk.LabelFrame(main_paned, text=" [ Motor Panel — 4 Motors ] ", padding=5)
        main_paned.add(left, weight=1)
        self.motor_labels = {}

        ttk.Label(left, text=f"Monochromator:", font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=5, pady=3)
        self.mono_lbl = ttk.Label(left, text=f"λ = {self.wavelength} nm", font=("Consolas", 11, "bold"))
        self.mono_lbl.pack(anchor=tk.W, padx=5)
        self.mono_bar = ttk.Progressbar(left, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.mono_bar.pack(pady=3)
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        ttk.Label(left, text=f"Filter Wheel:", font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=5, pady=3)
        self.filter_lbl = ttk.Label(left, text=f"Position {self.filter_pos}/6", font=("Consolas", 9))
        self.filter_lbl.pack(anchor=tk.W, padx=5)
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        ttk.Label(left, text=f"Stage X/Y:", font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=5, pady=3)
        self.stage_lbl = ttk.Label(left, text=f"X: {self.stage_x:.2f} mm  Y: {self.stage_y:.2f} mm",
                                   font=("Consolas", 9))
        self.stage_lbl.pack(anchor=tk.W, padx=5)
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        ttk.Label(left, text=f"Sensors:", font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=5, pady=3)
        self.sensor_labels = {}
        for name in ["PMT", "Plate Present", "Chamber Temp", "Cal Reference"]:
            lbl = ttk.Label(left, text=f"{name}: --", font=("Consolas", 8))
            lbl.pack(anchor=tk.W, padx=5, pady=1)
            self.sensor_labels[name] = lbl

        mid = ttk.LabelFrame(main_paned, text=" [ 96-Well Heatmap & Scan ] ", padding=5)
        main_paned.add(mid, weight=3)

        grid_frame = ttk.Frame(mid)
        grid_frame.pack(pady=10)

        self.wells = {}
        ttk.Label(grid_frame, text="", width=3).grid(row=0, column=0)
        for c_idx, col in enumerate(COLS):
            ttk.Label(grid_frame, text=str(col), width=4, anchor="center").grid(row=0, column=c_idx + 1)
        for r_idx, row in enumerate(ROWS):
            ttk.Label(grid_frame, text=row, width=3, anchor="center").grid(row=r_idx + 1, column=0)
            for c_idx in range(12):
                well = tk.Label(grid_frame, width=4, height=1, bg="#F5F5F5", relief="groove")
                well.grid(row=r_idx + 1, column=c_idx + 1, padx=1, pady=1)
                self.wells[(row, c_idx + 1)] = well

        ttk.Separator(mid, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        self.scan_progress = ttk.Progressbar(mid, orient=tk.HORIZONTAL, length=500, mode='determinate')
        self.scan_progress.pack(pady=3)
        self.scan_status = ttk.Label(mid, text="Status: IDLE", font=("Arial", 10, "bold"))
        self.scan_status.pack()

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        log_frame = ttk.LabelFrame(bottom_frame, text=" [ Measurement Data Stream ] ", padding=3)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=10, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.insert(tk.END, "[System] Initialized.\n")

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def env_tick(self):
        self.chamber_temp += random.uniform(-0.2, 0.2)
        self.chamber_temp = max(34, min(40, self.chamber_temp))
        self.sensor_labels["Chamber Temp"].config(text=f"Chamber Temp: {self.chamber_temp:.1f} °C")
        self.after(5000, self.env_tick)

    def set_wavelength(self, nm):
        self.log(f"[Motor] Monochromator moving: {self.wavelength} → {nm} nm...")
        steps = abs(nm - self.wavelength)
        for _ in range(min(int(steps / 10) + 1, 20)):
            self.wavelength += (1 if nm > self.wavelength else -1) * min(10, abs(nm - self.wavelength))
            self.mono_lbl.config(text=f"λ = {self.wavelength} nm")
            self.mono_bar['value'] = ((self.wavelength - 200) / 799) * 100
            time.sleep(0.03)
        self.wavelength = nm
        self.mono_lbl.config(text=f"λ = {self.wavelength} nm")
        self.mono_bar['value'] = ((self.wavelength - 200) / 799) * 100
        self.log(f"[Motor] Monochromator settled at {nm} nm.")

    def move_stage_to(self, row_idx, col_idx):
        target_x = (col_idx - 1) * 9.0 + 4.5
        target_y = row_idx * 9.0 + 4.5
        self.stage_x = target_x
        self.stage_y = target_y
        self.stage_lbl.config(text=f"X: {self.stage_x:.2f} mm  Y: {self.stage_y:.2f} mm")

    def simulate_scan(self, current_rpm):
        self.scanning = True
        self.scan_status.config(text="Status: SCANNING...", foreground="orange")
        self.set_wavelength(450 + random.choice([-50, 0, 50]))

        base_efficiency = current_rpm / 4000.0
        max_val = 0.0
        total_wells = 96
        scanned = 0
        self.filter_pos = random.randint(1, 6)
        self.filter_lbl.config(text=f"Position {self.filter_pos}/6")
        self.sensor_labels["Plate Present"].config(text="Plate Present: YES ●", foreground="green")

        for r_idx, row in enumerate(ROWS):
            for col in COLS:
                self.current_well = (r_idx, col)
                self.move_stage_to(r_idx, col)

                val = round(base_efficiency * 1.1 + random.uniform(-0.04, 0.04), 3)
                if val < 0: val = 0.0
                self.well_values[(row, col)] = val
                if val > max_val: max_val = val

                self.pmt_signal = val
                self.sensor_labels["PMT"].config(text=f"PMT: {val:.3f} OD")

                intensity = int((val / 1.2) * 10)
                shades = ["#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6",
                          "#2171B5", "#08519C", "#08306B", "#051A3B", "#020B1C"]
                self.wells[(row, col)].configure(bg=shades[min(max(intensity, 0), 10)])

                scanned += 1
                self.scan_progress['value'] = (scanned / total_wells) * 100
                self.root().update() if hasattr(self, 'root') else self.update()
                time.sleep(0.02)

            self.log(f"Row {row}: [{', '.join(f'{self.well_values[(row, c)]:.3f}' for c in COLS[:6])}...]")

        self.scanning = False
        self.scan_status.config(text="Status: COMPLETE", foreground="green")
        self.scan_progress['value'] = 0
        self.stage_lbl.config(text="X: 0.00 mm  Y: 0.00 mm")
        self.log(f"[System] Scan Done. Max Absorbance: {max_val:.3f}")
        self.sensor_labels["Cal Reference"].config(text=f"Cal Reference: {1.000 + random.uniform(-0.01, 0.01):.3f}",
            foreground="green")
        return max_val

    def remote_scan(self, current_rpm, conn):
        self.log(f"[Network] Received Scan Request (RPM Source: {current_rpm})")
        max_val = self.simulate_scan(current_rpm)
        conn.sendall(str(max_val).encode('utf-8'))
        conn.close()
        self.scan_status.config(text="Status: IDLE", foreground="black")

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50053))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data.startswith("SCAN:"):
                rpm = int(data.split(":")[1])
                self.after(0, self.remote_scan, rpm, conn)


if __name__ == "__main__":
    app = PlateReaderV3()
    app.mainloop()
