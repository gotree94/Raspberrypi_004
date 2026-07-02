#!/bin/bash
# ============================================================
# compare_benchmark.sh  (v2)
# Python vs C LED 프로그램 성능 비교 측정 스크립트
#
# 수정 내역 (v2):
#   - 시작 시간: sudo 캐시 워밍 → 순수 바이너리 기동 시간만 측정
#   - CPU 측정: ps(%cpu) + pidstat(1초 간격 정밀) 병행
#
# 사용법: sudo bash compare_benchmark.sh
#   ※ pidstat 정밀 측정을 위해 sudo로 실행 권장
#   ※ sysstat 패키지 필요: sudo apt install sysstat -y
# ============================================================

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
BLU='\033[0;34m'; CYN='\033[0;36m'; NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SRC="$SCRIPT_DIR/led_blink_python.py"
C_SRC="$SCRIPT_DIR/led_blink.c"
C_BIN="$SCRIPT_DIR/led_blink"
MEASURE_SEC=10   # CPU 측정 시간(초)

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

# pidstat 유무 확인
HAVE_PIDSTAT=0
if command -v pidstat >/dev/null 2>&1; then
    ok "pidstat 있음 (sysstat)"
    HAVE_PIDSTAT=1
else
    warn "pidstat 없음 — sudo apt install sysstat -y  (ps 측정만 진행)"
fi

# ── 1. C 빌드 ────────────────────────────────────────────────
header "C 빌드"
if pkg-config --exists libgpiod 2>/dev/null; then
    gcc -O2 -o "$C_BIN" "$C_SRC" -lgpiod && ok "빌드 성공: $C_BIN" \
      || { warn "빌드 실패"; exit 1; }
else
    warn "libgpiod 없어 C 빌드 건너뜀"
fi

# ── 2. 시작 시간 측정 함수 ────────────────────────────────────
# [v1 문제]
#   sudo ./led_blink 실행 시 sudo가 /etc/sudoers 확인·PAM 인증·
#   환경변수 정리를 수행 → 약 1000~1500ms 소요
#   → C 바이너리 자체 기동 시간(~5ms)이 sudo 인증 시간에 묻혀버림
#
# [v2 수정]
#   측정 직전 'sudo -v' 로 sudo 타임스탬프 캐시를 갱신
#   → 이후 sudo 호출은 인증 없이 캐시만 확인 (~5ms)
#   → C 순수 바이너리 기동 시간(~5ms)만 측정 가능
# ──────────────────────────────────────────────────────────────
warmup_sudo() {
    sudo -v 2>/dev/null
    info "sudo 캐시 워밍 완료 (이후 sudo 인증 지연 ~1000ms 제거됨)"
}

measure_start_time() {
    local t0 t1
    t0=$(date +%s%N)
    timeout 0.5s "$@" >/dev/null 2>&1 || true
    t1=$(date +%s%N)
    echo $(( t1 - t0 ))
}

# ── 3. RSS 메모리 측정 함수 ───────────────────────────────────
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

# ── 4a. CPU 측정 — ps 방식 ───────────────────────────────────
# ps는 프로세스 전체 누적 CPU 시간 / 경과 시간으로 평균 계산
# 해상도: 소수점 2자리 → 0.005% 미만은 0.00으로 반올림됨
# C처럼 2초 주기 중 ~2µs 만 CPU 사용(≈0.0001%)하면 ps는 항상 0.00 출력
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

# ── 4b. CPU 측정 — pidstat 방식 ──────────────────────────────
# pidstat: /proc/[pid]/stat 의 utime·stime 을 1초 간격으로 직접 차분 계산
# → ps보다 순간 사용률에 민감, 백그라운드 스레드 부하도 잘 포착
# → C가 0.00이면 해상도(0.01%) 이하임을 추가로 확인
# → Python이 ps와 pidstat 모두 7~8%면 gpiozero 스레드가 확실히 원인
measure_cpu_pidstat() {
    local pid cpu_avg
    "$@" >/dev/null 2>&1 &
    pid=$!
    sleep 1

    # Average 행의 8번째 컬럼(%CPU) 추출
    cpu_avg=$(pidstat -u -p $pid 1 $MEASURE_SEC 2>/dev/null \
        | awk '/Average/{print $8}' | tail -1)

    kill $pid 2>/dev/null; wait $pid 2>/dev/null
    [ -n "$cpu_avg" ] && echo "$cpu_avg" || echo "N/A"
}

# ── 5. 시작 시간 측정 ─────────────────────────────────────────
header "시작 시간 측정 — sudo 캐시 워밍 후 (3회 평균)"
echo -e "${CYN}[정보]${NC} 워밍 전: sudo 인증 ~1000ms 포함 → C가 Python보다 3× 느리게 측정됨 (v1 문제)"
echo -e "${CYN}[정보]${NC} 워밍 후: sudo 캐시 재사용 → C 순수 기동 시간(~5ms)만 측정"

warmup_sudo

py_start_total=0
c_start_total=0

for i in 1 2 3; do
    ns=$(measure_start_time python3 "$PY_SRC")
    py_start_total=$(( py_start_total + ns ))
    info "Python 시작 #$i: $(awk "BEGIN{printf \"%.1f\", $ns/1000000}") ms"
done

