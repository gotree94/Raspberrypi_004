const express = require('express');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const PORT = 3000;

app.use(express.static(path.join(__dirname, 'public')));

function runCommand(cmd) {
  return new Promise((resolve) => {
    exec(cmd, { timeout: 5000, shell: '/bin/bash' }, (error, stdout, stderr) => {
      resolve({ stdout: (stdout || '').trim(), stderr: (stderr || '').trim(), error: !!error });
    });
  });
}

let prevCpuStat = null;

async function getCpuPercent() {
  const { stdout } = await runCommand("awk '/^cpu / {print $2,$3,$4,$5,$6,$7,$8}' /proc/stat");
  if (!stdout) return null;
  const parts = stdout.trim().split(/\s+/).map(Number);
  const total = parts.reduce((a, b) => a + b, 0);
  const idle = parts[3] + (parts[4] || 0);
  if (prevCpuStat) {
    const dTotal = total - prevCpuStat.total;
    const dIdle = idle - prevCpuStat.idle;
    prevCpuStat = { total, idle };
    return dTotal > 0 ? parseFloat(((dTotal - dIdle) / dTotal * 100).toFixed(1)) : 0;
  }
  prevCpuStat = { total, idle };
  return 0;
}

async function getMemPercent() {
  const { stdout } = await runCommand("awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {printf \"%.1f %.1f %.1f\", t/1024, (t-a)/1024, (t-a)/t*100}' /proc/meminfo");
  if (!stdout) return null;
  const p = stdout.trim().split(/\s+/).map(Number);
  return { totalMB: p[0], usedMB: p[1], percent: p[2] };
}

async function getTemp() {
  const { stdout } = await runCommand("vcgencmd measure_temp 2>/dev/null | grep -oP '[\\d.]+'");
  return stdout ? parseFloat(stdout) : null;
}

async function getClock() {
  const { stdout } = await runCommand("vcgencmd measure_clock arm 2>/dev/null | grep -oP '[\\d.]+'");
  return stdout ? (parseFloat(stdout) / 1000000).toFixed(1) : null;
}

async function getVoltage() {
  const r = (s) => {
    const m = s.match(/([\d.]+)/);
    return m ? parseFloat(m[1]) : null;
  };
  const [core, sdram_c, sdram_i, sdram_p] = await Promise.all([
    runCommand('vcgencmd measure_volts core 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_c 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_i 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_p 2>/dev/null'),
  ]);
  return {
    core: r(core.stdout),
    sdram_c: r(sdram_c.stdout),
    sdram_i: r(sdram_i.stdout),
    sdram_p: r(sdram_p.stdout),
  };
}

async function getThrottled() {
  const { stdout } = await runCommand('vcgencmd get_throttled 2>/dev/null');
  if (!stdout) return { hex: '0x0', bits: [] };
  const m = stdout.match(/0x([0-9a-fA-F]+)/);
  if (!m) return { hex: stdout, bits: [] };
  const val = parseInt(m[1], 16);
  const bits = [];
  if (val & 0x1) bits.push('undervoltage_now');
  if (val & 0x2) bits.push('freq_capped_now');
  if (val & 0x4) bits.push('throttling_now');
  if (val & 0x8) bits.push('soft_temp_limit_now');
  if (val & 0x10000) bits.push('undervoltage_occurred');
  if (val & 0x20000) bits.push('freq_capped_occurred');
  if (val & 0x40000) bits.push('throttling_occurred');
  if (val & 0x80000) bits.push('soft_temp_limit_occurred');
  return { hex: stdout, bits, value: val };
}

