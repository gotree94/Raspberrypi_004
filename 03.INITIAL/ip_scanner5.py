#!/usr/bin/env python3
"""
IP Scanner v5 — DNS/ARP 캐시 플러시 + MAC 변경 감지 + 장치 DB
"""

import subprocess
import socket
import threading
import ipaddress
import sys
import os
import time
import argparse
import json
import re
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ── 색상 상수 ──────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"
    BG_DARK = "\033[40m"

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ip_scanner_db.json")

# ── 유틸리티 ───────────────────────────────────────────────
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def is_admin():
    if os.name != "nt":
        return os.geteuid() == 0
    try:
        return subprocess.check_output(
            ["net", "session"], stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
        ) is not None
    except Exception:
        return False

def ping(ip, timeout=1):
    param = "-n" if os.name == "nt" else "-c"
    w_param = ["-w", str(timeout * 1000)] if os.name == "nt" else ["-W", str(timeout)]
    cmd = ["ping", param, "1"] + w_param + [str(ip)]
    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 1)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

# ── DNS / ARP 캐시 플러시 ─────────────────────────────────
def flush_caches():
    print(f"  {C.YELLOW}DNS / ARP 캐시 플러시 중...{C.RESET}")
    if os.name == "nt":
        cmds = [
            ("ipconfig /flushdns", "DNS 캐시"),
            ("arp -d *", "ARP 캐시"),
        ]
        for cmd, label in cmds:
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                print(f"  {C.GREEN}  ✔ {label} 삭제 완료{C.RESET}")
            except Exception as e:
                print(f"  {C.RED}  ✘ {label} 실패: {e}{C.RESET}")
        # netsh로 한 번 더
        try:
            subprocess.run(["netsh", "interface", "ip", "delete", "arpcache"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass
    else:
        try:
            subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass
        try:
            subprocess.run(["sudo", "ip", "neigh", "flush", "all"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass

# ── ARP 스캔 (nmap 이용) ─────────────────────────────────
def arp_scan_nmap(network, timeout=30):
    """nmap ARP 스캔으로 활성 장치 목록 획득 (가장 빠름)"""
    try:
        subprocess.run(["nmap", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    except Exception:
        return None
    print(f"  {C.GRAY}nmap ARP 스캔 실행 중...{C.RESET}")
    try:
        out = subprocess.check_output(
            ["nmap", "-sn", "-PR", "-n", network],
            timeout=timeout, stderr=subprocess.DEVNULL
        ).decode(errors="ignore")
    except Exception:
        return None
    hosts = []
    for line in out.split("\n"):
        m = re.search(r"Nmap scan report for ([\d\.]+)", line)
        if m:
            hosts.append(m.group(1))
    return hosts if hosts else None

# ── ARP 테이블에서 직접 수집 ──────────────────────────────
def get_arp_table():
    """로컬 ARP 테이블에서 IP-MAC 매핑 수집"""
    entries = {}
    try:
        if os.name == "nt":
            out = subprocess.check_output(["arp", "-a"], stderr=subprocess.DEVNULL, timeout=3).decode(errors="ignore")
            for line in out.split("\n"):
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0].count(".") == 3:
                    ip = parts[0]
                    mac = parts[1].replace("-", ":").upper()
                    if mac.count(":") == 5 and mac != "FF:FF:FF:FF:FF:FF":
                        entries[ip] = mac
        else:
            out = subprocess.check_output(["arp", "-n"], stderr=subprocess.DEVNULL, timeout=3).decode(errors="ignore")
            for line in out.split("\n"):
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0].count(".") == 3:
                    ip = parts[0]
                    mac = parts[2].upper()
                    if mac.count(":") == 5 and mac != "FF:FF:FF:FF:FF:FF":
                        entries[ip] = mac
    except Exception:
        pass
    return entries

# ── mDNS ────────────────────────────────────────────────────
def _mdns_direct_query(mdns_map, timeout=2.0):
    MDNS_ADDR, MDNS_PORT = "224.0.0.251", 5353
    def build_query(name):
        header = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
        qname = b""
        for part in name.rstrip(".").split("."):
            e = part.encode()
            qname += bytes([len(e)]) + e
        qname += b"\x00"
        return header + qname + struct.pack(">HH", 12, 1)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sock.settimeout(timeout)
        sock.sendto(build_query("_services._dns-sd._udp.local"), (MDNS_ADDR, MDNS_PORT))
        end = time.time() + timeout
        while time.time() < end:
            try:
                data, addr = sock.recvfrom(4096)
                src_ip = addr[0]
                names = re.findall(rb"[\w\-]+\.local", data)
                for n in names:
                    name = n.decode(errors="ignore")
                    if name.endswith(".local") and src_ip not in mdns_map:
                        mdns_map[src_ip] = name
                        break
            except socket.timeout:
                break
        sock.close()
    except Exception:
        pass

def _resolve_local_via_powershell(hostname, timeout=3):
    """PowerShell Resolve-DnsName으로 .local 이름의 IPv4 조회"""
    try:
        ps = (f"Resolve-DnsName -Name {hostname} -Type A -ErrorAction SilentlyContinue | "
              "Where-Object {{ $_.IPAddress -match '^[0-9]' }} | "
              "Select-Object -First 1 -ExpandProperty IPAddress")
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            stderr=subprocess.DEVNULL, timeout=timeout
        ).decode(errors="ignore").strip()
        if out and out[0].isdigit():
            return out
    except Exception:
        pass
    return None

def _discover_local_via_ping_sweep(network):
    """ping sweep 후 역방향 mDNS 조회로 .local 이름 찾기"""
    found = {}
    net = ipaddress.IPv4Network(network, strict=False)
    hosts = list(net.hosts())
    # 빠른 ping
    alive = []
    with ThreadPoolExecutor(max_workers=128) as ex:
        fut_map = {ex.submit(ping, ip): ip for ip in hosts}
        for f in as_completed(fut_map):
            if f.result():
                alive.append(fut_map[f])
    # 각 alive IP에 대해 mDNS 역질의
    for ip in alive:
        try:
            ps = (f"Resolve-DnsName -Name {ip} -Type PTR -ErrorAction SilentlyContinue | "
                  "Select-Object -First 1 -ExpandProperty NameHost")
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps],
                stderr=subprocess.DEVNULL, timeout=2
            ).decode(errors="ignore").strip().rstrip(".")
            if out and out.endswith(".local"):
                found[str(ip)] = out
        except Exception:
            pass
    return found

def build_mdns_map(network=None):
    mdns_map = {}
    ipv4_entries = {}
    ipv6_names = []

    if os.name != "nt":
        try:
            out = subprocess.check_output(["avahi-browse", "-art", "--no-db-lookup"], stderr=subprocess.DEVNULL, timeout=4).decode(errors="ignore")
            for line in out.split("\n"):
                m = re.search(r"address = \[([\d\.]+)\]", line)
                n = re.search(r"hostname = \[([\w\-]+\.local)", line)
                if m and n:
                    mdns_map[m.group(1)] = n.group(1)
        except Exception:
            pass
        if not mdns_map:
            _mdns_direct_query(mdns_map)
        return mdns_map

    # Step 1: IPv4 직접 캐시
    try:
        ps_v4 = ("Get-DnsClientCache | Where-Object { $_.Entry -like '*.local' -and $_.Data -match '^[0-9]' } | "
                 "ForEach-Object { $_.Entry + ' ' + $_.Data }")
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_v4], stderr=subprocess.DEVNULL, timeout=5).decode(errors="ignore")
        for line in out.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) == 2:
                name, ip_addr = parts[0].strip(), parts[1].strip()
                if name.endswith(".local"):
                    ipv4_entries[name] = ip_addr
                    mdns_map[ip_addr] = name
    except Exception:
        pass

    # Step 2: IPv6만 캐시된 것은 강제 A 레코드 조회
    try:
        ps_v6 = ("Get-DnsClientCache | Where-Object { $_.Entry -like '*.local' } | Select-Object -ExpandProperty Entry -Unique")
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_v6], stderr=subprocess.DEVNULL, timeout=5).decode(errors="ignore")
        for line in out.strip().split("\n"):
            name = line.strip()
            if name.endswith(".local") and name not in ipv4_entries:
                ipv6_names.append(name)
    except Exception:
        pass

    for name in ipv6_names:
        ip = _resolve_local_via_powershell(name)
        if ip:
            mdns_map[ip] = name

    # Step 3: 캐시 없으면 네트워크 직접 탐색
    if not mdns_map:
        if network:
            found = _discover_local_via_ping_sweep(network)
            mdns_map.update(found)
        if not mdns_map:
            _mdns_direct_query(mdns_map)

    return mdns_map

