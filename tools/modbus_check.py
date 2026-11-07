import time
from pymodbus.client import ModbusTcpClient
import sys

SERVER_IP="192.168.100.48"
SERVER_PORT=502

client=ModbusTcpClient(SERVER_IP, port=SERVER_PORT)
print(f"Connecting to ESP32 at {SERVER_IP}:{SERVER_PORT}...")
is_connected = client.connect()
if not is_connected:
    print("Connection failed! Please check your network or ESP32 IP address.")
    sys.exit(1)

try:
    while True:
        response=client.read_input_registers(0,count=4)
        reaction = client.read_discrete_inputs(0, count=7)

        if response.isError() or reaction.isError():
            print("Error: Communication failure with Modbus Server!")
        else:
            u_main=response.registers[0]
            u_backup=response.registers[1]
            raw_temp=response.registers[2]
            heartbeat=response.registers[3]

            if raw_temp>32767:
                raw_temp-=65536
            temperature=raw_temp/10

            t_ok = 1 if reaction.bits[4] else 0
            q1_closed = 1 if reaction.bits[0] else 0
            q1_open = 1 if reaction.bits[1] else 0

            q2_closed = 1 if reaction.bits[2] else 0
            q2_open = 1 if reaction.bits[3] else 0
            q1_stuck = 1 if reaction.bits[5] else 0
            q2_stuck = 1 if reaction.bits[6] else 0

            print(
                f"U_MAIN={u_main} mV | U_BACKUP={u_backup} mV | Temp={temperature:.1f} °C | Heartbeat={heartbeat} | T_OK={t_ok} | Q1_CLOSED={q1_closed} | Q1_OPEN={q1_open} | Q2_CLOSED={q2_closed} | Q2_OPEN={q2_open} | Q1_STUCK={q1_stuck} | Q2_STUCK={q2_stuck}")

        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nStopping monitor...")
finally:
    client.close()
    print("Connection closed safely.")