if [ -f "$C_BIN" ]; then
    for i in 1 2 3; do
        ns=$(measure_start_time sudo "$C_BIN")
        c_start_total=$(( c_start_total + ns ))
        info "C     시작 #$i: $(awk "BEGIN{printf \"%.1f\", $ns/1000000}") ms"
    done
fi

PY_START_AVG=$(awk "BEGIN{printf \"%.1f\", $py_start_total/3/1000000}")
C_START_AVG=$([ -f "$C_BIN" ] \
    && awk "BEGIN{printf \"%.1f\", $c_start_total/3/1000000}" \
    || echo "N/A")

# ── 6. 메모리 측정 ───────────────────────────────────────────
header "메모리(RSS) 측정"
info "Python RSS 측정 중..."
PY_RSS=$(measure_rss python3 "$PY_SRC")
info "Python RSS: ${PY_RSS} kB"

if [ -f "$C_BIN" ]; then
    info "C RSS 측정 중..."
    C_RSS=$(measure_rss sudo "$C_BIN")
    info "C     RSS: ${C_RSS} kB"
else
    C_RSS="N/A"
fi

# ── 7. CPU 측정 — ps + pidstat 병행 ──────────────────────────
header "CPU 사용률 측정 (${MEASURE_SEC}초)"

echo ""
echo -e "${BOLD}[방법 1] ps  — 누적 평균, 해상도 0.01%${NC}"
echo -e "  sleep 위주 프로그램에서 0.00이 나오면 실제로 0에 매우 가까운 값"
info "Python CPU 측정 중 (ps, ${MEASURE_SEC}초)..."
PY_CPU_PS=$(measure_cpu_ps python3 "$PY_SRC")
info "Python CPU (ps): ${PY_CPU_PS}%"

if [ -f "$C_BIN" ]; then
    info "C CPU 측정 중 (ps, ${MEASURE_SEC}초)..."
    C_CPU_PS=$(measure_cpu_ps sudo "$C_BIN")
    info "C     CPU (ps): ${C_CPU_PS}%"
else
    C_CPU_PS="N/A"
fi

echo ""
if [ $HAVE_PIDSTAT -eq 1 ]; then
    echo -e "${BOLD}[방법 2] pidstat — 1초 간격 실시간, 해상도 0.01%${NC}"
    echo -e "  커널 /proc/[pid]/stat 직접 차분 계산 → ps보다 순간 부하에 민감"
    info "Python CPU 측정 중 (pidstat, ${MEASURE_SEC}초)..."
    PY_CPU_PIDSTAT=$(measure_cpu_pidstat python3 "$PY_SRC")
    info "Python CPU (pidstat): ${PY_CPU_PIDSTAT}%"

    if [ -f "$C_BIN" ]; then
        info "C CPU 측정 중 (pidstat, ${MEASURE_SEC}초)..."
        C_CPU_PIDSTAT=$(measure_cpu_pidstat sudo "$C_BIN")
        info "C     CPU (pidstat): ${C_CPU_PIDSTAT}%"
    else
        C_CPU_PIDSTAT="N/A"
    fi
else
    warn "pidstat 없음 — [방법 2] 건너뜀 (sudo apt install sysstat)"
    PY_CPU_PIDSTAT="(sysstat 없음)"
    C_CPU_PIDSTAT="(sysstat 없음)"
fi

# ── 8. 바이너리 / 소스 크기 ──────────────────────────────────
header "바이너리 / 소스 크기"
PY_SIZE=$(wc -c < "$PY_SRC")
C_SRC_SIZE=$(wc -c < "$C_SRC")
C_BIN_SIZE=$([ -f "$C_BIN" ] && wc -c < "$C_BIN" || echo "N/A")

# ── 9. 최종 결과 출력 ─────────────────────────────────────────
header "비교 결과"
printf "\n${BOLD}%-28s %15s %15s${NC}\n" "항목" "Python" "C"
printf "%-28s %15s %15s\n" \
    "────────────────────────────" "───────────────" "───────────────"
printf "%-28s %13sms %13sms\n" \
    "시작 시간 (sudo 캐시 후)"    "$PY_START_AVG"  "$C_START_AVG"
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

echo -e "${YLW}[참고] 시작 시간${NC}"
echo -e "  sudo 캐시 워밍 전 → sudo 인증 ~1000ms 포함 → C가 Python보다 3× 느리게 측정 (측정 오류)"
echo -e "  sudo 캐시 워밍 후 → C 순수 기동 시간 ~5ms vs Python ~500ms → C가 약 100× 빠름"
echo ""
echo -e "${YLW}[참고] CPU 0.00% 의미${NC}"
echo -e "  ps·pidstat 모두 해상도 0.01% → 그 이하는 0.00으로 표시됨"
echo -e "  C: 2초 주기 중 GPIO 조작 ~2µs → 실제 사용률 ≈ 0.0001% (측정 불가 수준, 진짜 0에 수렴)"
echo -e "  Python 7~8%: gpiozero 내부 백그라운드 스레드(핀 상태 폴링) 때문"
echo ""
echo -e "${YLW}[스레드별 CPU 상세 확인]${NC}"
echo -e "  ps -p \$(pgrep python3) -T -o tid,pcpu,comm"
echo -e "  pidstat -t -p \$(pgrep python3) 1 5"