# ── 호스트명 조회 ──────────────────────────────────────────
def get_hostname(ip, mdns_map):
    if ip in mdns_map:
        return mdns_map[ip]

    try:
        hostname = socket.gethostbyaddr(str(ip))[0]
        if hostname and not hostname.startswith(str(ip)):
            return hostname
    except (socket.herror, socket.gaierror, OSError):
        pass

    if os.name == "nt":
        ps_script = (
            "try { $r = Resolve-DnsName -Name " + ip + " -Type PTR -ErrorAction Stop; $r.NameHost } "
            "catch { $r = Resolve-DnsName -Name " + ip + " -ErrorAction SilentlyContinue; if ($r) { $r[0].NameHost } }"
        )
        try:
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_script], stderr=subprocess.DEVNULL, timeout=3).decode(errors="ignore").strip()
            if out and len(out) > 2 and "\n" not in out:
                return out.rstrip(".")
        except Exception:
            pass

        try:
            out = subprocess.check_output(["nbtstat", "-A", str(ip)], stderr=subprocess.DEVNULL, timeout=3).decode(errors="ignore")
            for line in out.split("\n"):
                if "<00>" in line and "GROUP" not in line.upper():
                    parts = line.strip().split()
                    if parts and len(parts[0]) > 1:
                        return parts[0].strip()
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(["avahi-resolve-address", str(ip)], stderr=subprocess.DEVNULL, timeout=3).decode().strip()
            if out:
                parts = out.split()
                if len(parts) >= 2:
                    return parts[1].rstrip(".")
        except Exception:
            pass
        try:
            out = subprocess.check_output(["nmblookup", "-A", str(ip)], stderr=subprocess.DEVNULL, timeout=3).decode()
            for line in out.split("\n"):
                if "<00>" in line and "GROUP" not in line:
                    name = line.strip().split()[0]
                    if name and name != "No":
                        return name
        except Exception:
            pass

    return ""

