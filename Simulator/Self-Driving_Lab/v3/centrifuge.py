import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket
import time
import random
import math

MOTOR_SPECS = {
    "MAIN_DRIVE":  {"type": "BLDC", "max_rpm": 14000, "power": 500, "unit": "W"},
    "LID_LOCK":    {"type": "DC Solenoid", "positions": 2, "unit": "locked/unlocked"},
    "COMPRESSOR":  {"type": "Reciprocating", "range": "4~30 °C", "unit": "cooling"}
}

SENSOR_SPECS = {
    "RPM_ENCODER":     {"type": "Hall sensor", "range": "0~14000 RPM"},
    "DOOR_INTERLOCK":  {"type": "Microswitch", "range": "locked/unlocked"},
    "IMBALANCE":       {"type": "Accelerometer", "range": "0~10 g"},
    "CHAMBER_TEMP":    {"type": "PT1000", "range": "-10~40 °C"},
    "ROTOR_DETECT":    {"type": "RFID", "range": "rotor type"},
    "VIBRATION":       {"type": "MEMS Accelerometer", "range": "0~50 mm/s"}
}


class CentrifugeV3(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌀 Centrifuge Simulator v3 — Eppendorf 5810R")
        self.geometry("1000x700")
        self.current_rpm = 0
        self.target_rpm = 0
        self.state = "STOPPED"
        self.door_locked = False
        self.chamber_temp = 22.1
        self.imbalance = 0.0
        self.vibration = 0.0
        self.rotor_type = "FA-45-6-30 (6×50 mL)"
        self.current_draw = 0.0
        self.initUI()
        threading.Thread(target=self.start_server, daemon=True).start()
        self.log("[System] Server listening on Port 50054...")
        self.log(f"[System] Motors: {len(MOTOR_SPECS)} total")
        self.log(f"[System] Sensors: {len(SENSOR_SPECS)} total")

    def initUI(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left = ttk.LabelFrame(main_paned, text=" [ Motor Panel — Drive Telemetry ] ", padding=5)
        main_paned.add(left, weight=1)
        self.motor_labels = {}
        ttk.Label(left, text=f"Main Drive (BLDC, 500W):", font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=5, pady=5)

        self.rpm_progress = ttk.Progressbar(left, orient=tk.VERTICAL, length=250, mode='determinate')
        self.rpm_progress.pack(pady=10)
        self.rpm_label = ttk.Label(left, text=f"0 / 0 RPM", font=("Consolas", 12, "bold"))
        self.rpm_label.pack()
        self.current_lbl = ttk.Label(left, text=f"Current: 0.0 A", font=("Consolas", 9))
        self.current_lbl.pack(pady=2)
        self.power_lbl = ttk.Label(left, text=f"Power: 0.0 W", font=("Consolas", 9))
        self.power_lbl.pack(pady=2)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Label(left, text=f"Lid Lock:", font=("Arial", 8)).pack(anchor=tk.W, padx=5)
        self.lid_lock_lbl = ttk.Label(left, text="UNLOCKED 🔓", font=("Consolas", 9))
        self.lid_lock_lbl.pack(anchor=tk.W, padx=5)

        ttk.Label(left, text=f"Compressor:", font=("Arial", 8)).pack(anchor=tk.W, padx=5, pady=2)
        self.compressor_lbl = ttk.Label(left, text="Standby", font=("Consolas", 9))
        self.compressor_lbl.pack(anchor=tk.W, padx=5)

        mid = ttk.LabelFrame(main_paned, text=" [ Rotor Animation ] ", padding=5)
        main_paned.add(mid, weight=2)
        self.rotor_canvas = tk.Canvas(mid, bg="#1a1a2e")
        self.rotor_canvas.pack(fill=tk.BOTH, expand=True)
        self.rotor_angle = 0
        self.draw_rotor()

        right = ttk.LabelFrame(main_paned, text=" [ Sensor Panel — 6 Sensors ] ", padding=5)
        main_paned.add(right, weight=1)
        self.sensor_labels = {}
        sensors_info = [
            ("RPM Encoder", lambda: f"{self.current_rpm} RPM", "hall"),
            ("Door Interlock", lambda: "LOCKED 🔒" if self.door_locked else "UNLOCKED 🔓", "switch"),
            ("Imbalance", lambda: f"{self.imbalance:.2f} g", "accel"),
            ("Vibration", lambda: f"{self.vibration:.1f} mm/s", "accel"),
            ("Chamber Temp", lambda: f"{self.chamber_temp:.1f} °C", "temp"),
            ("Rotor Detect", lambda: self.rotor_type, "rfid"),
        ]
        for name, getter, stype in sensors_info:
            frame = ttk.LabelFrame(right, text=f" {name} ", padding=3)
            frame.pack(fill=tk.X, padx=3, pady=2)
            lbl = ttk.Label(frame, text=getter(), font=("Consolas", 9))
            lbl.pack(anchor=tk.W)
            ttk.Label(frame, text=f"({stype})", font=("Arial", 7), foreground="gray").pack(anchor=tk.E)
            self.sensor_labels[name] = lbl

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        log_frame = ttk.LabelFrame(bottom_frame, text=" [ Log ] ", padding=3)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.insert(tk.END, "[System] Initialized.\n")

        self.anim_running = True
        self.animation_loop()

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def draw_rotor(self):
        self.rotor_canvas.delete("all")
        w = self.rotor_canvas.winfo_width() or 400
        h = self.rotor_canvas.winfo_height() or 300
        cx, cy = w // 2, h // 2
        max_r = min(w, h) // 2 - 30

        if self.state == "STOPPED":
            self.rotor_canvas.create_oval(cx - max_r, cy - max_r, cx + max_r, cy + max_r,
                                         outline="#334466", width=3, fill="#0d1b3e")
            self.rotor_canvas.create_text(cx, cy, text="⏹", fill="#4a9eff", font=("Arial", 40))
            self.rotor_canvas.create_text(cx, cy + 40, text="STOPPED", fill="gray", font=("Arial", 12))
        else:
            speed_factor = min(self.current_rpm / 14000, 1.0)
            rpm_color = "#00ff88" if speed_factor < 0.3 else "#ffaa00" if speed_factor < 0.7 else "#ff4444"
            self.rotor_angle = (self.rotor_angle + max(1, int(speed_factor * 20))) % 360
            rad = math.radians(self.rotor_angle)
            self.rotor_canvas.create_oval(cx - max_r, cy - max_r, cx + max_r, cy + max_r,
                                         outline=rpm_color, width=3, fill="#0d1b3e")
            for i in range(6):
                a = rad + i * math.pi / 3
                bx = cx + int(max_r * 0.7 * math.cos(a))
                by = cy + int(max_r * 0.7 * math.sin(a))
                self.rotor_canvas.create_oval(bx - 18, by - 18, bx + 18, by + 18,
                                            outline=rpm_color, fill=rpm_color, stipple="gray25")
                self.rotor_canvas.create_line(cx, cy, bx, by, fill=rpm_color, width=2)
            self.rotor_canvas.create_oval(cx - 25, cy - 25, cx + 25, cy + 25,
                                         outline="#4a9eff", fill="#162447")
            self.rotor_canvas.create_text(cx, cy, text=f"{self.current_rpm}", fill="white",
                                         font=("Arial", 9, "bold"))

            state_color = {"ACCELERATING": "#ffaa00", "RUNNING": "#00ff88", "DECELERATING": "#ff6600"}.get(self.state, "white")
            self.rotor_canvas.create_text(cx, cy + max_r - 20, text=f"{self.state} | {self.current_rpm} RPM",
                                         fill=state_color, font=("Arial", 9, "bold"))

    def animation_loop(self):
        self.draw_rotor()
        self.after(50, self.animation_loop)

    def update_sensors(self):
        self.sensor_labels["RPM Encoder"].config(text=f"{self.current_rpm} RPM")
        self.sensor_labels["Door Interlock"].config(text="LOCKED 🔒" if self.door_locked else "UNLOCKED 🔓")
        self.sensor_labels["Imbalance"].config(text=f"{self.imbalance:.2f} g",
            foreground="red" if self.imbalance > 5.0 else "black")
        self.sensor_labels["Vibration"].config(text=f"{self.vibration:.1f} mm/s")
        self.sensor_labels["Chamber Temp"].config(text=f"{self.chamber_temp:.1f} °C")
        self.sensor_labels["Rotor Detect"].config(text=self.rotor_type)

    def update_motors(self):
        pct = (self.current_rpm / 14000) * 100
        self.rpm_progress['value'] = pct
        self.rpm_label.config(text=f"{self.current_rpm} / {self.target_rpm} RPM")
        self.current_draw = (self.current_rpm / 14000) * 500 * 0.85 + random.uniform(-2, 2)
        self.current_lbl.config(text=f"Current: {self.current_draw:.1f} A")
        power = self.current_draw * 48
        self.power_lbl.config(text=f"Power: {power:.0f} W")

    def physics_loop(self, conn):
        self.chamber_temp += random.uniform(-0.1, 0.1)
        self.vibration = (self.current_rpm / 14000) * 3 + random.uniform(0, 1)
        self.imbalance = random.uniform(0, 0.5)

        if self.state == "ACCELERATING":
            if self.current_rpm < self.target_rpm:
                self.current_rpm = min(self.current_rpm + 1000, self.target_rpm)
                self.chamber_temp += 0.05
                self.update_motors()
                self.update_sensors()
                self.after(30, lambda: self.physics_loop(conn))
            else:
                self.current_rpm = self.target_rpm
                self.state = "RUNNING"
                self.log(f"[System] Target {self.target_rpm} RPM reached. Spinning...")
                self.update_motors()
                self.update_sensors()
                self.after(1500, lambda: self.trigger_deceleration(conn))

        elif self.state == "DECELERATING":
            if self.current_rpm > 0:
                self.current_rpm = max(self.current_rpm - 1200, 0)
                self.chamber_temp -= 0.03
                self.update_motors()
                self.update_sensors()
                self.after(30, lambda: self.physics_loop(conn))
            else:
                self.current_rpm = 0
                self.state = "STOPPED"
                self.door_locked = False
                self.lid_lock_lbl.config(text="UNLOCKED 🔓", foreground="black")
                self.compressor_lbl.config(text="Standby")
                self.log("[System] Spin done. Door unlocked.")
                self.update_motors()
                self.update_sensors()
                conn.sendall(b"SPIN_SUCCESS")
                conn.close()

    def trigger_deceleration(self, conn):
        self.state = "DECELERATING"
        self.log("[System] Hold complete. Decelerating...")
        self.physics_loop(conn)

    def start_spin(self, target_rpm, conn):
        self.state = "ACCELERATING"
        self.target_rpm = min(target_rpm, 14000)
        self.door_locked = True
        self.lid_lock_lbl.config(text="LOCKED 🔒", foreground="red")
        self.compressor_lbl.config(text="Cooling ON ❄", foreground="#4a9eff")
        self.log(f"[Network] Rx Spin Request: {target_rpm} RPM")
        self.log(f"[Motor] BLDC drive engaged. Locking door...")
        self.update_motors()
        self.update_sensors()
        self.physics_loop(conn)

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50054))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data.startswith("SPIN:"):
                rpm = int(data.split(":")[1])
                self.after(0, self.start_spin, rpm, conn)


if __name__ == "__main__":
    app = CentrifugeV3()
    app.mainloop()
