#!/usr/bin/env python3
"""
IP Scanner - 네트워크 장치 탐색 및 호스트명 표시
사용법: python3 ip_scanner.py [옵션]
"""

import subprocess
import socket
import threading
import ipaddress
import sys
import os
import time
import argparse
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

# ── 유틸리티 ───────────────────────────────────────────────
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def ping(ip, timeout=1):
    """호스트가 살아있는지 ping으로 확인"""
    param = "-n" if os.name == "nt" else "-c"
    w_param = ["-w", str(timeout * 1000)] if os.name == "nt" else ["-W", str(timeout)]
    cmd = ["ping", param, "1"] + w_param + [str(ip)]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 1
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# mDNS 사전 맵 구축
# Windows DNS 캐시에서 .local 이름 -> IPv4 매핑을 미리 수집.
# "ping rp4-nwkim.local" 을 한 번이라도 했다면 캐시에 남아 있다.
# ─────────────────────────────────────────────────────────────────────────────
def build_mdns_map():
    """
    Windows DNS 클라이언트 캐시에서 .local 항목 수집.
    반환: { "192.168.0.17": "rp4-nwkim.local", ... }
    """
    mdns_map = {}
    if os.name != "nt":
        return mdns_map
    try:
        ps = (
            "Get-DnsClientCache | "
            "Where-Object { $_.Entry -like '*.local' -and $_.Data -match '^[0-9]' } | "
            "ForEach-Object { $_.Entry + ' ' + $_.Data }"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode(errors="ignore")
        for line in out.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) == 2:
                name, ip_addr = parts[0].strip(), parts[1].strip()
                if name.endswith(".local") and ip_addr:
                    mdns_map[ip_addr] = name
    except Exception:
        pass
    return mdns_map