# ── MAC 조회 ───────────────────────────────────────────────
def get_mac_address(ip):
    try:
        if os.name == "nt":
            output = subprocess.check_output(["arp", "-a", str(ip)], stderr=subprocess.DEVNULL, timeout=2).decode()
            for line in output.split("\n"):
                if str(ip) in line:
                    parts = line.split()
                    for p in parts:
                        if "-" in p and len(p) == 17:
                            return p.replace("-", ":").upper()
        else:
            output = subprocess.check_output(["arp", "-n", str(ip)], stderr=subprocess.DEVNULL, timeout=2).decode()
            for line in output.split("\n"):
                if str(ip) in line:
                    parts = line.split()
                    for p in parts:
                        if ":" in p and len(p) == 17:
                            return p.upper()
    except Exception:
        pass
    return ""

def get_mac_bulk(ip_list):
    """ARP 테이블에서 한 번에 여러 IP의 MAC 조회"""
    table = get_arp_table()
    result = {}
    for ip in ip_list:
        if ip in table:
            result[ip] = table[ip]
        else:
            result[ip] = get_mac_address(ip)
    return result

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def guess_network(local_ip):
    parts = local_ip.rsplit(".", 1)
    return f"{parts[0]}.0/24"

def vendor_hint(mac):
    oui_db = {
        "B8:27:EB": "Raspberry Pi", "DC:A6:32": "Raspberry Pi",
        "E4:5F:01": "Raspberry Pi", "D8:3A:DD": "Raspberry Pi",
        "00:50:56": "VMware",       "00:0C:29": "VMware",
        "08:00:27": "VirtualBox",   "AC:DE:48": "Apple",
        "F0:18:98": "Apple",        "3C:22:FB": "Apple",
        "00:1A:A0": "Dell",         "F8:DB:88": "Samsung",
        "78:11:DC": "Samsung",      "00:1B:21": "Intel",
        "00:E0:4C": "Realtek",
    }
    prefix = mac[:8] if len(mac) >= 8 else ""
    return oui_db.get(prefix, "")

