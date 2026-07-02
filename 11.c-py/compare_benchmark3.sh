#!/bin/bash
# ============================================================
# compare_benchmark.sh  (v3)
# Python vs C LED 프로그램 성능 비교 측정 스크립트
#
# 수정 내역 (v3):
#   - root(sudo)로 스크립트 전체 실행 → sudo 중간 레이어 완전 제거
#   - $! 로 sudo PID 잡던 문제 해결 → 실제 프로세스 PID 정확히 추적
#   - C RSS 0 kB, CPU N/A 버그 수정
#
# 사용법: sudo bash compare_benchmark.sh
#   ※ sysstat 패키지 필요: sudo apt install sysstat -y
# ============================================================

# ── root 권한 확인 ────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo "[오류] root 권한 필요: sudo bash $0"
    exit 1
fi

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
BLU='\033[0;34m'; CYN='\033[0;36m'; NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SRC="$SCRIPT_DIR/led_blink_python.py"
C_SRC="$SCRIPT_DIR/led_blink.c"
C_BIN="$SCRIPT_DIR/led_blink"
MEASURE_SEC=10

header() { echo -e "\n${BLU}${BOLD}══ $1 ══${NC}"; }
ok()     { echo -e "${GRN}[OK]${NC} $1"; }
warn()   { echo -e "${YLW}[!!]${NC} $1"; }
info()   { echo -e "${CYN}[--]${NC} $1"; }

# ── 0. 환경 확인 ─────────────────────────────────────────────
header "환경 확인"
python3 --version && ok "Python3 있음" || { warn "python3 없음"; exit 1; }
gcc --version | head -1 && ok "gcc 있음" || { warn "gcc 없음 — sudo apt install gcc"; exit 1; }
pkg-config --modversion libgpiod 2>/dev/null && ok "libgpiod 있음" \
  || warn "libgpiod 없음 — sudo apt install libgpiod-dev"

HAVE_PIDSTAT=0
if command -v pidstat >/dev/null 2>&1; then
    ok "pidstat 있음 (sysstat)"; HAVE_PIDSTAT=1
else
    warn "pidstat 없음 — sudo apt install sysstat -y"
fi

# ── 1. C 빌드 ────────────────────────────────────────────────
header "C 빌드"
if pkg-config --exists libgpiod 2>/dev/null; then
    gcc -O2 -o "$C_BIN" "$C_SRC" -lgpiod && ok "빌드 성공: $C_BIN" \
      || { warn "빌드 실패"; exit 1; }
else
    warn "libgpiod 없어 C 빌드 건너뜀"
fi

# ── 2. 시작 시간 측정 ─────────────────────────────────────────
# root로 실행 중이므로 sudo 불필요 → C 바이너리 직접 실행
# [v2 문제] sudo cmd & → $!는 sudo PID, 실제 C PID 아님
# [v3 수정] 스크립트를 root로 실행 → sudo 없이 직접 실행, PID 정확
measure_start_time() {
    local t0 t1
    t0=$(date +%s%N)
    timeout 0.5s "$@" >/dev/null 2>&1 || true
    t1=$(date +%s%N)
    echo $(( t1 - t0 ))
}

header "시작 시간 측정 (3회 평균)"
info "root 실행 → sudo 없이 C 바이너리 직접 기동 → 순수 기동 시간만 측정"

py_start_total=0; c_start_total=0

for i in 1 2 3; do
    ns=$(measure_start_time python3 "$PY_SRC")
    py_start_total=$(( py_start_total + ns ))
    info "Python 시작 #$i: $(awk "BEGIN{printf \"%.1f\", $ns/1000000}") ms"
done

if [ -f "$C_BIN" ]; then
    for i in 1 2 3; do
        ns=$(measure_start_time "$C_BIN")   # sudo 없이 직접 실행
        c_start_total=$(( c_start_total + ns ))
        info "C     시작 #$i: $(awk "BEGIN{printf \"%.1f\", $ns/1000000}") ms"
    done
fi

