import tkinter as tk, socket, threading, json, sys, time, random, math

MOTORS = [
    "MSA Build", "Template Search",
    "Model Inference 1", "Model Inference 2", "Model Inference 3",
    "Model Inference 4", "Model Inference 5",
    "Relaxation", "Confidence Scoring"
]
COLORS = {"IDLE": "#808080", "RUNNING": "#00CC00", "COMPLETED": "#0066CC", "FAILED": "#CC0000"}

class AlphaFoldAgent:
    def __init__(self, port=50061):
        self.port = port
        self.root = tk.Tk()
        self.root.title(f"AlphaFold Protein Structure Prediction Agent (Port {port})")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.motor_states = {m: "IDLE" for m in MOTORS}
        self.sensors = {"pLDDT": 0.0, "PAE": 30.0, "Coverage": 0.0, "Seq Length": 0}
        self.sequence = ""
        self.running = False
        self.stop_event = threading.Event()
        self.build_gui()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.server.listen(5)
        self.server.settimeout(1.0)

    def build_gui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        left = tk.LabelFrame(top, text="Computational Motors", padx=5, pady=5)
        left.pack(side=tk.LEFT, fill=tk.Y)
        self.motor_widgets = {}
        for m in MOTORS:
            f = tk.Frame(left)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=m, width=16, anchor=tk.W).pack(side=tk.LEFT)
            ind = tk.Label(f, text="\u25cf", fg=COLORS["IDLE"], font=("Segoe UI", 12))
            ind.pack(side=tk.LEFT, padx=3)
            lbl = tk.Label(f, text="IDLE", width=10)
            lbl.pack(side=tk.LEFT)
            self.motor_widgets[m] = (ind, lbl)
        center = tk.LabelFrame(top, text="Predicted Structure", padx=5, pady=5)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(center, width=420, height=420, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_structure(0)
        right = tk.LabelFrame(top, text="AI Sensors", padx=5, pady=5)
        right.pack(side=tk.LEFT, fill=tk.Y)
        self.sensor_vars = {}
        for name in ["pLDDT", "PAE", "Coverage", "Seq Length"]:
            f = tk.Frame(right)
            f.pack(fill=tk.X, pady=3)
            tk.Label(f, text=name, width=10, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.StringVar(value="0.0")
            self.sensor_vars[name] = var
            tk.Label(f, textvariable=var, width=10, anchor=tk.E).pack(side=tk.LEFT)
        bottom = tk.Frame(self.root)
        bottom.pack(fill=tk.BOTH, padx=5, pady=5)
        tk.Label(bottom, text="Command Log:").pack(anchor=tk.W)
        self.log_text = tk.Text(bottom, height=8, state=tk.DISABLED)
        sb = tk.Scrollbar(bottom, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def draw_structure(self, plddt):
        self.canvas.delete("all")
        w, h = 420, 420
        cx, cy = w // 2, h // 2
        n = max(5, min(40, max(5, self.sensors["Seq Length"]) // 8 + 5))
        conf_colors = ["#FF4444", "#FF8844", "#FFCC44", "#88DD44", "#44FF44"]
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            r = 120 + 60 * math.sin(i * 0.7 + a)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            self.canvas.create_line(x1, y1, x2, y2, fill="#999", width=2)
        for i, (x, y) in enumerate(pts):
            ci = min(4, int(plddt / 20)) if plddt > 0 else 0
            r = 7
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=conf_colors[ci], outline="#333", width=1)

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def set_motor(self, motor, state):
        self.motor_states[motor] = state
        ind, lbl = self.motor_widgets[motor]
        ind.config(fg=COLORS[state])
        lbl.config(text=state)

    def set_sensor(self, name, value):
        self.sensors[name] = value
        fmt = {"pLDDT": "{:.1f}", "PAE": "{:.1f}", "Coverage": "{:.1f}%", "Seq Length": "{}"}
        self.sensor_vars[name].set(fmt[name].format(value))

    def predict(self, sequence):
        self.sequence = sequence
        self.running = True
        threading.Thread(target=self._run_pipeline, args=(sequence,), daemon=True).start()

    def _run_pipeline(self, seq):
        try:
            seq_len = len(seq)
            self.root.after(0, self.set_sensor, "Seq Length", seq_len)
            self.root.after(0, self.log, f"Prediction started: {seq_len} residues")

            self.root.after(0, self.set_motor, "MSA Build", "RUNNING")
            self.root.after(0, self.log, "  MSA Building...")
            time.sleep(random.uniform(2, 5))
            self.root.after(0, self.set_motor, "MSA Build", "COMPLETED")
            self.root.after(0, self.set_sensor, "Coverage", min(100, 50 + random.uniform(0, 40)))
            if self.stop_event.is_set(): return

            self.root.after(0, self.set_motor, "Template Search", "RUNNING")
            self.root.after(0, self.log, "  Template Searching...")
            time.sleep(random.uniform(2, 5))
            self.root.after(0, self.set_motor, "Template Search", "COMPLETED")
            if self.stop_event.is_set(): return

            plddt_sum = 0
            for i in range(1, 6):
                mn = f"Model Inference {i}"
                self.root.after(0, self.set_motor, mn, "RUNNING")
                self.root.after(0, self.log, f"  {mn}...")
                time.sleep(random.uniform(2, 5))
                noise = random.uniform(-3, 3)
                p = max(0, min(100, 95 - seq_len / 100 + noise))
                plddt_sum += p
                pa = max(0, min(30, 15 + random.uniform(-5, 5) - seq_len / 200))
                self.root.after(0, self.set_sensor, "pLDDT", p)
                self.root.after(0, self.set_sensor, "PAE", pa)
                self.root.after(0, self.set_motor, mn, "COMPLETED")
                self.root.after(0, self.log, f"    pLDDT={p:.1f}, PAE={pa:.1f}")
                self.root.after(0, self.draw_structure, p)
                if self.stop_event.is_set(): return

            self.root.after(0, self.set_motor, "Relaxation", "RUNNING")
            self.root.after(0, self.log, "  Relaxation...")
            time.sleep(random.uniform(2, 4))
            self.root.after(0, self.set_motor, "Relaxation", "COMPLETED")
            if self.stop_event.is_set(): return

            self.root.after(0, self.set_motor, "Confidence Scoring", "RUNNING")
            self.root.after(0, self.log, "  Confidence Scoring...")
            time.sleep(random.uniform(2, 3))
            final_plddt = max(0, min(100, plddt_sum / 5 + random.uniform(-1, 1)))
            self.root.after(0, self.set_sensor, "pLDDT", final_plddt)
            self.root.after(0, self.set_motor, "Confidence Scoring", "COMPLETED")
            self.root.after(0, self.draw_structure, final_plddt)
            self.root.after(0, self.log, f"  Complete! Final pLDDT: {final_plddt:.1f}")
        except Exception as e:
            self.root.after(0, self.log, f"ERROR: {e}")
            for m in MOTORS:
                if self.motor_states[m] == "RUNNING":
                    self.root.after(0, self.set_motor, m, "FAILED")
        finally:
            self.running = False

    def reset(self):
        if self.running:
            self.stop_event.set()
            time.sleep(0.5)
            self.stop_event.clear()
        for m in MOTORS:
            self.set_motor(m, "IDLE")
        self.set_sensor("pLDDT", 0)
        self.set_sensor("PAE", 30)
        self.set_sensor("Coverage", 0)
        self.set_sensor("Seq Length", 0)
        self.draw_structure(0)
        self.log("Reset complete.")

    def handle_client(self, conn):
        try:
            data = conn.recv(4096).decode().strip()
            if not data:
                return
            self.root.after(0, self.log, f"TCP << {data[:80]}")
            if data.startswith("PREDICT:"):
                seq = data[8:]
                if self.running:
                    conn.send(b"BUSY: Prediction in progress\n")
                elif len(seq) < 10 or len(seq) > 1000:
                    conn.send(b"ERROR: Sequence must be 10-1000 chars\n")
                else:
                    conn.send(b"OK: Prediction started\n")
                    self.root.after(0, self.predict, seq)
            elif data == "STATUS":
                s = {"motors": dict(self.motor_states), "sensors": dict(self.sensors), "running": self.running}
                conn.send((json.dumps(s) + "\n").encode())
            elif data == "CONFIDENCE":
                conn.send((f"{self.sensors['pLDDT']:.1f}\n").encode())
            elif data == "RESET":
                self.root.after(0, self.reset)
                conn.send(b"OK: Reset\n")
            else:
                conn.send(b"ERROR: Unknown command\n")
        except Exception as e:
            try:
                conn.send(f"ERROR: {e}\n".encode())
            except Exception:
                pass
        finally:
            conn.close()

    def server_loop(self):
        while not self.stop_event.is_set():
            try:
                conn, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break
        self.server.close()

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()

    def run(self):
        threading.Thread(target=self.server_loop, daemon=True).start()
        self.log(f"Agent ready on port {self.port}")
        self.root.mainloop()

if __name__ == "__main__":
    port = 50061
    if "--port" in sys.argv:
        i = sys.argv.index("--port")
        if i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    AlphaFoldAgent(port).run()