# ── 장치 DB (JSON) ─────────────────────────────────────────
def load_device_db():
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_device_db(db):
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def update_device_db(results):
    db = load_device_db()
    now = datetime.now().isoformat()
    for h in results:
        ip = h["ip"]
        mac = h["mac"] if h["mac"] and h["mac"] != "??:??:??:??:??:??" else None
        if ip not in db:
            db[ip] = {"first_seen": now}
        prev = db[ip]
        prev["last_seen"] = now
        prev["hostname"] = h["hostname"]
        if mac:
            prev_mac = prev.get("mac")
            if prev_mac and prev_mac != mac:
                prev.setdefault("mac_history", []).append({"mac": prev_mac, "hostname": prev.get("hostname", ""), "seen": prev.get("last_seen", "")})
                prev["mac_changed"] = True
            prev["mac"] = mac
    save_device_db(db)
    return db

def check_mac_changes(results, db):
    """DB와 비교해 각 IP의 MAC/호스트명 변경 여부 표시"""
    for h in results:
        ip = h["ip"]
        if ip in db:
            prev = db[ip]
            prev_mac = prev.get("mac", "")
            prev_hn = prev.get("hostname", "")
            curr_mac = h["mac"] if h["mac"] != "??:??:??:??:??:??" else ""
            changes = []
            if prev_mac and curr_mac and prev_mac != curr_mac:
                changes.append(f"MAC 변경: {prev_mac} → {curr_mac}")
            if prev_hn and h["hostname"] != "(알 수 없음)" and prev_hn != h["hostname"]:
                changes.append(f"호스트명 변경: {prev_hn} → {h['hostname']}")
            h["changes"] = changes
    return results

# ── 스캔 워커 ──────────────────────────────────────────────
def scan_host(ip, timeout, mdns_map):
    if not ping(ip, timeout):
        return None
    hostname = get_hostname(ip, mdns_map)
    mac = get_mac_address(ip)
    vendor = vendor_hint(mac) if mac else ""
    if not vendor and "raspberrypi" in hostname.lower():
        vendor = "Raspberry Pi"
    return {
        "ip": ip,
        "hostname": hostname or "(알 수 없음)",
        "mac": mac or "??:??:??:??:??:??",
        "vendor": vendor,
        "changes": [],
    }

# ── UI ──────────────────────────────────────────────────────
BANNER = f"""
{C.CYAN}{C.BOLD}
  ██╗██████╗     ███████╗ ██████╗ █████╗ ███╗   ██╗███╗   ██╗███████╗██████╗
  ██║██╔══██╗    ██╔════╝██╔════╝██╔══██╗████╗  ██║████╗  ██║██╔════╝██╔══██╗
  ██║██████╔╝    ███████╗██║     ███████║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
  ██║██╔═══╝     ╚════██║██║     ██╔══██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
  ██║██║         ███████║╚██████╗██║  ██║██║ ╚████║██║ ╚████║███████╗██║  ██║
  ╚═╝╚═╝         ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
{C.RESET}"""

def print_banner():
    print(BANNER)
    print(f"  {C.GRAY}네트워크 장치 탐색기 v5  ·  SD 교체 MAC 변경 감지{C.RESET}")
    print(f"  {C.GRAY}{'─' * 66}{C.RESET}\n")

def print_table_header():
    hdr = f"\n  {C.BOLD}{C.WHITE}{'NO':>3}  {'IP 주소':<17} {'호스트명':<32} {'MAC 주소':<20} {'제조사':<14} {'변경사항'}{C.RESET}"
    print(hdr)
    print(f"  {C.GRAY}{'─' * 110}{C.RESET}")

def print_row(idx, host, my_ip):
    tag = f" {C.GREEN}◀ 현재 기기{C.RESET}" if host["ip"] == my_ip else ""
    no_str   = f"{C.CYAN}{idx:>3}{C.RESET}"
    ip_str   = f"{C.YELLOW}{host['ip']:<17}{C.RESET}"
    hn_str   = f"{C.WHITE}{host['hostname']:<32}{C.RESET}"
    mac_str  = f"{C.GRAY}{host['mac']:<20}{C.RESET}"
    vnd_str  = f"{C.MAGENTA}{host['vendor']:<14}{C.RESET}"
    changes = host.get("changes", [])
    if changes:
        chg_str = f"{C.RED}⚠ {'; '.join(changes)}{C.RESET}"
    else:
        chg_str = ""
    print(f"  {no_str}  {ip_str} {hn_str} {mac_str} {vnd_str} {chg_str}{tag}")