def get_hostname(ip, mdns_map):
    """IP -> 호스트명 조회 (4단계 시도)"""

    # ── 0) 사전 수집된 mDNS 캐시에서 즉시 반환 ───────────────
    if ip in mdns_map:
        return mdns_map[ip]

    # ── 1) 일반 역방향 DNS (PTR 레코드) ──────────────────────
    try:
        hostname = socket.gethostbyaddr(str(ip))[0]
        if hostname and not hostname.startswith(str(ip)):
            return hostname
    except (socket.herror, socket.gaierror, OSError):
        pass

    # ── 2) Windows 전용 처리 ─────────────────────────────────
    if os.name == "nt":
        # 2a) PowerShell Resolve-DnsName (Windows 10/11 내장 mDNS 활용)
        ps_script = (
            "try {"
            "  $r = Resolve-DnsName -Name " + ip + " -Type PTR -ErrorAction Stop;"
            "  $r.NameHost"
            "} catch {"
            "  $r = Resolve-DnsName -Name " + ip + " -ErrorAction SilentlyContinue;"
            "  if ($r) { $r[0].NameHost }"
            "}"
        )
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_script],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode(errors="ignore").strip()
            if out and len(out) > 2 and "\n" not in out:
                return out.rstrip(".")
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass

        # 2b) nbtstat -A (NetBIOS - Windows PC 이름 잘 잡힘)
        try:
            out = subprocess.check_output(
                ["nbtstat", "-A", str(ip)],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode(errors="ignore")
            for line in out.split("\n"):
                if "<00>" in line and "GROUP" not in line.upper():
                    parts = line.strip().split()
                    if parts and len(parts[0]) > 1:
                        return parts[0].strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass

    # ── 3) Linux/macOS 전용 처리 ─────────────────────────────
    else:
        try:
            out = subprocess.check_output(
                ["avahi-resolve-address", str(ip)],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode().strip()
            if out:
                parts = out.split()
                if len(parts) >= 2:
                    return parts[1].rstrip(".")
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass

        try:
            out = subprocess.check_output(
                ["nmblookup", "-A", str(ip)],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode()
            for line in out.split("\n"):
                if "<00>" in line and "GROUP" not in line:
                    name = line.strip().split()[0]
                    if name and name != "No":
                        return name
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass

    return ""


def get_mac_address(ip):
    """ARP 테이블에서 MAC 주소 가져오기"""
    try:
        if os.name == "nt":
            output = subprocess.check_output(["arp", "-a", str(ip)],
                                             stderr=subprocess.DEVNULL,
                                             timeout=2).decode()
            for line in output.split("\n"):
                if str(ip) in line:
                    parts = line.split()
                    for p in parts:
                        if "-" in p and len(p) == 17:
                            return p.upper()
        else:
            output = subprocess.check_output(["arp", "-n", str(ip)],
                                             stderr=subprocess.DEVNULL,
                                             timeout=2).decode()
            for line in output.split("\n"):
                if str(ip) in line:
                    parts = line.split()
                    for p in parts:
                        if ":" in p and len(p) == 17:
                            return p.upper()
    except Exception:
        pass
    return ""

def get_local_ip():
    """현재 기기의 로컬 IP 주소"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def guess_network(local_ip):
    """로컬 IP 기반으로 /24 네트워크 추정"""
    parts = local_ip.rsplit(".", 1)
    return f"{parts[0]}.0/24"

def vendor_hint(mac):
    """MAC OUI로 제조사 힌트"""
    oui_db = {
        "B8:27:EB": "Raspberry Pi",
        "DC:A6:32": "Raspberry Pi",
        "E4:5F:01": "Raspberry Pi",
        "D8:3A:DD": "Raspberry Pi",
        "00:50:56": "VMware",
        "00:0C:29": "VMware",
        "08:00:27": "VirtualBox",
        "AC:DE:48": "Apple",
        "F0:18:98": "Apple",
        "3C:22:FB": "Apple",
        "00:1A:A0": "Dell",
        "F8:DB:88": "Samsung",
        "78:11:DC": "Samsung",
        "00:1B:21": "Intel",
        "00:E0:4C": "Realtek",
    }
    prefix = mac[:8] if len(mac) >= 8 else ""
    return oui_db.get(prefix, "")

# ── 스캔 워커 ──────────────────────────────────────────────
def scan_host(ip, timeout, mdns_map):
    """단일 호스트 스캔"""
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
    }

# ── 헤더 / UI ──────────────────────────────────────────────
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
    print(f"  {C.GRAY}네트워크 장치 탐색기  ·  hostname / MAC / 제조사 표시{C.RESET}")
    print(f"  {C.GRAY}{'─' * 66}{C.RESET}\n")

def print_table_header():
    print(f"\n  {C.BOLD}{C.WHITE}{'NO':>3}  {'IP 주소':<17} {'호스트명':<32} {'MAC 주소':<20} {'제조사':<14}{C.RESET}")
    print(f"  {C.GRAY}{'─' * 94}{C.RESET}")

def print_row(idx, host, my_ip):
    tag = f" {C.GREEN}◀ 현재 기기{C.RESET}" if host["ip"] == my_ip else ""
    no_str   = f"{C.CYAN}{idx:>3}{C.RESET}"
    ip_str   = f"{C.YELLOW}{host['ip']:<17}{C.RESET}"
    hn_str   = f"{C.WHITE}{host['hostname']:<32}{C.RESET}"
    mac_str  = f"{C.GRAY}{host['mac']:<20}{C.RESET}"
    vnd_str  = f"{C.MAGENTA}{host['vendor']:<14}{C.RESET}"
    print(f"  {no_str}  {ip_str} {hn_str} {mac_str} {vnd_str}{tag}")

def progress_bar(done, total, width=40):
    pct = done / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"{C.CYAN}[{bar}]{C.RESET} {C.WHITE}{done}/{total}{C.RESET} ({pct*100:.0f}%)"

# ── SSH / 접속 도우미 ──────────────────────────────────────
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
    else:
        print(f"  {C.RED}잘못된 번호입니다.{C.RESET}")

# ── 메인 스캔 루프 ─────────────────────────────────────────
def run_scan(network, timeout, workers, verbose):
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

    # mDNS 캐시 사전 수집 (Windows)
    sys.stdout.write(f"\n  {C.GRAY}mDNS 캐시 수집 중...{C.RESET} ")
    sys.stdout.flush()
    mdns_map = build_mdns_map()
    if mdns_map:
        print(f"\r  {C.GREEN}✔ mDNS 캐시 {len(mdns_map)}개 항목 발견:{C.RESET}           ")
        for k, v in mdns_map.items():
            print(f"    {C.CYAN}{k:<18}{C.RESET}→  {C.YELLOW}{v}{C.RESET}")
    else:
        print(f"\r  {C.GRAY}mDNS 캐시 없음 (DNS/NetBIOS 방식으로 진행){C.RESET}    ")

    print(f"\n  {C.GRAY}스캔 중...{C.RESET}")

    results = []
    done_count = 0
    lock = threading.Lock()
    start_time = time.time()

    def update_progress():
        sys.stdout.write(f"\r  {progress_bar(done_count, total)}  발견: {C.GREEN}{len(results)}{C.RESET}대   ")
        sys.stdout.flush()

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
        return

    print_table_header()
    for i, h in enumerate(results, 1):
        print_row(i, h, my_ip)

    print(f"\n  {C.GRAY}{'─' * 94}{C.RESET}")
    print(f"  {C.BOLD}총 {C.GREEN}{len(results)}{C.RESET}{C.BOLD}대 발견  /{C.RESET}  {total}개 스캔  ({elapsed:.1f}s)")

    # .local 장치를 못 찾은 경우 안내
    unknown_count = sum(1 for h in results if h["hostname"] == "(알 수 없음)")
    if unknown_count > 0 and not mdns_map and os.name == "nt":
        print(f"\n  {C.YELLOW}💡 팁: 호스트명 미확인 장치 {unknown_count}대 있음.")
        print(f"     Raspberry Pi 등 .local 장치는 먼저 아래 명령 후 재스캔 하세요:")
        print(f"     {C.CYAN}ping rp4-nwkim.local{C.RESET}  {C.YELLOW}← Windows DNS 캐시에 등록됨{C.RESET}")

    save = input(f"\n  결과를 CSV로 저장할까요? (y/N): ").strip().lower()
    if save == "y":
        fname = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, "w", encoding="utf-8") as f:
            f.write("번호,IP,호스트명,MAC,제조사\n")
            for i, h in enumerate(results, 1):
                f.write(f"{i},{h['ip']},{h['hostname']},{h['mac']},{h['vendor']}\n")
        print(f"  {C.GREEN}저장 완료: {fname}{C.RESET}")

    show_connect_menu(results)

# ── CLI 진입점 ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="IP Scanner — 네트워크 장치 탐색 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python3 ip_scanner.py                       # 자동 네트워크 감지
  python3 ip_scanner.py -n 192.168.1.0/24     # 특정 서브넷 스캔
  python3 ip_scanner.py -n 10.0.0.0/24 -t 2  # 타임아웃 2초
  python3 ip_scanner.py -w 256                # 스레드 256개
        """
    )
    parser.add_argument("-n", "--network",  help="스캔할 네트워크 (예: 192.168.1.0/24)")
    parser.add_argument("-t", "--timeout",  type=int, default=1,   help="ping 타임아웃 (초, 기본: 1)")
    parser.add_argument("-w", "--workers",  type=int, default=128,  help="동시 스레드 수 (기본: 128)")
    parser.add_argument("-v", "--verbose",  action="store_true",    help="상세 출력")
    args = parser.parse_args()

    network = args.network
    if not network:
        my_ip = get_local_ip()
        network = guess_network(my_ip)

    try:
        run_scan(network, args.timeout, args.workers, args.verbose)
    except KeyboardInterrupt:
        print(f"\n\n  {C.YELLOW}사용자가 스캔을 중단했습니다.{C.RESET}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