PY_START_AVG=$(awk "BEGIN{printf \"%.1f\", $py_start_total/3/1000000}")
C_START_AVG=$([ -f "$C_BIN" ] \
    && awk "BEGIN{printf \"%.1f\", $c_start_total/3/1000000}" \
    || echo "N/A")

# ── 3. RSS 메모리 측정 ───────────────────────────────────────
# [v2 문제] sudo cmd & → $!는 sudo PID → /proc/sudo_pid/status 읽어
#           sudo가 exec 후 사라지면 RSS=0 반환
# [v3 수정] 직접 실행 → $! = 실제 프로세스 PID → 정확한 RSS 측정
measure_rss() {
    local pid rss_max=0 rss
    "$@" >/dev/null 2>&1 &
    pid=$!
    for i in $(seq 1 20); do
        sleep 0.1
        rss=$(awk '/VmRSS/{print $2}' /proc/$pid/status 2>/dev/null) || break
        [ -n "$rss" ] && [ "$rss" -gt "$rss_max" ] && rss_max=$rss
    done
    kill $pid 2>/dev/null; wait $pid 2>/dev/null
    echo $rss_max
}

header "메모리(RSS) 측정"
info "Python RSS 측정 중..."
PY_RSS=$(measure_rss python3 "$PY_SRC")
info "Python RSS: ${PY_RSS} kB"

if [ -f "$C_BIN" ]; then
    info "C RSS 측정 중..."
    C_RSS=$(measure_rss "$C_BIN")           # sudo 없이 직접 실행
    info "C     RSS: ${C_RSS} kB"
else
    C_RSS="N/A"
fi

# ── 4. CPU 측정 — ps + pidstat 병행 ──────────────────────────
# [v2 문제] sudo cmd & → ps -p sudo_pid → sudo 종료 후 PID 없어져 N/A
# [v3 수정] 직접 실행 → ps/pidstat 이 실제 PID 정확히 추적

# 방법1: ps — 누적 평균 (해상도 0.01%)
measure_cpu_ps() {
    local pid samples=0 cpu_sum=0 cpu
    "$@" >/dev/null 2>&1 &
    pid=$!
    sleep 1
    for i in $(seq 1 $MEASURE_SEC); do
        cpu=$(ps -p $pid -o %cpu --no-headers 2>/dev/null | tr -d ' ') || break
        if [ -n "$cpu" ]; then
            cpu_sum=$(awk "BEGIN{print $cpu_sum + $cpu}")
            samples=$((samples + 1))
        fi
        sleep 1
    done
    kill $pid 2>/dev/null; wait $pid 2>/dev/null
    [ $samples -gt 0 ] \
        && awk "BEGIN{printf \"%.2f\", $cpu_sum / $samples}" \
        || echo "N/A"
}

# 방법2: pidstat — 1초 간격 실시간 (해상도 0.01%, 순간 부하에 민감)
measure_cpu_pidstat() {
    local pid cpu_avg
    "$@" >/dev/null 2>&1 &
    pid=$!
    sleep 1
    cpu_avg=$(pidstat -u -p $pid 1 $MEASURE_SEC 2>/dev/null \
        | awk '/Average/{print $8}' | tail -1)
    kill $pid 2>/dev/null; wait $pid 2>/dev/null
    [ -n "$cpu_avg" ] && echo "$cpu_avg" || echo "N/A"
}

header "CPU 사용률 측정 (${MEASURE_SEC}초)"

echo ""
echo -e "${BOLD}[방법 1] ps — 누적 평균, 해상도 0.01%${NC}"
echo -e "  0.00이 나오면 0.005% 미만 (사실상 0에 수렴)"
info "Python CPU 측정 중 (ps, ${MEASURE_SEC}초)..."
PY_CPU_PS=$(measure_cpu_ps python3 "$PY_SRC")
info "Python CPU (ps): ${PY_CPU_PS}%"

if [ -f "$C_BIN" ]; then
    info "C CPU 측정 중 (ps, ${MEASURE_SEC}초)..."
    C_CPU_PS=$(measure_cpu_ps "$C_BIN")
    info "C     CPU (ps): ${C_CPU_PS}%"
