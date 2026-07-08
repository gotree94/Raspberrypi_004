import tkinter as tk
from tkinter import scrolledtext
import socket
import threading
import json
import random
import time
import argparse


class VirtualScreener:
    def __init__(self, port=50065):
        self.port = port
        self.library_size = 10000
        self.hit_count = 0
        self.hit_rate = 0.0
        self.diversity_score = random.uniform(0.3, 0.9)
        self.enrichment_factor = random.uniform(1.0, 50.0)
        self.compounds = []
        self.motors = {
            "Library Loading": "IDLE",
            "Fingerprint Calc": "IDLE",
            "Similarity Search": "IDLE",
            "Pharmacophore": "IDLE",
            "Clustering": "IDLE",
        }
        self.motor_order = list(self.motors.keys())
        self.motor_labels = {}
        self.sensor_labels = {}
        self.canvas = None

        self._init_compounds()
        self._init_gui()
        self._start_tcp_server()

    def _init_compounds(self):
        random.seed(42)
        atoms_pool = ["C", "N", "O", "S", "F", "Cl", "Br", "P", "I"]
        self.compounds = []
        for i in range(10000):
            length = random.randint(5, 30)
            smi = "".join(random.choice(atoms_pool) for _ in range(length))
            self.compounds.append({
                "id": f"CMP{i+1:05d}",
                "smiles": smi,
                "weight": random.uniform(100, 800),
                "logp": random.uniform(-2, 8),
                "hbd": random.randint(0, 10),
                "hba": random.randint(0, 10),
                "tpsa": random.uniform(0, 200),
                "rotb": random.randint(0, 15),
                "active": False,
                "x": random.uniform(0, 100),
                "y": random.uniform(0, 100),
            })

    def _init_gui(self):
        self.root = tk.Tk()
        self.root.title(f"Virtual Screening Agent (Port {self.port})")
        self.root.geometry("1000x700")

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = tk.LabelFrame(main_frame, text="Motors", width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        for m in self.motor_order:
            row = tk.Frame(left_frame)
            row.pack(fill=tk.X, padx=5, pady=3)
            tk.Label(row, text=m, width=20, anchor=tk.W).pack(side=tk.LEFT)
            ind = tk.Label(row, text="IDLE", bg="gray", fg="white", width=10)
            ind.pack(side=tk.RIGHT)
            self.motor_labels[m] = ind

        center_frame = tk.Frame(main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        cframe = tk.LabelFrame(center_frame, text="Chemical Space")
        cframe.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(cframe, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Configure>", self._draw_plot)

        right_frame = tk.LabelFrame(main_frame, text="Sensors", width=220)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_frame.pack_propagate(False)

        sensors = [
            ("Library Size", f"{self.library_size:,}"),
            ("Hit Count", "0"),
            ("Hit Rate", "0.00%"),
            ("Diversity Score", f"{self.diversity_score:.3f}"),
            ("Enrichment Factor", f"{self.enrichment_factor:.2f}"),
        ]
        for name, val in sensors:
            row = tk.Frame(right_frame)
            row.pack(fill=tk.X, padx=5, pady=3)
            tk.Label(row, text=name, width=18, anchor=tk.W).pack(side=tk.LEFT)
            lbl = tk.Label(row, text=val, bg="lightgray", width=10, anchor=tk.E)
            lbl.pack(side=tk.RIGHT)
            self.sensor_labels[name] = lbl

        log_frame = tk.LabelFrame(self.root, text="Command Log")
        log_frame.pack(fill=tk.BOTH, padx=5, pady=(0, 5))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _draw_plot(self, event=None):
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 400
        h = self.canvas.winfo_height() or 300
        if w < 10 or h < 10:
            return
        m = 30
        sw, sh = w - 2 * m, h - 2 * m
        for cpd in self.compounds:
            cx = m + (cpd["x"] / 100.0) * sw
            cy = m + (cpd["y"] / 100.0) * sh
            color = "#d32f2f" if cpd["active"] else "#b0b0b0"
            self.canvas.create_oval(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5, fill=color, outline="")

    def _log(self, msg):
        if self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

    def _update_motor(self, name, state):
        colors = {"IDLE": "gray", "RUNNING": "green", "COMPLETED": "blue", "FAILED": "red"}
        self.motors[name] = state
        if name in self.motor_labels:
            self.motor_labels[name].config(text=state, bg=colors.get(state, "gray"))

    def _update_sensor(self, name, value):
        if name in self.sensor_labels:
            self.sensor_labels[name].config(text=value)

    def _run_motors(self):
        for motor in self.motor_order:
            self._update_motor(motor, "RUNNING")
            self._log(f"Motor: {motor} started")
            delay = random.uniform(2, 5)
            time.sleep(delay)
            if random.random() < 0.05:
                self._update_motor(motor, "FAILED")
                self._log(f"Motor: {motor} FAILED")
            else:
                self._update_motor(motor, "COMPLETED")
                self._log(f"Motor: {motor} completed in {delay:.1f}s")
        self._log("All motors completed")

    def _screen_library(self, smiles):
        self._log(f"SCREEN: {smiles[:50]}...")

        def task():
            self._run_motors()
            hr = random.uniform(0.5, 15.0)
            hc = int(self.library_size * hr / 100.0)
            self.hit_count = hc
            self.hit_rate = hr
            self.diversity_score = random.uniform(0.3, 0.95)
            self.enrichment_factor = random.uniform(1.0, 80.0)
            idxs = set(random.sample(range(self.library_size), min(hc, self.library_size)))
            for i, cpd in enumerate(self.compounds):
                cpd["active"] = i in idxs
            self.root.after(0, self._update_sensors)
            self.root.after(0, self._draw_plot)

        threading.Thread(target=task, daemon=True).start()
        return "SCREENING started\n"

    def _update_sensors(self):
        self._update_sensor("Library Size", f"{self.library_size:,}")
        self._update_sensor("Hit Count", f"{self.hit_count:,}")
        self._update_sensor("Hit Rate", f"{self.hit_rate:.2f}%")
        self._update_sensor("Diversity Score", f"{self.diversity_score:.3f}")
        self._update_sensor("Enrichment Factor", f"{self.enrichment_factor:.2f}")

    def _filter_library(self, criteria):
        self._log(f"FILTER: {criteria}")
        remaining = random.randint(100, self.library_size)
        self.library_size = remaining
        self._update_sensor("Library Size", f"{self.library_size:,}")
        return f"FILTERED: {remaining} compounds remaining\n"

    def _get_status(self):
        return json.dumps({
            "library_size": self.library_size,
            "hit_count": self.hit_count,
            "hit_rate": round(self.hit_rate, 2),
            "diversity_score": round(self.diversity_score, 3),
            "enrichment_factor": round(self.enrichment_factor, 2),
            "motors": self.motors,
        }) + "\n"

    def _reset_library(self):
        self._log("RESET")
        self.library_size = 10000
        self.hit_count = 0
        self.hit_rate = 0.0
        self.diversity_score = random.uniform(0.3, 0.9)
        self.enrichment_factor = random.uniform(1.0, 50.0)
        for cpd in self.compounds:
            cpd["active"] = False
        for m in self.motor_order:
            self._update_motor(m, "IDLE")
        self._update_sensors()
        self.root.after(0, self._draw_plot)
        return "RESET OK\n"

    def _start_tcp_server(self):
        def serve():
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", self.port))
            srv.listen(5)
            self._log(f"TCP server listening on port {self.port}")
            while True:
                try:
                    conn, addr = srv.accept()
                    threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
                except:
                    break

        threading.Thread(target=serve, daemon=True).start()

    def _handle_client(self, conn, addr):
        with conn:
            self._log(f"Connection from {addr[0]}:{addr[1]}")
            try:
                data = conn.recv(4096).decode().strip()
                if not data:
                    return
                parts = data.split(":", 1)
                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "SCREEN":
                    resp = self._screen_library(arg)
                elif cmd == "FILTER":
                    resp = self._filter_library(arg)
                elif cmd == "STATUS":
                    resp = self._get_status()
                elif cmd == "RESET":
                    resp = self._reset_library()
                else:
                    resp = f"UNKNOWN: {cmd}\n"
                conn.sendall(resp.encode())
            except Exception as e:
                self._log(f"Error: {e}")

    def _on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Virtual Screening Agent")
    parser.add_argument("--port", type=int, default=50065, help="TCP port")
    args = parser.parse_args()
    app = VirtualScreener(port=args.port)
    app.run()
