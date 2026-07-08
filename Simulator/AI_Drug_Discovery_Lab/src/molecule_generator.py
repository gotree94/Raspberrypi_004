import tkinter as tk
from tkinter import ttk
import threading
import socket
import json
import time
import random
import sys
import argparse

PREDEFINED_MOLECULES = [
    ("CCO", "Ethanol", 0.85, 1.2, -0.14, 46.07, 1, 1),
    ("CC(=O)O", "Acetic acid", 0.67, 1.8, -0.17, 60.05, 1, 2),
    ("c1ccccc1", "Benzene", 0.70, 2.5, 2.13, 78.11, 0, 0),
    ("c1ccccc1O", "Phenol", 0.75, 2.8, 1.55, 94.11, 1, 0),
    ("CC(C)Cc1ccc(cc1)[N+]([O-])=O", "Ibuprofen fragment", 0.82, 3.2, 2.81, 179.22, 0, 2),
    ("CC(C(=O)O)c1ccc(cc1)Cl", "Chloro-ibuprofen", 0.78, 3.5, 2.90, 194.61, 1, 2),
    ("CN1CCN(CC1)C2=C(C=C(C=C2)Cl)Cl", "Antipsychotic scaffold", 0.72, 4.1, 3.10, 268.18, 0, 2),
    ("c1cc2cc(cc2cc1)C(=O)O", "Naphthoic acid", 0.74, 3.8, 2.45, 172.18, 1, 2),
    ("CC1=CC(=O)C=C1", "Vitamin K3 fragment", 0.69, 3.0, 1.87, 122.12, 0, 1),
    ("COc1ccc(cc1)CCN", "Dopamine analog", 0.81, 2.9, 1.12, 151.21, 2, 1),
    ("Cc1cc(C)cc(N)c1", "Xylidine", 0.65, 2.4, 1.95, 121.18, 2, 0),
    ("O=C(O)C1CCCN1C(=O)c2ccc(cc2)Cl", "Proline derivative", 0.79, 3.6, 1.45, 253.68, 1, 3),
    ("CC1CN(C(=O)C1)c2ccc(cc2)F", "Fluorophenyl lactam", 0.76, 3.3, 2.10, 193.22, 0, 2),
    ("COc1ccc(cc1OC)C(=O)O", "Veratric acid", 0.80, 2.7, 1.38, 182.17, 1, 2),
    ("CC(C)(C)c1ccc(cc1)O", "BHT fragment", 0.73, 2.1, 2.95, 150.22, 1, 0),
]

MOTOR_NAMES = ["VAE Encoding", "Latent Sampling", "Decoding", "Property Filter", "RL Optimization"]
MOTOR_TIMES = [(1.0, 2.0), (0.8, 1.8), (1.2, 2.5), (1.5, 3.5), (1.8, 4.0)]