app.get('/api/snapshot', async (req, res) => {
  const [sys, temp, clock, mem, volt, thr, cpuPercent, load, gpuMem, armMem] = await Promise.all([
    Promise.all([
      runCommand("grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"'"),
      runCommand('uname -a'),
      runCommand('cat /proc/device-tree/model 2>/dev/null'),
      runCommand("grep Revision /proc/cpuinfo | awk '{print $3}'"),
      runCommand("grep Serial /proc/cpuinfo | awk '{print $3}'"),
      runCommand('vcgencmd version 2>/dev/null'),
    ]),
    getTemp(),
    getClock(),
    getMemPercent(),
    getVoltage(),
    getThrottled(),
    getCpuPercent(),
    runCommand("cat /proc/loadavg | awk '{print $1,$2,$3}'"),
    runCommand('vcgencmd get_mem gpu 2>/dev/null'),
    runCommand('vcgencmd get_mem arm 2>/dev/null'),
  ]);

  const s = { os: sys[0].stdout, uname: sys[1].stdout, model: sys[2].stdout, revision: sys[3].stdout, serial: sys[4].stdout, firmware: sys[5].stdout };

  res.json({
    system: s,
    cpu: { percent: cpuPercent, temp, clock, load: load.stdout },
    memory: { ...mem, gpuMem: gpuMem.stdout, armMem: armMem.stdout },
    voltage: volt,
    throttled: thr,
  });
});

app.get('/api/system', async (req, res) => {
  const [osRelease, uname, model, revision, serial, firmware] = await Promise.all([
    runCommand('cat /etc/os-release 2>/dev/null'),
    runCommand('uname -a'),
    runCommand('cat /proc/device-tree/model 2>/dev/null'),
    runCommand("grep Revision /proc/cpuinfo | awk '{print $3}'"),
    runCommand("grep Serial /proc/cpuinfo | awk '{print $3}'"),
    runCommand('vcgencmd version 2>/dev/null'),
  ]);
  res.json({ osRelease: osRelease.stdout, uname: uname.stdout, model: model.stdout, revision: revision.stdout, serial: serial.stdout, firmware: firmware.stdout });
});

app.get('/api/cpu', async (req, res) => {
  const [cpuinfo, lscpu, clock, temp, scalingFreq, load, percent] = await Promise.all([
    runCommand("grep -m1 'model name' /proc/cpuinfo 2>/dev/null"),
    runCommand('lscpu 2>/dev/null'),
    runCommand('vcgencmd measure_clock arm 2>/dev/null'),
    runCommand('vcgencmd measure_temp 2>/dev/null'),
    runCommand('cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null'),
    runCommand("awk '{print $1, $2, $3}' /proc/loadavg"),
    getCpuPercent(),
  ]);
  res.json({ cpuinfo: cpuinfo.stdout, lscpu: lscpu.stdout, clock: clock.stdout, temp: temp.stdout, scalingFreq: scalingFreq.stdout, load: load.stdout, percent });
});

app.get('/api/memory', async (req, res) => {
  const [free, meminfo, gpuMem, armMem, memPercent] = await Promise.all([
    runCommand('free -h'),
    runCommand("head -20 /proc/meminfo"),
    runCommand('vcgencmd get_mem gpu 2>/dev/null'),
    runCommand('vcgencmd get_mem arm 2>/dev/null'),
    getMemPercent(),
  ]);
  res.json({ free: free.stdout, meminfo: meminfo.stdout, gpuMem: gpuMem.stdout, armMem: armMem.stdout, percent: memPercent?.percent });
});

app.get('/api/voltage', async (req, res) => {
  const [coreVolt, sdramVolt, sdramI, sdramP, throttled] = await Promise.all([
    runCommand('vcgencmd measure_volts core 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_c 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_i 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_p 2>/dev/null'),
    runCommand('vcgencmd get_throttled 2>/dev/null'),
  ]);
  res.json({ coreVolt: coreVolt.stdout, sdramVolt: sdramVolt.stdout, sdramI: sdramI.stdout, sdramP: sdramP.stdout, throttled: throttled.stdout });
});

app.get('/api/disk', async (req, res) => {
  const [df, inode] = await Promise.all([
    runCommand('df -h'),
    runCommand('df -i 2>/dev/null'),
  ]);
  res.json({ df: df.stdout, inode: inode.stdout });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Pi Monitor running at http://localhost:${PORT}`);
});