def progress_bar(done, total, width=40):
    pct = done / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"{C.CYAN}[{bar}]{C.RESET} {C.WHITE}{done}/{total}{C.RESET} ({pct*100:.0f}%)"

# ── SSH 접속 도우미 ──────────────────────────────────────
def show_connect_menu(hosts):
    print(f"\n  {C.BOLD}{C.CYAN}{'─' * 60}")
    print(f"  ★  SSH 접속 명령어 생성")
    print(f"  {'─' * 60}{C.RESET}")
    print(f"\n  접속할 장치 번호를 입력하세요 (0=종료): ", end="")
    try:
        choice = int(input().strip())
    except (ValueError, EOFError):
        return
    if choice == 0:
        return
    if 1 <= choice <= len(hosts):
        h = hosts[choice - 1]
        print(f"\n  {C.GREEN}선택된 장치:{C.RESET} {h['ip']}  ({h['hostname']})")
        print(f"\n  {C.BOLD}── SSH 접속 예시 ─────────────────────────────{C.RESET}")
        print(f"  {C.YELLOW}ssh pi@{h['ip']}{C.RESET}              ← Raspberry Pi 기본")
        print(f"  {C.YELLOW}ssh ubuntu@{h['ip']}{C.RESET}          ← Ubuntu Server")
        print(f"  {C.YELLOW}ssh root@{h['ip']}{C.RESET}            ← root 접속")
        print(f"  {C.YELLOW}ssh -p 2222 user@{h['ip']}{C.RESET}    ← 포트 변경")
        print(f"\n  {C.BOLD}── SCP / RSYNC ───────────────────────────────{C.RESET}")
        print(f"  {C.YELLOW}scp file.txt pi@{h['ip']}:~/{C.RESET}")
        print(f"  {C.YELLOW}rsync -avz ./dir pi@{h['ip']}:~/dir{C.RESET}")
        if h["vendor"] == "Raspberry Pi":
            print(f"\n  {C.MAGENTA}💡 Raspberry Pi 감지 → 기본 계정: pi / raspberry{C.RESET}")

# ── .local 장치 별도 표시 ─────────────────────────────────
def show_local_devices(results):
    local_devices = [h for h in results if h["hostname"].endswith(".local")]
    if local_devices:
        print(f"\n  {C.BOLD}{C.CYAN}🔍 .local 장치 목록{C.RESET}")
        for h in local_devices:
            print(f"    {C.YELLOW}{h['ip']:<18}{C.RESET} → {C.GREEN}{h['hostname']}{C.RESET}  {C.GRAY}[{h['mac']}]{C.RESET}")
        print(f"  {C.GRAY}접속: {C.CYAN}ssh pi@{local_devices[0]['ip']}{C.RESET}")

# ── 실행 안내 출력 ─────────────────────────────────────────
def print_usage_tips(flush_used=False):
    if not flush_used:
        print(f"\n  {C.YELLOW}💡 캐시 문제가 있다면 --flush 옵션으로 재시도:{C.RESET}")
        print(f"     {C.CYAN}python ip_scanner5.py --flush{C.RESET}")
    print(f"  {C.YELLOW}💡 nmap 설치 시 ARP 스캔 사용 가능:{C.RESET}")
    print(f"     {C.CYAN}python ip_scanner5.py --arp-scan{C.RESET}")

