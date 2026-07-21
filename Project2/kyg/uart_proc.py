import serial
import time
import socket
import select

def uart_worker(port, baudrate, rx_queue, tx_queue):
    print(f"[UART/TCP] Process Started on {port} at {baudrate} baud.")
    
    is_tcp = port.startswith("TCP:")
    conn = None
    
    def connect_tcp():
        host, p = port[4:].split(":")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((host, int(p)))
        s.setblocking(False)
        return s
        
    def read_line_tcp(s):
        buffer = b""
        while True:
            ready = select.select([s], [], [], 0.05)
            if ready[0]:
                data = s.recv(1)
                if not data: return "" # Disconnected
                buffer += data
                if buffer.endswith(b'\n'):
                    return buffer.decode('utf-8', errors='ignore').strip()
            else:
                return buffer.decode('utf-8', errors='ignore').strip() if buffer else ""

    while True:
        try:
            if conn is None or (not is_tcp and not conn.is_open):
                try:
                    if is_tcp:
                        conn = connect_tcp()
                        print("[TCP] Connected to Simulator.")
                    else:
                        conn = serial.Serial(port, baudrate, timeout=0.1)
                        print("[UART] Connected to STM32.")
                except Exception as e:
                    print(f"[{'TCP' if is_tcp else 'UART'}] Waiting for connection on {port}... ({e})")
                    time.sleep(2)
                    continue

            # 1. TX 전송
            while not tx_queue.empty():
                cmd = tx_queue.get_nowait()
                if isinstance(cmd, str):
                    if is_tcp: conn.sendall(cmd.encode('utf-8'))
                    else: conn.write(cmd.encode('utf-8'))

            # 2. RX 수신
            line = ""
            if is_tcp:
                line = read_line_tcp(conn)
            else:
                if conn.in_waiting > 0:
                    line = conn.readline().decode('utf-8', errors='ignore').strip()
                    
            if line:
                    # 예상 포맷: S:50.0,999.0,999.0|Y:15.3|E:120.5,120.5|C:0
                    if line.startswith("S:"):
                        try:
                            parts = line.split('|')
                            s_parts = parts[0][2:].split(',')
                            y_part = parts[1][2:]
                            e_parts = parts[2][2:].split(',')
                            c_part = parts[3][2:]
                            
                            telemetry = {
                                'sonar_f': float(s_parts[0]),
                                'sonar_l': float(s_parts[1]),
                                'sonar_r': float(s_parts[2]),
                                'yaw': float(y_part),
                                'enc_l': float(e_parts[0]),
                                'enc_r': float(e_parts[1]),
                                'crash': int(c_part)
                            }
                            
                            # 최신 데이터만 유지
                            if rx_queue.full():
                                try: rx_queue.get_nowait()
                                except: pass
                            rx_queue.put(telemetry)
                        except Exception as e:
                            pass # 파싱 에러 무시 (쓰레기값)
                            
        except Exception as e:
            print(f"[{'TCP' if is_tcp else 'UART'}] Disconnected or Error: {e}")
            if conn:
                conn.close()
                conn = None
            time.sleep(1)
