import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket
import time
import random
import math

MOTOR_SPECS = {
    "X_GANTRY":  {"type": "Stepper", "resolution": 0.1, "max_speed": 500, "unit": "mm"},
    "Y_GANTRY":  {"type": "Stepper", "resolution": 0.1, "max_speed": 300, "unit": "mm"},
    "Z_HEAD":    {"type": "Stepper", "resolution": 0.05, "max_speed": 200, "unit": "mm"},
    "PLUNGER_1": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "PLUNGER_2": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "PLUNGER_3": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "PLUNGER_4": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "PLUNGER_5": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "PLUNGER_6": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "PLUNGER_7": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "PLUNGER_8": {"type": "Stepper", "resolution": 0.1, "max_speed": 50, "unit": "uL/s"},
    "TIP_EJECTOR": {"type": "Solenoid", "resolution": "-", "max_speed": "-", "unit": "on/off"},
    "RESERVOIR_SHUTTLE": {"type": "Stepper", "resolution": 0.5, "max_speed": 100, "unit": "mm"}
}

SENSOR_SPECS = {
    "TIP_1":  {"type": "Capacitive", "range": "present/absent"},
    "TIP_2":  {"type": "Capacitive", "range": "present/absent"},
    "TIP_3":  {"type": "Capacitive", "range": "present/absent"},
    "TIP_4":  {"type": "Capacitive", "range": "present/absent"},
    "TIP_5":  {"type": "Capacitive", "range": "present/absent"},
    "TIP_6":  {"type": "Capacitive", "range": "present/absent"},
    "TIP_7":  {"type": "Capacitive", "range": "present/absent"},
    "TIP_8":  {"type": "Capacitive", "range": "present/absent"},
    "LLD_1":  {"type": "Capacitive", "range": "contact/no_contact"},
    "LLD_2":  {"type": "Capacitive", "range": "contact/no_contact"},
    "LLD_3":  {"type": "Capacitive", "range": "contact/no_contact"},
    "LLD_4":  {"type": "Capacitive", "range": "contact/no_contact"},
    "LLD_5":  {"type": "Capacitive", "range": "contact/no_contact"},
    "LLD_6":  {"type": "Capacitive", "range": "contact/no_contact"},
    "LLD_7":  {"type": "Capacitive", "range": "contact/no_contact"},
    "LLD_8":  {"type": "Capacitive", "range": "contact/no_contact"},
    "PRESSURE": {"type": "Differential", "range": "-500~500 mbar"},
    "HOME_X": {"type": "Optical limit", "range": "homed/not_homed"},
    "HOME_Y": {"type": "Optical limit", "range": "homed/not_homed"},
    "HOME_Z": {"type": "Optical limit", "range": "homed/not_homed"}
}


class MotorState:
    def __init__(self):
        self.X = 0.0
        self.Y = 0.0
        self.Z = 0.0
        self.plungers = [0.0] * 8
        self.tip_ejector = False
        self.shuttle_pos = 0.0

    def home_all(self):
        self.X, self.Y, self.Z = 0.0, 0.0, 0.0
        self.shuttle_pos = 0.0


class SensorState:
    def __init__(self):
        self.tips = [False] * 8
        self.lld = [False] * 8
        self.pressure = 0.0
        self.home_x = False
        self.home_y = False
        self.home_z = False