# ── 메인 스캔 ──────────────────────────────────────────────
def run_scan(network, timeout, workers, verbose, do_flush, do_arp_scan):
    my_ip = get_local_ip()
    net = ipaddress.IPv4Network(network, strict=False)
    hosts_to_scan = list(net.hosts())
    total = len(hosts_to_scan)

    clear()
    print_banner()
    print(f"  {C.BOLD}대상 네트워크 :{C.RESET} {C.CYAN}{network}{C.RESET}")
    print(f"  {C.BOLD}내 IP 주소    :{C.RESET} {C.GREEN}{my_ip}{C.RESET}")
    print(f"  {C.BOLD}스캔 대상     :{C.RESET} {C.WHITE}{total}개 호스트{C.RESET}")
    print(f"  {C.BOLD}타임아웃      :{C.RESET} {timeout}s   스레드: {workers}")
    print(f"  {C.BOLD}시작 시각     :{C.RESET} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if do_flush:
        print(f"\n  {C.BOLD}{C.YELLOW}🧹 캐시 플러시 모드{C.RESET}")
        if not is_admin():
            print(f"  {C.RED}⚠ 관리자 권한이 필요합니다. 캐시 삭제가 실패할 수 있습니다.{C.RESET}")
        flush_caches()

    # ARP 스캔 시도
    arp_hosts = None
    if do_arp_scan:
        arp_hosts = arp_scan_nmap(network)
        if arp_hosts:
            print(f"  {C.GREEN}✔ nmap ARP 스캔 결과 {len(arp_hosts)}개 장치 발견{C.RESET}")
        else:
            print(f"  {C.YELLOW}⚠ nmap ARP 스캔 실패 (nmap 미설치?), ICMP ping sweep 사용{C.RESET}")

    # mDNS 캐시 수집
    print(f"\n  {C.GRAY}mDNS 캐시 수집 중...{C.RESET}", end=" ")
    sys.stdout.flush()
    mdns_map = build_mdns_map(network)
    if mdns_map:
        print(f"\r  {C.GREEN}✔ mDNS 캐시 {len(mdns_map)}개 항목 발견:{C.RESET}")
        for k, v in mdns_map.items():
            print(f"    {C.CYAN}{k:<18}{C.RESET}→  {C.YELLOW}{v}{C.RESET}")
        # 갱신된 mdns_map으로 ARP 장치의 hostname을 미리 채움
        if arp_hosts:
            for ip in mdns_map:
                if ip in arp_hosts:
                    pass
    else:
        print(f"\r  {C.GRAY}mDNS 캐시 없음 (ping sweep + 역방향 조회로 진행){C.RESET}")

    print(f"\n  {C.GRAY}스캔 중...{C.RESET}")
    if arp_hosts:
        print(f"  {C.GRAY}(ARP 스캔 기반으로 검증만 수행){C.RESET}")

    # ARP 테이블 사전 수집
    arp_table = get_arp_table()

    results = []
    done_count = 0
    lock = threading.Lock()
    start_time = time.time()

    def update_progress():
        sys.stdout.write(f"\r  {progress_bar(done_count, total)}  발견: {C.GREEN}{len(results)}{C.RESET}대   ")
        sys.stdout.flush()

    if arp_hosts:
        # ARP 스캔 결과가 있으면 해당 IP만 ping 검증
        scan_targets = [ip for ip in arp_hosts if ip in arp_table or ping(ip, timeout)]
        for ip in scan_targets:
            with lock:
                done_count += 1
                if ping(ip, timeout):
                    h = scan_host(ip, timeout, mdns_map)
                    if h:
                        # ARP 테이블에서 이미 MAC을 알면 재사용
                        if ip in arp_table and (h["mac"] == "??:??:??:??:??:??" or not h["mac"]):
                            h["mac"] = arp_table[ip]
                        results.append(h)
                update_progress()
        total = len(hosts_to_scan)  # 표시용 원래대로
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(scan_host, str(ip), timeout, mdns_map): ip for ip in hosts_to_scan}
            for future in as_completed(futures):
                with lock:
                    done_count += 1
                    result = future.result()
                    if result:
                        results.append(result)
                    update_progress()

    elapsed = time.time() - start_time
    results.sort(key=lambda x: socket.inet_aton(x["ip"]))

    print(f"\n\n  {C.GREEN}{C.BOLD}✔ 스캔 완료{C.RESET}  —  {elapsed:.1f}초 소요\n")
    if not results:
        print(f"  {C.YELLOW}활성 호스트를 찾지 못했습니다.{C.RESET}\n")
        print_usage_tips(do_flush)
        return

    # 장치 DB 로드 및 MAC 변경 감지
    db = load_device_db()
    results = check_mac_changes(results, db)

    print_table_header()
    for i, h in enumerate(results, 1):
        print_row(i, h, my_ip)

    print(f"\n  {C.GRAY}{'─' * 110}{C.RESET}")
    print(f"  {C.BOLD}총 {C.GREEN}{len(results)}{C.RESET}{C.BOLD}대 발견  /{C.RESET}  {total}개 스캔  ({elapsed:.1f}s)")

    # DB 업데이트 (변경 감지 후 저장)
    update_device_db(results)

    # MAC 변경이 감지된 장치 표시
    changed = [h for h in results if h.get("changes")]
    if changed:
        print(f"\n  {C.RED}{C.BOLD}⚠ MAC/호스트명 변경 감지!{C.RESET}")
        for h in changed:
            for ch in h["changes"]:
                print(f"    {C.YELLOW}{h['ip']}{C.RESET}: {C.RED}{ch}{C.RESET}")
        print(f"\n  {C.YELLOW}💡 SD 카드를 교체한 것으로 의심됩니다.{C.RESET}")
        print(f"     위 IP에 대해 새로운 SSH 접속 정보를 확인하세요.")

    # .local 장치 표시
    show_local_devices(results)

    # 알 수 없는 장치 안내
    unknown_count = sum(1 for h in results if h["hostname"] == "(알 수 없음)")
    if unknown_count > 0:
        print(f"\n  {C.YELLOW}💡 호스트명 미확인 장치 {unknown_count}대 있음.{C.RESET}")
        if not do_flush:
            print(f"     캐시 문제일 수 있으니 --flush 옵션으로 재시도 해보세요.")

    # 장치 DB 히스토리 표시
    db = load_device_db()
    history_items = {k: v for k, v in db.items() if len(v.get("mac_history", [])) > 0}
    if history_items:
        print(f"\n  {C.BOLD}{C.CYAN}📋 이전 MAC 변경 내역{C.RESET}")
        for ip, info in history_items.items():
            for h in info.get("mac_history", []):
                print(f"    {C.YELLOW}{ip:<18}{C.RESET} 이전MAC: {C.GRAY}{h['mac']:<20}{C.RESET} ({h.get('hostname','')})")

    save = input(f"\n  결과를 CSV로 저장할까요? (y/N): ").strip().lower()
    if save == "y":
        fname = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, "w", encoding="utf-8") as f:
            f.write("번호,IP,호스트명,MAC,제조사,변경사항\n")
            for i, h in enumerate(results, 1):
                chg = "; ".join(h.get("changes", []))
                f.write(f"{i},{h['ip']},{h['hostname']},{h['mac']},{h['vendor']},{chg}\n")
        print(f"  {C.GREEN}저장 완료: {fname}{C.RESET}")

    show_connect_menu(results)

