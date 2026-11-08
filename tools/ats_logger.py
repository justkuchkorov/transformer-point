import sys
import time
import csv
import os
from datetime import datetime
from pymodbus.client import ModbusTcpClient

PLC_IP = "127.0.0.1"
PLC_PORT = 502
PLC_PERIOD = 0.1
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

STATE_NAMES = [
    "Q1_CLOSED",
    "Q1_OPEN",
    "Q2_CLOSED",
    "Q2_OPEN",
    "MAIN_OK",
    "BACKUP_OK",
    "MAIN_LOST",
    "WANT_BACKUP",
    "Q1_CLOSE_CMD",
    "Q1_OPEN_CMD",
    "Q2_CLOSE_CMD",
    "Q2_OPEN_CMD",
]
ALARM_NAMES = [
    "COMMS_LOST", "Q1_FAIL", "Q2_FAIL", "TEMP_ALARM",
    "SENSOR_FAULT", "MAIN_WIRE_BAD", "BACKUP_WIRE_BAD",
]
COLUMNS = ["t_s", "u_main_mv", "u_backup_mv", "temp_c"] + STATE_NAMES + ALARM_NAMES

client = ModbusTcpClient(PLC_IP, port=PLC_PORT)

print(f"Connecting to PLC at {PLC_IP}:{PLC_PORT}...")
if not client.connect():
    print("Connection failed!")
    sys.exit(1)

filepath = os.path.join(LOG_DIR, f"ats_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv")
print(f"Logging to {filepath}  (Ctrl+C to stop)")

try:
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        t0 = time.monotonic()
        rows = 0

        while True:
            rr = client.read_input_registers(0, count=5)
            if rr.isError():
                print("Read error, retrying...")
                time.sleep(1)
                continue

            u_main_mv = rr.registers[0]
            u_backup_mv = rr.registers[1]

            raw = rr.registers[2]
            if raw > 32767:
                raw -= 65536
            temp_c = raw / 10

            state = rr.registers[3]
            alarm = rr.registers[4]

            state_bits = []
            for n in range(12):
                state_bits.append((state >> n) & 1)

            alarm_bits = []
            for n in range(7):
                alarm_bits.append((alarm >> n) & 1)

            t_s = round(time.monotonic() - t0, 3)

            row = [t_s, u_main_mv, u_backup_mv, temp_c] + state_bits + alarm_bits
            writer.writerow(row)
            f.flush()

            rows += 1
            if rows % 10 == 0:
                print(f"t={t_s:8.1f}s  U_main={u_main_mv:6d} mV  "
                      f"Q1={state_bits[0]}  Q2={state_bits[2]}  WANT_BACKUP={state_bits[7]}")

            time.sleep(PLC_PERIOD)

except KeyboardInterrupt:
    print(f"\nStopped. Saved to {filepath}")

finally:
    client.close()
    print("Connection closed.")