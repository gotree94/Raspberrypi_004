const express = require('express');
const { exec } = require('child_process');
const http = require('http');
const path = require('path');

const app = express();
const server = http.createServer(app);

const PORT = 3000;

// ─── 명령어 실행 헬퍼 ────────────────────────────────────────────────────────
function run(cmd) {
  return new Promise((resolve) => {
    exec(cmd, { timeout: 5000 }, (err, stdout) => {
      resolve(err ? '' : stdout.trim());
    });
  });
}

// ─── 데이터 수집 함수들 ───────────────────────────────────────────────────────

async function getOsInfo() {
  const [osRelease, kernel, model, revision, serial] = await Promise.all([
    run("cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"'"),
    run('uname -r'),
    run('cat /proc/device-tree/model 2>/dev/null || echo "N/A"'),
    run("cat /proc/cpuinfo | grep Revision | awk '{print $3}'"),
    run("cat /proc/cpuinfo | grep Serial | awk '{print $3}'"),
  ]);
  return { osRelease, kernel, model: model.replace(/\0/g, ''), revision, serial };
}

async function getCpuInfo() {
  const [clockRaw, tempRaw, throttleRaw, loadRaw, cpuCount] = await Promise.all([
    run('vcgencmd measure_clock arm 2>/dev/null || cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo "0"'),
    run('vcgencmd measure_temp 2>/dev/null || cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo "0"'),
    run('vcgencmd get_throttled 2>/dev/null || echo "throttled=0x0"'),
    run("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"),
    run('nproc'),
  ]);

  // 클럭 파싱
  let clockMHz = 0;
  if (clockRaw.includes('=')) {
    const hz = parseInt(clockRaw.split('=')[1]);
    clockMHz = Math.round(hz / 1000000);
  } else {
    clockMHz = Math.round(parseInt(clockRaw) / 1000);
  }

  // 온도 파싱
  let tempC = 0;
  if (tempRaw.includes('temp=')) {
    tempC = parseFloat(tempRaw.replace("temp=", "").replace("'C", ""));
  } else {
    tempC = parseFloat(tempRaw) / 1000;
  }

  // 스로틀링 파싱
  let throttleHex = '0x0';
  if (throttleRaw.includes('=')) {
    throttleHex = throttleRaw.split('=')[1];
  }
  const throttleVal = parseInt(throttleHex, 16);
  const throttleFlags = {
    undervoltNow:    !!(throttleVal & (1 << 0)),
    freqCapNow:      !!(throttleVal & (1 << 1)),
    throttledNow:    !!(throttleVal & (1 << 2)),
    tempLimitNow:    !!(throttleVal & (1 << 3)),
    undervoltPast:   !!(throttleVal & (1 << 16)),
    freqCapPast:     !!(throttleVal & (1 << 17)),
    throttledPast:   !!(throttleVal & (1 << 18)),
    tempLimitPast:   !!(throttleVal & (1 << 19)),
  };

  const cpuUsage = parseFloat(loadRaw) || 0;

  return { clockMHz, tempC: parseFloat(tempC.toFixed(1)), throttleHex, throttleFlags, cpuUsage, cpuCount: parseInt(cpuCount) };
}

async function getMemoryInfo() {
  const [memRaw, gpuMem, armMem] = await Promise.all([
    run('cat /proc/meminfo'),
    run('vcgencmd get_mem gpu 2>/dev/null || echo "gpu=0M"'),
    run('vcgencmd get_mem arm 2>/dev/null || echo "arm=0M"'),
  ]);

  const parse = (key) => {
    const match = memRaw.match(new RegExp(`${key}:\\s+(\\d+)`));
    return match ? parseInt(match[1]) * 1024 : 0; // KB → Bytes
  };

  const total    = parse('MemTotal');
  const free     = parse('MemFree');
  const buffers  = parse('Buffers');
  const cached   = parse('Cached');
  const available = parse('MemAvailable');
  const used     = total - available;

  const gpuMB = parseInt(gpuMem.replace('gpu=','').replace('M','')) || 0;
  const armMB = parseInt(armMem.replace('arm=','').replace('M','')) || 0;

  return {
    total, used, free, available, buffers, cached, gpuMB, armMB,
    usedPercent: total ? parseFloat(((used / total) * 100).toFixed(1)) : 0,
  };
}

async function getVoltageInfo() {
  const [core, sdramC, sdramI, sdramP] = await Promise.all([
    run('vcgencmd measure_volts core 2>/dev/null || echo "volt=0V"'),
    run('vcgencmd measure_volts sdram_c 2>/dev/null || echo "volt=0V"'),
    run('vcgencmd measure_volts sdram_i 2>/dev/null || echo "volt=0V"'),
    run('vcgencmd measure_volts sdram_p 2>/dev/null || echo "volt=0V"'),
  ]);

  const parseV = (s) => parseFloat(s.replace('volt=','').replace('V','')) || 0;
  return {
    core:   parseV(core),
    sdramC: parseV(sdramC),
    sdramI: parseV(sdramI),
    sdramP: parseV(sdramP),
  };
}

async function getDiskInfo() {
  const [dfRaw, dfInodeRaw] = await Promise.all([
    run("df -B1 | grep -v tmpfs | grep -v udev | tail -n +2"),
    run("df -i | grep -v tmpfs | grep -v udev | tail -n +2"),
  ]);

  const parseDF = (raw) => raw.split('\n').filter(Boolean).map(line => {
    const parts = line.trim().split(/\s+/);
    return {
      filesystem: parts[0],
      total:      parseInt(parts[1]) || 0,
      used:       parseInt(parts[2]) || 0,
      available:  parseInt(parts[3]) || 0,
      usedPercent: parts[4] ? parseInt(parts[4]) : 0,
      mountpoint:  parts[5] || '',
    };
  });

  return { disks: parseDF(dfRaw) };
}

async function getFirmwareInfo() {
  const firmware = await run('vcgencmd version 2>/dev/null || echo "N/A"');
  return { firmware };
}

// ─── REST API ─────────────────────────────────────────────────────────────────

app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/all', async (req, res) => {
  try {
    const [os, cpu, memory, voltage, disk, fw] = await Promise.all([
      getOsInfo(),
      getCpuInfo(),
      getMemoryInfo(),
      getVoltageInfo(),
      getDiskInfo(),
      getFirmwareInfo(),
    ]);
    res.json({ timestamp: Date.now(), os, cpu, memory, voltage, disk, firmware: fw.firmware });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/cpu', async (req, res) => {
  res.json(await getCpuInfo());
});

app.get('/api/memory', async (req, res) => {
  res.json(await getMemoryInfo());
});

app.get('/api/disk', async (req, res) => {
  res.json(await getDiskInfo());
});

// ─── SSE (Server-Sent Events) 실시간 스트림 ──────────────────────────────────
app.get('/api/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');

  const sendData = async () => {
    try {
      const [cpu, memory] = await Promise.all([getCpuInfo(), getMemoryInfo()]);
      const data = JSON.stringify({ timestamp: Date.now(), cpu, memory });
      res.write(`data: ${data}\n\n`);
    } catch (e) {
      res.write(`data: ${JSON.stringify({ error: e.message })}\n\n`);
    }
  };

  sendData();
  const interval = setInterval(sendData, 2000);
  req.on('close', () => clearInterval(interval));
});

// ─── 서버 시작 ────────────────────────────────────────────────────────────────
server.listen(PORT, '0.0.0.0', () => {
  console.log(`\n🍓 Raspberry Pi Monitor 서버 시작`);
  console.log(`   로컬:    http://localhost:${PORT}`);
  console.log(`   네트워크: http://$(hostname -I | awk '{print $1}'):${PORT}`);
  console.log(`\n   Ctrl+C 로 종료\n`);
});