# ── CLI ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="IP Scanner v5 — 네트워크 장치 탐색 (캐시 플러시 + MAC 변경 감지)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python ip_scanner5.py                              # 자동 네트워크 감지
  python ip_scanner5.py --flush                      # DNS/ARP 캐시 삭제 후 스캔
  python ip_scanner5.py --arp-scan                   # nmap ARP 스캔 (설치 필요)
  python ip_scanner5.py --flush --arp-scan           # 캐시 삭제 + ARP 스캔
  python ip_scanner5.py -n 192.168.1.0/24 -t 2      # 특정 네트워크
        """
    )
    parser.add_argument("-n", "--network",  help="스캔할 네트워크 (예: 192.168.1.0/24)")
    parser.add_argument("-t", "--timeout",  type=int, default=1,   help="ping 타임아웃 (초, 기본: 1)")
    parser.add_argument("-w", "--workers",  type=int, default=128, help="동시 스레드 수 (기본: 128)")
    parser.add_argument("-v", "--verbose",  action="store_true",   help="상세 출력")
    parser.add_argument("-f", "--flush",    action="store_true",   help="DNS/ARP 캐시 삭제 후 스캔")
    parser.add_argument("-a", "--arp-scan", action="store_true",   help="nmap ARP 스캔 사용 (설치 필요)")
    args = parser.parse_args()

    network = args.network
    if not network:
        my_ip = get_local_ip()
        network = guess_network(my_ip)

    try:
        run_scan(network, args.timeout, args.workers, args.verbose, args.flush, args.arp_scan)
    except KeyboardInterrupt:
        print(f"\n\n  {C.YELLOW}사용자가 스캔을 중단했습니다.{C.RESET}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
