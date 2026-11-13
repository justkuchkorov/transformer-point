# Transformer ATS logic and IEC 104

This project is about a small version of the engineering of a transformer distribution system: a desk-size 10/0.4 kV transformer point with two supplies, built at 3.3 V.

In real life, we may have some electricity problems. We have a main supply and a backup supply. But sometimes the main supply can fail; at that time we have to switch to the backup supply, with some time delay, to prevent people from staying in the dark. However, this info can be untruthful, because our sensors may be dead and give us fake info about the main supply collapsing. For example, a gauge wire can be broken. So we are going to make a real-life simulation with my ESP32 at 3.3 V, resistors, Python and a PLC.

```
ESP32 (field)  ──Modbus──►  CODESYS PLC  ──Modbus──►  Python gateway  ──IEC 104──►  dispatcher
2 supply gauges,            the ATS,                  the RTU,                       the control
DS18B20, breakers Q1/Q2     in ladder                 port 2404                      room
```

Setup: <img width="2560" height="1438" alt="image" src="https://github.com/user-attachments/assets/0b59869a-7611-4448-a0fd-a0dd2fb31e7b" />

## What it does

- **Main lost for 3 s:** open Q1, *see* it open, then close Q2. Measured: **5.4 s** to backup, **1.8 s** with no supply in between.
- **A 2 s blink does nothing.** The 3 s timer starts again from zero.
- **A broken gauge wire does nothing.** A gauge reads 0.5 V on a dead supply but 0 V on a broken wire, so a broken wire never counts as a power cut.
- **Main healthy for 10 s:** back to main, with the same break-before-make.
- **Alarms:** frozen data (heartbeat watchdog), a breaker that does not move (locked out until ACK), a hot transformer (only when the sensor can be trusted).
- **The dispatcher sees it all over IEC 104:** positions, voltages, temperature and alarms, each with a time stamp and a trust flag. When the ESP32 goes silent, its values arrive marked **INVALID**, not as zeros.

![A transfer and the return, logged by the PLC](logs/ats_2026-11-08_02-34-49.png)

## Status

| Part | |
|---|---|
| 1. Field: gauges, ESP32 Modbus server, breaker simulator | ✅ |
| 2. ATS in ladder, CSV log and plot | ✅ |
| 3. What-if tests | ❌ not done |
| 4. IEC 104 gateway and dispatcher | ✅ with two gaps (below) |

**Known gaps, honestly:**

- **The ACK command** reaches the gateway but not the PLC, so the gateway refuses it instead of pretending.
- **No end-to-end run with the ESP32 yet.** IEC 104 was tested with the PLC running but the ESP32 off, and the field values arrived INVALID, as designed.
- **A start-up bug, found but not fixed.** Before its first data arrives, the PLC can send "open Q2" and latch Q2_FAIL. It needs "no commands until the first fresh heartbeat" (Part 3).

## Lessons that cost me the most

- **A broken wire is not a dead supply.** The ESP32 even reads 142 mV on a wire my meter shows as 0 V, so the broken-wire limit is 250 mV, not 0.
- **Logged in is not running.** CODESYS stays in STOP after a download.
- **Frozen data looks like good data.** The PLC kept showing 2042 mV after the Modbus link had died. Nothing noticed until I added the heartbeat watchdog.
- **A command left TRUE fires again** every 200 ms (pumping). Commands are now 500 ms pulses.
- **`WiFi.config()` with one argument** sets the ESP32's own address: mine became 255.255.255.0.
- **"0 mV" is a lie when there's no data.** IEC 104 trust flags say "don't trust" instead.

All 36 failures, the measurements, the maps and the 22 ladder networks are in **[docs/details.md](docs/details.md)**.

## Run it

Safety: USB power only, nothing above 3.3 V on any pin, no mains anywhere.

1. Flash [firmware/field_node](firmware/field_node) (create `secrets.h` with `WIFI_SSID` and `WIFI_PASS`).
2. Open [plc/ats_logic.project](plc/ats_logic.project) in CODESYS 3.5 SP22, download it to CODESYS Control Win and start it.
3. Python on Windows, from the repository folder:

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tools\ats_logger.py
.venv\Scripts\python tools\plot_log.py
```

The IEC 104 part needs Python 3.13 (c104 has no 3.14 build):

```
py install 3.13
py -V:3.13 -m venv .venv313
.venv313\Scripts\python -m pip install -r requirements-gateway.txt
.venv313\Scripts\python tools\gateway.py
.venv313\Scripts\python tools\dispatcher.py
```

## What I learnt

What I learnt today is that building hardware is so interesting, and after building the hardware, making the schematic design is so easy: you just look at your hardware setup, then copy it to KiCad. (Mistake 7 shows the copy still needs checking.)

## How this was made

I built, measured and drew everything myself, and I wrote the firmware, the PLC program, the Python logger and plotter, and the first IEC 104 gateway and dispatcher (reading the PLC, positions, alarms, deadbands). Claude (an AI tutor) explained the ideas, reviewed and compiled my code, ran checks on the board and the PLC, measured the transfer times from my CSV log, made the git commits, cleaned up the KiCad schematic and wrote this README from my notes. Claude also wrote the last gateway step (trust flags, the `update()` helper, PLC-loss handling) and the dispatcher's quality print and late-start fix, when I chose to finish Part 4 that way. I also asked other AI chatbots for explanations and help while coding.

## Repository

```
firmware/field_node/   ESP32 sketch (secrets.h stays local)
plc/                   CODESYS project: the ATS in ladder, SCADA_MAP in ST
tools/                 Modbus check, breaker commands, logger, plotter, IEC 104 gateway and dispatcher
logs/                  the transfer shown above
hardware/              KiCad 10 schematic and PDF
docs/details.md        everything else
```