else
    C_CPU_PS="N/A"
fi

echo ""
if [ $HAVE_PIDSTAT -eq 1 ]; then
    echo -e "${BOLD}[방법 2] pidstat — 1초 간격 실시간, 해상도 0.01%${NC}"
    echo -e "  /proc/[pid]/stat 직접 차분 → 백그라운드 스레드 부하도 포착"
    info "Python CPU 측정 중 (pidstat, ${MEASURE_SEC}초)..."
    PY_CPU_PIDSTAT=$(measure_cpu_pidstat python3 "$PY_SRC")
    info "Python CPU (pidstat): ${PY_CPU_PIDSTAT}%"

    if [ -f "$C_BIN" ]; then
        info "C CPU 측정 중 (pidstat, ${MEASURE_SEC}초)..."
        C_CPU_PIDSTAT=$(measure_cpu_pidstat "$C_BIN")
        info "C     CPU (pidstat): ${C_CPU_PIDSTAT}%"
    else
        C_CPU_PIDSTAT="N/A"
    fi
else
    warn "pidstat 없음 — [방법 2] 건너뜀"
    PY_CPU_PIDSTAT="(sysstat 없음)"; C_CPU_PIDSTAT="(sysstat 없음)"
fi

# ── 5. 바이너리 / 소스 크기 ──────────────────────────────────
header "바이너리 / 소스 크기"
PY_SIZE=$(wc -c < "$PY_SRC")
C_SRC_SIZE=$(wc -c < "$C_SRC")
C_BIN_SIZE=$([ -f "$C_BIN" ] && wc -c < "$C_BIN" || echo "N/A")

# ── 6. 최종 결과 출력 ─────────────────────────────────────────
header "비교 결과"
printf "\n${BOLD}%-28s %15s %15s${NC}\n" "항목" "Python" "C"
printf "%-28s %15s %15s\n" \
    "────────────────────────────" "───────────────" "───────────────"
printf "%-28s %13sms %13sms\n" \
    "시작 시간 (직접 실행)"       "$PY_START_AVG"  "$C_START_AVG"
printf "%-28s %12s kB %12s kB\n" \
    "메모리 RSS"                  "$PY_RSS"        "$C_RSS"
printf "%-28s %14s%% %14s%%\n" \
    "CPU — ps (누적 평균)"        "$PY_CPU_PS"     "$C_CPU_PS"
printf "%-28s %14s%% %14s%%\n" \
    "CPU — pidstat (순간 평균)"   "$PY_CPU_PIDSTAT" "$C_CPU_PIDSTAT"
printf "%-28s %13s B  %13s B\n" \
    "소스 크기"                   "$PY_SIZE"       "$C_SRC_SIZE"
printf "%-28s %15s %12s B\n" \
    "실행 파일 크기"              "(인터프리터)"   "$C_BIN_SIZE"
printf "\n"

echo -e "${YLW}[v2→v3 수정 내역]${NC}"
echo -e "  v2 문제: sudo cmd & → \$!= sudo PID → RSS=0, CPU=N/A 오측정"
echo -e "  v3 수정: sudo bash 로 스크립트 전체 root 실행 → C 직접 실행"
echo -e "           → \$! = 실제 프로세스 PID → RSS·CPU 정확히 측정"
echo ""
echo -e "${YLW}[참고] CPU 0.00% 의미${NC}"
echo -e "  C: 2초 주기 중 GPIO 조작 ~2µs → 실제 사용률 ≈ 0.0001% (측정 불가, 진짜 0에 수렴)"
echo -e "  Python 7~8%: gpiozero 내부 백그라운드 스레드(핀 상태 폴링) 때문"
echo ""
echo -e "${YLW}[스레드별 CPU 상세 확인]${NC}"
echo -e "  ps -p \$(pgrep python3) -T -o tid,pcpu,comm"
echo -e "  pidstat -t -p \$(pgrep python3) 1 5"
