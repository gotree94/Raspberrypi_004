const express = require('express');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const PORT = 3000;

app.use(express.static(path.join(__dirname, 'public')));

function runCommand(cmd) {
  return new Promise((resolve) => {
    exec(cmd, { timeout: 5000, shell: '/bin/bash' }, (error, stdout, stderr) => {
      resolve({
        stdout: (stdout || '').trim(),
        stderr: (stderr || '').trim(),
        error: !!error,
      });
    });
  });
}

app.get('/api/system', async (req, res) => {
  const [osRelease, uname, model, revision, serial, firmware] = await Promise.all([
    runCommand('cat /etc/os-release 2>/dev/null'),
    runCommand('uname -a'),
    runCommand('cat /proc/device-tree/model 2>/dev/null; cat /proc/cpuinfo | grep -m1 "Model" 2>/dev/null'),
    runCommand("grep Revision /proc/cpuinfo | awk '{print $3}'"),
    runCommand("grep Serial /proc/cpuinfo | awk '{print $3}'"),
    runCommand('vcgencmd version 2>/dev/null'),
  ]);
  res.json({
    osRelease: osRelease.stdout,
    uname: uname.stdout,
    model: model.stdout,
    revision: revision.stdout,
    serial: serial.stdout,
    firmware: firmware.stdout,
  });
});

app.get('/api/cpu', async (req, res) => {
  const [cpuinfo, lscpu, clock, temp, scalingFreq, load] = await Promise.all([
    runCommand("grep -m1 'model name' /proc/cpuinfo 2>/dev/null"),
    runCommand('lscpu 2>/dev/null'),
    runCommand('vcgencmd measure_clock arm 2>/dev/null'),
    runCommand('vcgencmd measure_temp 2>/dev/null'),
    runCommand('cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null'),
    runCommand("awk '{print $1, $2, $3}' /proc/loadavg"),
  ]);
  res.json({
    cpuinfo: cpuinfo.stdout,
    lscpu: lscpu.stdout,
    clock: clock.stdout,
    temp: temp.stdout,
    scalingFreq: scalingFreq.stdout,
    load: load.stdout,
  });
});

app.get('/api/memory', async (req, res) => {
  const [free, meminfo, gpuMem, armMem] = await Promise.all([
    runCommand('free -h'),
    runCommand("head -20 /proc/meminfo"),
    runCommand('vcgencmd get_mem gpu 2>/dev/null'),
    runCommand('vcgencmd get_mem arm 2>/dev/null'),
  ]);
  res.json({
    free: free.stdout,
    meminfo: meminfo.stdout,
    gpuMem: gpuMem.stdout,
    armMem: armMem.stdout,
  });
});

app.get('/api/voltage', async (req, res) => {
  const [coreVolt, sdramVolt, sdramI, sdramP, throttled] = await Promise.all([
    runCommand('vcgencmd measure_volts core 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_c 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_i 2>/dev/null'),
    runCommand('vcgencmd measure_volts sdram_p 2>/dev/null'),
    runCommand('vcgencmd get_throttled 2>/dev/null'),
  ]);
  res.json({
    coreVolt: coreVolt.stdout,
    sdramVolt: sdramVolt.stdout,
    sdramI: sdramI.stdout,
    sdramP: sdramP.stdout,
    throttled: throttled.stdout,
  });
});

app.get('/api/disk', async (req, res) => {
  const [df, inode] = await Promise.all([
    runCommand('df -h'),
    runCommand('df -i 2>/dev/null'),
  ]);
  res.json({
    df: df.stdout,
    inode: inode.stdout,
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Pi Monitor running at http://localhost:${PORT}`);
});
