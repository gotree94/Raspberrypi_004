import tkinter as tk
from tkinter import scrolledtext
import socket
import threading
import json
import random
import time
import argparse

MOTOR_NAMES = ["Protein Prep", "Ligand Prep", "Grid Gen", "Docking", "Scoring"]
SENSOR_NAMES = ["Best Affinity", "Avg Affinity", "RMSD", "H-Bonds"]
MOTOR_COLORS = {"IDLE": "#808080", "RUNNING": "#4CAF50", "COMPLETED": "#2196F3", "FAILED": "#F44336"}


class DockingAgent:
    def __init__(self, port):
        self.port = port
        self.motors = {name: "IDLE" for name in MOTOR_NAMES}
        self.sensors = {name: 0.0 for name in SENSOR_NAMES}
        self.affinity_records = []
        self.smiles_counter = 0
        self.docking_in_progress = False
        self._running = True
        self.lock = threading.Lock()

        self._build_gui()
        self._start_tcp_server()

    def _build_gui(self):
        self.root = tk.Tk()
        self.root.title(f"Molecular Docking Agent (Port {self.port})")
        self.root.geometry("960x700")
        self.root.minsize(800, 600)

        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        top = tk.Frame(main)
        top.pack(fill=tk.BOTH, expand=True)

        left = tk.LabelFrame(top, text="Motor States", width=190)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))
        left.pack_propagate(False)

        self.motor_leds = {}
        for name in MOTOR_NAMES:
            row = tk.Frame(left)
            row.pack(fill=tk.X, padx=6, pady=4)
            led = tk.Canvas(row, width=20, height=20, highlightthickness=0)
            led.pack(side=tk.LEFT, padx=(0, 6))
            self._draw_led(led, MOTOR_COLORS["IDLE"])
            tk.Label(row, text=name, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.motor_leds[name] = led

        center = tk.LabelFrame(top, text="Binding Affinities")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.canvas = tk.Canvas(center, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw_chart())

        right = tk.LabelFrame(top, text="Sensor Values", width=210)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        right.pack_propagate(False)

        self.sensor_displays = {}
        for name in SENSOR_NAMES:
            row = tk.Frame(right)
            row.pack(fill=tk.X, padx=6, pady=5)
            tk.Label(row, text=name, anchor="w", font=("TkDefaultFont", 9, "bold")).pack(fill=tk.X)
            val = tk.Label(row, text="--", anchor="e", fg="#1565C0", font=("TkDefaultFont", 11))
            val.pack(fill=tk.X)
            self.sensor_displays[name] = val

        bottom = tk.LabelFrame(main, text="Command Log")
        bottom.pack(fill=tk.BOTH, padx=0, pady=(6, 0))

        self.log_area = scrolledtext.ScrolledText(bottom, height=10, state="disabled",
                                                   font=("Consolas", 9), bg="#1E1E1E", fg="#D4D4D4",
                                                   insertbackground="white")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _draw_led(self, canvas, color):
        canvas.delete("all")
        w, h = int(canvas["width"]), int(canvas["height"])
        canvas.create_oval(1, 1, w - 1, h - 1, fill=color, outline="#333", width=1)

    def _draw_chart(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        if not self.affinity_records:
            self.canvas.create_text(w // 2, h // 2, text="No docking data — send DOCK:smiles", fill="#999")
            return

        data = sorted(self.affinity_records, key=lambda x: x[1])[:8]
        n = len(data)
        min_val = data[-1][1] if data else -15
        bar_gap = 6
        bar_h = min(38, (h - 30 - (n - 1) * bar_gap) // n)
        if bar_h < 8:
            bar_h = 8
        y_start = 18
        label_w = 70
        max_bar_w = w - label_w - 50

        for i, (label, val) in enumerate(data):
            y = y_start + i * (bar_h + bar_gap)
            t = val / min_val if min_val < 0 else 0
            bar_w = t * max_bar_w
            r = int(255 * t)
            g = int(255 * (1 - t))
            b = 0
            color = f"#{r:02x}{g:02x}{b:02x}"

            self.canvas.create_rectangle(label_w, y, label_w + bar_w, y + bar_h,
                                          fill=color, outline="#333", width=1)
            self.canvas.create_text(label_w - 4, y + bar_h // 2, text=f"{val:.2f}",
                                    anchor="e", font=("TkDefaultFont", 9))
            self.canvas.create_text(label_w + bar_w + 4, y + bar_h // 2, text=label,
                                    anchor="w", font=("TkDefaultFont", 8))

    def set_motor_state(self, name, state):
        with self.lock:
            self.motors[name] = state
        color = MOTOR_COLORS[state]
        self.root.after(0, lambda n=name, c=color: self._draw_led(self.motor_leds[n], c))

    def set_sensor_value(self, name, value):
        with self.lock:
            self.sensors[name] = value
        unit = " kcal/mol" if "Affinity" in name else (" \u00c5" if name == "RMSD" else "")
        text = f"{value:.2f}{unit}" if isinstance(value, float) else f"{value}{unit}"
        self.root.after(0, lambda n=name, t=text: self.sensor_displays[n].config(text=t))

    def log(self, msg):
        self.root.after(0, lambda: self._log_impl(msg))

    def _log_impl(self, msg):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def _start_tcp_server(self):
        def serve():
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(("0.0.0.0", self.port))
            self.server.listen(5)
            self.server.settimeout(1.0)
            self.log(f"TCP server listening on 0.0.0.0:{self.port}")
            while self._running:
                try:
                    conn, addr = self.server.accept()
                    threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except OSError:
                    break
            self.server.close()

        threading.Thread(target=serve, daemon=True).start()

    def _handle_client(self, conn, addr):
        self.log(f"Connection from {addr[0]}:{addr[1]}")
        try:
            raw = conn.recv(8192).decode().strip()
            if not raw:
                return
            resp = self.process_command(raw)
            conn.sendall(resp.encode())
        except Exception as e:
            try:
                conn.sendall(f"ERROR: {e}".encode())
            except OSError:
                pass
        finally:
            conn.close()

    def process_command(self, cmd):
        parts = cmd.split(":", 1)
        verb = parts[0].upper()

        if verb == "DOCK":
            if len(parts) < 2:
                return "ERROR: missing SMILES"
            if self.docking_in_progress:
                return "ERROR: docking already in progress"
            threading.Thread(target=self._run_docking, args=(parts[1],), daemon=True).start()
            return "DOCKING_STARTED"

        if verb == "SCORE":
            return json.dumps({"best_affinity": self.sensors["Best Affinity"]})

        if verb == "STATUS":
            with self.lock:
                data = {"motors": dict(self.motors), "sensors": dict(self.sensors)}
            return json.dumps(data)

        if verb == "RESET":
            self._reset()
            return "RESET_OK"

        return "ERROR: unknown command"

    def _run_docking(self, smiles):
        self.docking_in_progress = True
        self.smiles_counter += 1
        lig_id = f"L{self.smiles_counter}"
        self.log(f"--- Docking #{self.smiles_counter} | SMILES: {smiles} ---")

        for name in MOTOR_NAMES:
            self.set_motor_state(name, "IDLE")

        for name in MOTOR_NAMES:
            self.set_motor_state(name, "RUNNING")
            dur = random.uniform(1.0, 4.0)
            self.log(f"  {name} ... {dur:.2f}s")
            time.sleep(dur)
            if random.random() < 0.04:
                self.set_motor_state(name, "FAILED")
                self.log(f"  {name} FAILED")
                self.docking_in_progress = False
                self.log("--- Docking ABORTED ---")
                return
            self.set_motor_state(name, "COMPLETED")

        affinity = max(-15.0, min(0.0, -8 + random.gauss(0, 2) - len(smiles) * 0.1))
        self.affinity_records.append((lig_id, affinity))

        best = min(v for _, v in self.affinity_records)
        avg = sum(v for _, v in self.affinity_records) / len(self.affinity_records)
        rmsd = random.uniform(0.2, 4.8)
        hb = random.randint(1, 10)

        self.set_sensor_value("Best Affinity", best)
        self.set_sensor_value("Avg Affinity", avg)
        self.set_sensor_value("RMSD", rmsd)
        self.set_sensor_value("H-Bonds", hb)

        self.root.after(100, self._draw_chart)
        self.log(f"  Result: {lig_id}  affinity={affinity:.2f} kcal/mol  RMSD={rmsd:.2f}  H-bonds={hb}")
        self.log("--- Docking complete ---")
        self.docking_in_progress = False

    def _reset(self):
        for name in MOTOR_NAMES:
            self.set_motor_state(name, "IDLE")
        for name in SENSOR_NAMES:
            self.set_sensor_value(name, 0.0)
        self.affinity_records.clear()
        self.smiles_counter = 0
        self.root.after(100, self._draw_chart)
        self.log("System reset")

    def _on_close(self):
        self._running = False
        if hasattr(self, "server"):
            try:
                self.server.close()
            except OSError:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Molecular Docking Agent")
    parser.add_argument("--port", type=int, default=50062, help="TCP listen port")
    args = parser.parse_args()

    agent = DockingAgent(port=args.port)
    agent.run()
