import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket
import time
import random

MOTOR_SPECS = {
    "ELEVATOR": {"type": "Stepper + Ball screw", "slots": 50, "speed": 200, "unit": "mm/s"},
    "SHUTTLE":  {"type": "DC Brushed", "positions": 2, "unit": "extended/retracted"},
    "DOOR":     {"type": "DC", "positions": 2, "unit": "open/closed"},
    "FAN":      {"type": "EC Fan", "max_rpm": 3000, "unit": "RPM"}
}

SENSOR_SPECS = {
    "SLOT_OCCUPANCY": {"count": 50, "type": "Photoelectric", "range": "present/empty"},
    "DOOR_POSITION":  {"type": "Microswitch", "range": "open/closed"},
    "TEMP_1":         {"type": "PT100", "range": "4~60 °C"},
    "TEMP_2":         {"type": "PT100", "range": "4~60 °C"},
    "HUMIDITY":       {"type": "Capacitive", "range": "20~80 %RH"},
    "ELEVATOR_HOME":  {"type": "Optical limit", "range": "homed/not_homed"}
}


class PlateHotelV3(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🏨 Plate Hotel Simulator v3 — Liconic STX Series")
        self.geometry("950x700")
        self.slots = [False] * 50
        self.elevator_level = 1
        self.shuttle_extended = False
        self.door_open = False
        self.fan_rpm = 1500
        self.temp_1 = 22.5
        self.temp_2 = 23.1
        self.humidity = 45.0
        self.elevator_homed = True
        self.door_sensor = "closed"
        self.initUI()
        threading.Thread(target=self.start_server, daemon=True).start()
        self.simulation_tick()
        self.log("[System] Server listening on Port 50052...")
        self.log(f"[System] Motors: {len(MOTOR_SPECS)} total")
        self.log(f"[System] Sensors: {sum(v['count'] if isinstance(v.get('count'), int) else 1 for v in SENSOR_SPECS.values())} total")

    def initUI(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left = ttk.LabelFrame(main_paned, text=" [ Motor Panel — 4 Motors ] ", padding=5)
        main_paned.add(left, weight=1)

        self.elevator_bar = ttk.Progressbar(left, orient=tk.VERTICAL, length=300, mode='determinate')
        self.elevator_bar.pack(pady=5)
        self.elevator_lbl = ttk.Label(left, text=f"Elevator: Level {self.elevator_level}/50", font=("Consolas", 9))
        self.elevator_lbl.pack()
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        self.shuttle_lbl = ttk.Label(left, text="Shuttle: RETRACTED", font=("Consolas", 9))
        self.shuttle_lbl.pack(anchor=tk.W, padx=10, pady=2)
        self.door_lbl = ttk.Label(left, text="Door: CLOSED", font=("Consolas", 9))
        self.door_lbl.pack(anchor=tk.W, padx=10, pady=2)
        self.fan_lbl = ttk.Label(left, text=f"Fan: {self.fan_rpm} RPM", font=("Consolas", 9))
        self.fan_lbl.pack(anchor=tk.W, padx=10, pady=2)

        mid = ttk.LabelFrame(main_paned, text=" [ Slot Grid — 50× Photoelectric Sensors ] ", padding=5)
        main_paned.add(mid, weight=2)
        self.slot_buttons = {}
        slot_canvas = tk.Canvas(mid, height=360)
        scrollbar = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=slot_canvas.yview)
        slot_frame = ttk.Frame(slot_canvas)
        slot_frame.bind("<Configure>", lambda e: slot_canvas.configure(scrollregion=slot_canvas.bbox("all")))
        slot_canvas.create_window((0, 0), window=slot_frame, anchor="nw")
        slot_canvas.configure(yscrollcommand=scrollbar.set)
        slot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for row in range(10):
            for col in range(5):
                idx = row * 5 + col
                f = ttk.Frame(slot_frame)
                f.grid(row=row, column=col, padx=2, pady=2)
                lbl = tk.Label(f, width=8, height=2, bg="#A8DADC", relief="ridge",
                              text=f"S{idx+1}\n[PLATE]" if random.random() > 0.3 else f"S{idx+1}\n[EMPTY]",
                              font=("Arial", 7))
                lbl.pack()
                self.slot_buttons[idx] = lbl
                if "EMPTY" in lbl.cget("text"):
                    self.slots[idx] = False
                else:
                    self.slots[idx] = True

        right = ttk.LabelFrame(main_paned, text=" [ Sensor Panel — Environment ] ", padding=5)
        main_paned.add(right, weight=1)

        self.sensor_labels = {}
        ttk.Label(right, text=f"Door Position:", font=("Arial", 8)).pack(anchor=tk.W, padx=5, pady=2)
        self.sensor_labels["DOOR"] = ttk.Label(right, text="CLOSED ○", font=("Consolas", 9))
        self.sensor_labels["DOOR"].pack(anchor=tk.W, padx=5)

        ttk.Label(right, text=f"Temperature 1 (upper):", font=("Arial", 8)).pack(anchor=tk.W, padx=5, pady=2)
        self.sensor_labels["TEMP_1"] = ttk.Label(right, text=f"{self.temp_1:.1f} °C", font=("Consolas", 9))
        self.sensor_labels["TEMP_1"].pack(anchor=tk.W, padx=5)

        ttk.Label(right, text=f"Temperature 2 (lower):", font=("Arial", 8)).pack(anchor=tk.W, padx=5, pady=2)
        self.sensor_labels["TEMP_2"] = ttk.Label(right, text=f"{self.temp_2:.1f} °C", font=("Consolas", 9))
        self.sensor_labels["TEMP_2"].pack(anchor=tk.W, padx=5)

        ttk.Label(right, text=f"Humidity:", font=("Arial", 8)).pack(anchor=tk.W, padx=5, pady=2)
        self.sensor_labels["HUMIDITY"] = ttk.Label(right, text=f"{self.humidity:.1f} %RH", font=("Consolas", 9))
        self.sensor_labels["HUMIDITY"].pack(anchor=tk.W, padx=5)

        ttk.Label(right, text=f"Elevator Home:", font=("Arial", 8)).pack(anchor=tk.W, padx=5, pady=2)
        self.sensor_labels["HOME"] = ttk.Label(right, text="HOMED ●", foreground="green", font=("Consolas", 9))
        self.sensor_labels["HOME"].pack(anchor=tk.W, padx=5)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(right, text=f"Slot Count:", font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=5)
        self.slot_count_lbl = ttk.Label(right, text="", font=("Consolas", 9))
        self.slot_count_lbl.pack(anchor=tk.W, padx=5)

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        self.log_box = scrolledtext.ScrolledText(bottom_frame, height=10, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.insert(tk.END, "[System] Initialized.\n")

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def simulation_tick(self):
        self.temp_1 += random.uniform(-0.3, 0.3)
        self.temp_2 += random.uniform(-0.2, 0.2)
        self.humidity += random.uniform(-0.5, 0.5)
        self.temp_1 = max(4, min(60, self.temp_1))
        self.temp_2 = max(4, min(60, self.temp_2))
        self.humidity = max(20, min(80, self.humidity))

        self.sensor_labels["TEMP_1"].config(text=f"{self.temp_1:.1f} °C")
        self.sensor_labels["TEMP_2"].config(text=f"{self.temp_2:.1f} °C")
        self.sensor_labels["HUMIDITY"].config(text=f"{self.humidity:.1f} %RH")

        occupied = sum(1 for v in self.slots if v)
        self.slot_count_lbl.config(text=f"Occupied: {occupied}/50  Empty: {50-occupied}/50")
        self.after(3000, self.simulation_tick)

    def eject_plate(self, slot_num, conn):
        if 1 <= slot_num <= 50:
            idx = slot_num - 1
            if self.slots[idx]:
                self.log(f"[Network] Executing EjectPlate for Slot {slot_num}")
                self.door_open = True
                self.door_sensor = "open"
                self.sensor_labels["DOOR"].config(text="OPEN ●", foreground="orange")
                self.door_lbl.config(text="Door: OPEN", foreground="orange")
                self.log("[Motor] Door opening...")
                time.sleep(0.3)

                target_level = (idx // 5) + 1
                self.log(f"[Motor] Elevator moving to level {target_level}...")
                for lev in range(self.elevator_level, target_level + (1 if target_level > self.elevator_level else -1),
                                1 if target_level > self.elevator_level else -1):
                    self.elevator_level = lev
                    self.elevator_bar['value'] = (lev / 50) * 100
                    self.elevator_lbl.config(text=f"Elevator: Level {lev}/50")
                    time.sleep(0.05)
                self.log(f"[Motor] Elevator at level {target_level}. Shuttle extending...")

                self.shuttle_extended = True
                self.shuttle_lbl.config(text="Shuttle: EXTENDED", foreground="green")
                time.sleep(0.2)

                self.slots[idx] = False
                self.slot_buttons[idx].config(bg="#E63946", text=f"S{slot_num}\n[EMPTY]")
                self.log(f"[Sensor] Slot {slot_num} occupancy → EMPTY detected")
                time.sleep(0.2)

                self.shuttle_extended = False
                self.shuttle_lbl.config(text="Shuttle: RETRACTED", foreground="black")
                self.sensor_labels["DOOR"].config(text="CLOSED ○", foreground="black")
                self.door_lbl.config(text="Door: CLOSED", foreground="black")
                self.door_open = False
                self.door_sensor = "closed"
                self.log("[Motor] Door closing complete.")
                conn.sendall(b"SUCCESS")
            else:
                self.log(f"[Skip] Slot {slot_num} already empty.")
                conn.sendall(b"SUCCESS")
        conn.close()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50052))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data and data.startswith("EJECT:"):
                slot = int(data.split(":")[1])
                self.after(0, self.eject_plate, slot, conn)
            else:
                conn.close()


if __name__ == "__main__":
    app = PlateHotelV3()
    app.mainloop()