class MoleculeGenerator:
    def __init__(self, root, port):
        self.root = root
        self.port = port
        self.root.title(f"AI Molecule Generator Agent (Port {port})")
        self.root.geometry("1050x700")
        self.root.resizable(True, True)

        self.motor_states = ["IDLE"] * 5
        self.sensors = {"QED": 0.0, "SA": 10.0, "LogP": 0.0, "MW": 0.0, "HBD": 0, "HBA": 0}
        self.current_smiles = ""
        self.current_name = ""
        self.log_lines = []
        self.running = False
        self.lock = threading.Lock()

        self._build_gui()
        self._draw_molecule()
        self.log("Agent initialized on port %d" % port)

    def _build_gui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left_frame = ttk.LabelFrame(top_frame, text="Motor Controls", width=220)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_frame.pack_propagate(False)

        self.motor_labels = []
        self.motor_canvases = []
        for name in MOTOR_NAMES:
            row = ttk.Frame(left_frame)
            row.pack(fill=tk.X, padx=5, pady=3)
            can = tk.Canvas(row, width=20, height=20, highlightthickness=0)
            can.pack(side=tk.LEFT, padx=(0, 5))
            circle = can.create_oval(3, 3, 17, 17, fill="gray", outline="black")
            lab = ttk.Label(row, text=name, width=22, anchor=tk.W)
            lab.pack(side=tk.LEFT)
            self.motor_labels.append(lab)
            self.motor_canvases.append((can, circle))

        center_frame = ttk.LabelFrame(top_frame, text="Molecular Graph")
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(center_frame, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        right_frame = ttk.LabelFrame(top_frame, text="Sensors", width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        right_frame.pack_propagate(False)

        self.sensor_bars = {}
        sensor_config = [
            ("QED", 0.0, 1.0, "#4CAF50"),
            ("SA Score", 1.0, 10.0, "#FF9800"),
            ("LogP", -2.0, 10.0, "#2196F3"),
            ("MW", 100.0, 1000.0, "#9C27B0"),
            ("HBD", 0.0, 15.0, "#E91E63"),
            ("HBA", 0.0, 15.0, "#00BCD4"),
        ]
        for key, lo, hi, color in sensor_config:
            row = ttk.Frame(right_frame)
            row.pack(fill=tk.X, padx=5, pady=3)
            lab = ttk.Label(row, text=key, width=10, anchor=tk.W)
            lab.pack(side=tk.LEFT)
            can = tk.Canvas(row, width=80, height=16, highlightthickness=0, bg="white")
            can.pack(side=tk.LEFT, padx=(2, 2))
            can.create_rectangle(0, 0, 80, 16, outline="black", fill="#e0e0e0")
            bar = can.create_rectangle(2, 2, 2, 14, fill=color, outline="")
            val = ttk.Label(row, text="--", width=8, anchor=tk.E)
            val.pack(side=tk.LEFT)
            self.sensor_bars[key] = {"canvas": can, "bar": bar, "label": val, "lo": lo, "hi": hi}

        bottom_frame = ttk.LabelFrame(self.root, text="Command Log", height=120)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        bottom_frame.pack_propagate(False)

        self.log_text = tk.Text(bottom_frame, height=6, state=tk.DISABLED, wrap=tk.WORD)
        scroll = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _draw_molecule(self, smiles=None):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50:
            w = 400
        if h < 50:
            h = 300

        cx, cy = w // 2, h // 2
        if smiles:
            n_atoms = len(smiles.translate(str.maketrans("", "", "cCnNnN1234567890:=#()[],.\\/")).replace("[", "").replace("]", ""))
            n_atoms = max(n_atoms, 3)
        else:
            n_atoms = 6
        n_atoms = min(n_atoms, 12)

        radius = min(w, h) // 3
        angles = [2 * 3.14159 * i / n_atoms for i in range(n_atoms)]
        pts = [(cx + radius * 0.7 + radius * 0.3 * (1 if n_atoms > 4 else 0),
                cy + radius * 0.3)]
        if n_atoms > 1:
            pts = [(cx + radius * 0.7 * a, cy + radius * 0.3 * b)
                   for a, b in [(1, 0.5), (0.6, -0.8), (-0.3, -1.0),
                                (-0.9, -0.3), (-0.9, 0.6), (-0.3, 1.0),
                                (0.6, 1.2), (1.1, 0.3), (1.0, -0.6),
                                (0.0, -1.3), (-1.1, -0.6), (-1.1, 0.7)]]
        colors = ["#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
                  "#4DB6AC", "#FFF176", "#A1887F", "#90A4AE", "#F06292",
                  "#AED581", "#FF8A65"]
        elems = ["C", "N", "O", "C", "C", "N", "O", "C", "C", "N", "O", "C"]

        for i in range(min(n_atoms, len(pts))):
            x, y = pts[i]
            r2 = 16
            self.canvas.create_oval(x - r2, y - r2, x + r2, y + r2,
                                    fill=colors[i % len(colors)], outline="black", width=2)
            self.canvas.create_text(x, y, text=elems[i % len(elems)], font=("Arial", 10, "bold"))
            for j in range(i + 1, min(n_atoms, len(pts))):
                if abs(i - j) <= 2 or (i < 2 and j == n_atoms - 1) or (i == 0 and j == n_atoms - 2):
                    x2, y2 = pts[j]
                    self.canvas.create_line(x, y, x2, y2, width=2, fill="#555")

        info = ""
        if self.current_name:
            info = self.current_name
        if self.current_smiles:
            info += (" | " if info else "") + self.current_smiles
        if info:
            self.canvas.create_text(cx, h - 20, text=info, font=("Arial", 9), fill="#333")

    def set_motor(self, idx, state):
        color_map = {"IDLE": "gray", "RUNNING": "green", "COMPLETED": "blue", "FAILED": "red"}
        with self.lock:
            self.motor_states[idx] = state
            can, circle = self.motor_canvases[idx]
            can.itemconfig(circle, fill=color_map.get(state, "gray"))
        self.root.update_idletasks()

    def set_sensor(self, key, value):
        info = self.sensor_bars.get(key)
        if not info:
            return
        lo, hi = info["lo"], info["hi"]
        frac = max(0.0, min(1.0, (value - lo) / (hi - lo)))
        x = 2 + frac * 76
        info["canvas"].coords(info["bar"], 2, 2, x, 14)
        txt = "%.2f" % value if isinstance(value, float) else str(value)
        info["label"].configure(text=txt)

    def update_sensors_from_mol(self, mol):
        smiles, name, qed, sa, logp, mw, hbd, hba = mol
        self.current_smiles = smiles
        self.current_name = name
        with self.lock:
            self.sensors["QED"] = qed
            self.sensors["SA"] = sa
            self.sensors["LogP"] = logp
            self.sensors["MW"] = mw
            self.sensors["HBD"] = hbd
            self.sensors["HBA"] = hba
        for key, val in [("QED", qed), ("SA Score", sa), ("LogP", logp),
                         ("MW", mw), ("HBD", hbd), ("HBA", hba)]:
            self.set_sensor(key, val)
        self.root.after(0, lambda: self._draw_molecule(smiles))

    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        line = "[%s] %s" % (ts, msg)
        self.log_lines.append(line)
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def run_motors(self, mol_idx=None):
        if self.running:
            return
        self.running = True
        for i in range(5):
            self.set_motor(i, "IDLE")

        def runner():
            try:
                for i, (name, times) in enumerate(zip(MOTOR_NAMES, MOTOR_TIMES)):
                    self.root.after(0, lambda idx=i: self.set_motor(idx, "RUNNING"))
                    self.root.after(0, lambda idx=i: self.log("%s started..." % MOTOR_NAMES[idx]))
                    dur = random.uniform(*times)
                    steps = max(1, int(dur / 0.1))
                    for s in range(steps):
                        time.sleep(0.1)
                        frac = (s + 1) / steps
                        if i == 0:
                            self.set_sensor("QED", frac * 0.8)
                        elif i == 1:
                            self.set_sensor("SA Score", 10 - frac * 3)
                        elif i == 2:
                            self.set_sensor("LogP", -2 + frac * 4)
                        elif i == 3:
                            self.set_sensor("MW", 100 + frac * 300)
                        elif i == 4:
                            self.set_sensor("HBD", frac * 3)
                            self.set_sensor("HBA", frac * 2)
                    self.root.after(0, lambda idx=i: self.set_motor(idx, "COMPLETED"))
                    self.root.after(0, lambda idx=i: self.log("%s completed." % MOTOR_NAMES[idx]))

                if mol_idx is not None:
                    mol = PREDEFINED_MOLECULES[mol_idx]
                else:
                    mol = random.choice(PREDEFINED_MOLECULES)
                self.root.after(0, lambda m=mol: self.update_sensors_from_mol(m))
                self.root.after(0, lambda: self.log("Molecule generated: %s (%s)" % (mol[1], mol[0])))
            finally:
                self.running = False

        threading.Thread(target=runner, daemon=True).start()

    def handle_command(self, cmd):
        cmd = cmd.strip()
        if cmd.startswith("GENERATE:"):
            prop = cmd[9:].strip()
            self.log("Received GENERATE command (property: %s)" % prop)
            idx = random.randrange(len(PREDEFINED_MOLECULES))
            mol = PREDEFINED_MOLECULES[idx]
            self.root.after(0, lambda: self.run_motors(idx))
            return json.dumps({"status": "ok", "smiles": mol[0], "name": mol[1],
                               "properties": {"QED": mol[2], "SA": mol[3],
                                              "LogP": mol[4], "MW": mol[5],
                                              "HBD": mol[6], "HBA": mol[7]}})
        elif cmd.startswith("OPTIMIZE:"):
            inp = cmd[9:].strip()
            self.log("Received OPTIMIZE command for: %s" % inp)
            target_set = [m for m in PREDEFINED_MOLECULES if m[0] != inp] or PREDEFINED_MOLECULES
            mol = random.choice(target_set)
            improved = list(mol)
            improved = (improved[0], improved[1], min(1.0, improved[2] + random.uniform(0.05, 0.2)),
                        improved[3], improved[4], improved[5], improved[6], improved[7])
            self.root.after(0, lambda: self.run_motors(None))
            self.root.after(0, lambda: self.update_sensors_from_mol(improved))
            return json.dumps({"status": "ok", "smiles": improved[0], "name": improved[1],
                               "properties": {"QED": improved[2], "SA": improved[3],
                                              "LogP": improved[4], "MW": improved[5],
                                              "HBD": improved[6], "HBA": improved[7]}})
        elif cmd == "STATUS":
            with self.lock:
                motors = list(self.motor_states)
                sens = dict(self.sensors)
            return json.dumps({"status": "ok", "motors": motors, "sensors": sens,
                               "current_smiles": self.current_smiles,
                               "current_name": self.current_name, "running": self.running})
        elif cmd == "RESET":
            self.log("Received RESET command")
            self.running = False
            for i in range(5):
                self.set_motor(i, "IDLE")
            self.update_sensors_from_mol(PREDEFINED_MOLECULES[0])
            return json.dumps({"status": "ok", "message": "Reset complete"})
        else:
            return json.dumps({"status": "error", "message": "Unknown command"})


class TCPServer:
    def __init__(self, agent, port):
        self.agent = agent
        self.port = port
        self.server = None

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", self.port))
        self.server.listen(5)
        self.server.settimeout(1.0)
        self.agent.log("TCP server listening on port %d" % self.port)

        while True:
            try:
                conn, addr = self.server.accept()
                self.agent.log("Connection from %s:%d" % addr)
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def handle_client(self, conn, addr):
        try:
            data = conn.recv(4096).decode("utf-8").strip()
            if data:
                self.agent.log("TCP recv: %s" % data[:80])
                resp = self.agent.handle_command(data)
                conn.sendall((resp + "\n").encode("utf-8"))
            else:
                conn.sendall(json.dumps({"status": "error", "message": "Empty command"}).encode("utf-8") + b"\n")
        except Exception as e:
            try:
                conn.sendall(json.dumps({"status": "error", "message": str(e)}).encode("utf-8") + b"\n")
            except Exception:
                pass
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="AI Molecule Generator Agent")
    parser.add_argument("--port", type=int, default=50064, help="TCP port (default: 50064)")
    args = parser.parse_args()

    root = tk.Tk()
    agent = MoleculeGenerator(root, args.port)

    server = TCPServer(agent, args.port)
    t = threading.Thread(target=server.start, daemon=True)
    t.start()

    root.mainloop()


if __name__ == "__main__":
    main()