class LiquidHandlerV3(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("💧 Liquid Handler Simulator v3 — Hamilton Microlab STAR")
        self.geometry("1000x700")
        self.motor = MotorState()
        self.sensor = SensorState()
        self.initUI()
        threading.Thread(target=self.start_server, daemon=True).start()
        self.log("[System] Server listening on Port 50051...")
        self.log(f"[System] Motors: {sum(v['max_speed'] != '-' for v in MOTOR_SPECS.values())} total")
        self.log(f"[System] Sensors: {len(SENSOR_SPECS)} total")

    def initUI(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.LabelFrame(main_paned, text=" [ Motor Control Panel — 13 Motors ] ", padding=5)
        main_paned.add(left_frame, weight=1)
        self.motor_vars = {}
        self.motor_bars = {}
        row = 0
        for i in range(1, 9):
            lbl = ttk.Label(left_frame, text=f"Plunger Ch.{i}:")
            lbl.grid(row=row, column=0, sticky=tk.W, padx=2, pady=1)
            var = tk.DoubleVar()
            bar = ttk.Progressbar(left_frame, orient=tk.HORIZONTAL, length=120, mode='determinate', variable=var)
            bar.grid(row=row, column=1, padx=2, pady=1)
            val = ttk.Label(left_frame, text=f"0.0 uL", font=("Consolas", 8))
            val.grid(row=row, column=2, sticky=tk.W, padx=2)
            self.motor_vars[f"P{i}"] = (var, val)
            row += 1
        sep = ttk.Separator(left_frame, orient=tk.HORIZONTAL)
        sep.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=3)
        row += 1
        self.motor_xyz = {}
        for name in ("X Gantry", "Y Gantry", "Z Head"):
            lbl = ttk.Label(left_frame, text=f"{name}:")
            lbl.grid(row=row, column=0, sticky=tk.W, padx=2, pady=1)
            val = ttk.Label(left_frame, text=f"0.0 mm", font=("Consolas", 8))
            val.grid(row=row, column=1, columnspan=2, sticky=tk.W, padx=2)
            self.motor_xyz[name] = val
            row += 1
        ttk.Label(left_frame, text=f"Tip Ejector:", foreground="gray").grid(row=row, column=0, sticky=tk.W, padx=2)
        self.tip_eject_lbl = ttk.Label(left_frame, text="OFF", foreground="gray")
        self.tip_eject_lbl.grid(row=row, column=1, sticky=tk.W, padx=2)
        row += 1
        ttk.Label(left_frame, text=f"Shuttle:", foreground="gray").grid(row=row, column=0, sticky=tk.W, padx=2)
        self.shuttle_lbl = ttk.Label(left_frame, text="0.0 mm", foreground="gray")
        self.shuttle_lbl.grid(row=row, column=1, sticky=tk.W, padx=2)
        row += 1

        mid_frame = ttk.LabelFrame(main_paned, text=" [ Sensor Panel — 20 Sensors ] ", padding=5)
        main_paned.add(mid_frame, weight=1)
        self.sensor_labels = {}
        r = 0
        ttk.Label(mid_frame, text="[Tip Presence × 8]", font=("Arial", 8, "bold")).grid(row=r, column=0, columnspan=4, sticky=tk.W)
        r += 1
        for i in range(8):
            self.sensor_labels[f"TIP_{i+1}"] = ttk.Label(mid_frame, text=f"Ch.{i+1}: ⚪", font=("Consolas", 8))
            self.sensor_labels[f"TIP_{i+1}"].grid(row=r, column=i % 4, sticky=tk.W, padx=2)
            if i % 4 == 3: r += 1
        r += 1
        ttk.Label(mid_frame, text="[LLD × 8]", font=("Arial", 8, "bold")).grid(row=r, column=0, columnspan=4, sticky=tk.W)
        r += 1
        for i in range(8):
            self.sensor_labels[f"LLD_{i+1}"] = ttk.Label(mid_frame, text=f"Ch.{i+1}: ▲", font=("Consolas", 8))
            self.sensor_labels[f"LLD_{i+1}"].grid(row=r, column=i % 4, sticky=tk.W, padx=2)
            if i % 4 == 3: r += 1
        r += 1
        ttk.Label(mid_frame, text="[System Sensors]", font=("Arial", 8, "bold")).grid(row=r, column=0, columnspan=4, sticky=tk.W)
        r += 1
        self.sensor_labels["PRESSURE"] = ttk.Label(mid_frame, text="Pressure: 0 mbar", font=("Consolas", 8))
        self.sensor_labels["PRESSURE"].grid(row=r, column=0, columnspan=4, sticky=tk.W, padx=2)
        r += 1
        self.sensor_labels["HOME_X"] = ttk.Label(mid_frame, text="Home X: ⚪", font=("Consolas", 8))
        self.sensor_labels["HOME_X"].grid(row=r, column=0, sticky=tk.W, padx=2)
        self.sensor_labels["HOME_Y"] = ttk.Label(mid_frame, text="Home Y: ⚪", font=("Consolas", 8))
        self.sensor_labels["HOME_Y"].grid(row=r, column=1, sticky=tk.W, padx=2)
        self.sensor_labels["HOME_Z"] = ttk.Label(mid_frame, text="Home Z: ⚪", font=("Consolas", 8))
        self.sensor_labels["HOME_Z"].grid(row=r, column=2, sticky=tk.W, padx=2)

        right_frame = ttk.LabelFrame(main_paned, text=" [ Log & Animation ] ", padding=5)
        main_paned.add(right_frame, weight=2)

        self.canvas = tk.Canvas(right_frame, height=120, bg="#1a1a2e")
        self.canvas.pack(fill=tk.X, pady=3)
        self.draw_idle_animation()

        self.log_box = scrolledtext.ScrolledText(right_frame, height=18, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True)

    def draw_idle_animation(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 800
        h = 120
        cx, cy = 120, 60
        self.canvas.create_text(cx, cy - 25, text="[Gantry]", fill="#4a9eff", font=("Arial", 7))
        self.canvas.create_rectangle(cx - 40, cy - 15, cx + 40, cy + 15, outline="#4a9eff", fill="#162447", tags="gantry_head")
        self.canvas.create_text(cx, cy, text="IDLE", fill="gray", font=("Arial", 8))
        self.canvas.create_line(50, cy + 20, w - 50, cy + 20, fill="#333355")
        for i in range(8):
            bx = 260 + i * 28
            by = cy + 20
            self.canvas.create_rectangle(bx - 8, by - 30, bx + 8, by, outline="#4a9eff" if i == 0 else "#334466", fill="#0d1b3e", tags=f"tip_{i}")
            self.canvas.create_text(bx, by + 10, text=f"Ch{i+1}", fill="gray", font=("Arial", 6))

    def update_animation(self, active_ch=0, volume=0):
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 800
        h = 120
        cx, cy = 120, 50
        self.canvas.create_text(cx, cy - 25, text="[Gantry]", fill="#4a9eff", font=("Arial", 7))
        head_fill = "#4a9eff"
        self.canvas.create_rectangle(cx - 40, cy - 15, cx + 40, cy + 15, outline="#4a9eff", fill=head_fill, tags="gantry_head")
        self.canvas.create_text(cx, cy, text="DISPENSING", fill="white", font=("Arial", 8, "bold"))
        self.canvas.create_line(50, cy + 25, w - 50, cy + 25, fill="#333355")
        for i in range(8):
            bx = 260 + i * 28
            by = cy + 25
            fill = "#0d1b3e"
            outline = "#4a9eff" if i == active_ch else "#334466"
            tip_height = int((volume / 300) * 30) if i == active_ch else 5
            self.canvas.create_rectangle(bx - 8, by - 30, bx + 8, by - tip_height, outline=outline, fill=fill)
            vol_color = "#4a9eff" if i == active_ch else "#1a3a6e"
            self.canvas.create_rectangle(bx - 8, by - tip_height, bx + 8, by, outline=outline, fill=vol_color)
            self.canvas.create_text(bx, by + 10, text=f"Ch{i+1}", fill="gray", font=("Arial", 6))

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def update_motor_display(self):
        for i in range(8):
            var, val_lbl = self.motor_vars[f"P{i+1}"]
            var.set(min(self.motor.plungers[i] / 300.0 * 100, 100))
            val_lbl.config(text=f"{self.motor.plungers[i]:.1f} uL")
        self.motor_xyz["X Gantry"].config(text=f"{self.motor.X:.1f} mm")
        self.motor_xyz["Y Gantry"].config(text=f"{self.motor.Y:.1f} mm")
        self.motor_xyz["Z Head"].config(text=f"{self.motor.Z:.2f} mm")
        self.tip_eject_lbl.config(text="ON ●" if self.motor.tip_ejector else "OFF ○")
        self.shuttle_lbl.config(text=f"{self.motor.shuttle_pos:.1f} mm")

    def update_sensor_display(self):
        for i in range(8):
            tip_char = "●" if self.sensor.tips[i] else "○"
            self.sensor_labels[f"TIP_{i+1}"].config(text=f"Ch.{i+1}: {tip_char}")
            ll_char = "⬇" if self.sensor.lld[i] else "▲"
            self.sensor_labels[f"LLD_{i+1}"].config(text=f"Ch.{i+1}: {ll_char}")
        self.sensor_labels["PRESSURE"].config(text=f"Pressure: {self.sensor.pressure:+.0f} mbar",
            foreground="red" if abs(self.sensor.pressure) > 300 else "black")
        self.sensor_labels["HOME_X"].config(text=f"Home X: {'●' if self.sensor.home_x else '○'}")
        self.sensor_labels["HOME_Y"].config(text=f"Home Y: {'●' if self.sensor.home_y else '○'}")
        self.sensor_labels["HOME_Z"].config(text=f"Home Z: {'●' if self.sensor.home_z else '○'}")

    def simulate_dispense(self, volume):
        self.motor.home_all()
        self.sensor.home_x = self.sensor.home_y = self.sensor.home_z = True
        self.sensor.tips = [True] * 8
        self.update_motor_display()
        self.update_sensor_display()
        self.log(f"[Init] Homing complete. Tips loaded.")
        self.motor.X = 50 + random.uniform(-5, 5)
        self.motor.Y = 30 + random.uniform(-3, 3)
        self.motor.Z = 10
        self.log(f"[Move] Gantry → X={self.motor.X:.1f}, Y={self.motor.Y:.1f}, Z={self.motor.Z:.1f}")
        self.update_motor_display()
        time.sleep(0.3)

        active_ch = random.randint(0, 7)
        self.sensor.lld[active_ch] = True
        self.sensor.pressure = -random.uniform(50, 200)
        self.log(f"[LLD] Ch.{active_ch+1} liquid contact detected. Pressure: {self.sensor.pressure:.0f} mbar")
        self.update_sensor_display()
        time.sleep(0.2)

        vol_per_step = volume / 10
        for step in range(11):
            self.motor.plungers[active_ch] = min(step * vol_per_step, volume)
            self.sensor.pressure = -200 + random.uniform(-20, 20)
            self.update_motor_display()
            self.update_sensor_display()
            self.update_animation(active_ch, self.motor.plungers[active_ch])
            time.sleep(0.08)
        self.motor.Z = 15
        self.sensor.lld[active_ch] = False
        self.sensor.pressure = 0
        self.log(f"[Done] Dispensed {volume} uL via Ch.{active_ch+1}")
        self.update_motor_display()
        self.update_sensor_display()
        self.update_animation()
        self.draw_idle_animation()

    def remote_dispense(self, volume, conn):
        self.log(f"[Network] Rx Dispense Request: {volume} uL")
        self.simulate_dispense(volume)
        self.log("[System] Dispense complete. Sending response...")
        conn.sendall(b"DISPENSE_SUCCESS")
        conn.close()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50051))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data.startswith("DISPENSE:"):
                vol = int(data.split(":")[1])
                self.after(0, self.remote_dispense, vol, conn)


if __name__ == "__main__":
    app = LiquidHandlerV3()
    app.mainloop()
