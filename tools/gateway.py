import c104
import time
from pymodbus.client import ModbusTcpClient
import sys

server = c104.Server(ip="0.0.0.0", port=2404)
station = server.add_station(common_address=1)

ALARM_NAMES = [
    "COMMS_LOST", "Q1_FAIL", "Q2_FAIL", "TEMP_ALARM",
    "SENSOR_FAULT", "MAIN_WIRE_BAD", "BACKUP_WIRE_BAD",
]

alarms = {}

q1 = station.add_point(io_address=101, type=c104.Type.M_DP_TB_1)
q2 = station.add_point(io_address=102, type=c104.Type.M_DP_TB_1)
want_backup = station.add_point(io_address=201, type=c104.Type.M_SP_TB_1)
u_main = station.add_point(io_address=301, type=c104.Type.M_ME_TF_1)
u_backup = station.add_point(io_address=302, type=c104.Type.M_ME_TF_1)
temperature = station.add_point(io_address=303, type=c104.Type.M_ME_TF_1)
ack = station.add_point(io_address=401, type=c104.Type.C_SC_NA_1)

q1.value = c104.Double.ON
q2.value = c104.Double.OFF
want_backup.value = False
u_main.value = 2035.0
u_backup.value = 2042.0
temperature.value = 20.0

for i, name in enumerate(ALARM_NAMES):
    p = station.add_point(io_address=202+i, type=c104.Type.M_SP_TB_1)
    p.value = False
    alarms[name] = p

def doorbell(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
    print("ACK received", point.io_address, point.value, message.cot, point.recorded_at)
    return c104.ResponseState.SUCCESS
ack.on_receive(callable=doorbell)

def to_double(closed, opened):
    if closed == 1 and opened == 0:
        return c104.Double.ON
    elif closed == 0 and opened == 1:
        return c104.Double.OFF
    elif closed == 0 and opened == 0:
        return c104.Double.INTERMEDIATE
    else:
        return c104.Double.INDETERMINATE

PLC_IP = "127.0.0.1"
PLC_PORT = 502
DEADBAND_MV = 20.0
DEADBAND_C = 0.2

plc = ModbusTcpClient(PLC_IP, port=PLC_PORT)
print(f"Connecting to PLC at {PLC_IP}:{PLC_PORT}...")
if not plc.connect():
    print("CONNECTION FAILED!")
    sys.exit(1)

server.start()
print("GateWay running...")

while True:
    rr = plc.read_input_registers(0, count=5)
    if rr.isError():
        print("PLC read error, retrying...")
        time.sleep(1)
        continue

    u_main_mv = rr.registers[0]
    u_backup_mv = rr.registers[1]



    new_u_main = float(u_main_mv)
    if abs(new_u_main - u_main.value) >= DEADBAND_MV:
        u_main.value = new_u_main
        u_main.transmit(cause=c104.Cot.SPONTANEOUS)
        print(f"NEW U_MAIN: {u_main}")

    new_u_backup = float(u_backup_mv)
    if abs(new_u_backup - u_backup.value) >= DEADBAND_MV:
        u_backup.value = new_u_backup
        u_backup.transmit(cause=c104.Cot.SPONTANEOUS)
        print(f"NEW U_BACKUP: {u_backup}")

    raw = rr.registers[2]
    if raw > 32767:
        raw -= 65536
    temp_c = raw / 10

    new_temp_c = float(temp_c)
    if abs(new_temp_c - temperature.value) >= DEADBAND_C:
        temperature.value = new_temp_c
        temperature.transmit(cause=c104.Cot.SPONTANEOUS)
        print(f"NEW TEMP: {temperature}")

    state = rr.registers[3]
    alarm = rr.registers[4]

    state_bits = []
    for n in range(12):
        state_bits.append((state >> n) & 1)

    q1_closed = state_bits[0]
    q1_open = state_bits[1]
    q2_closed = state_bits[2]
    q2_open = state_bits[3]

    new_q1 = to_double(q1_closed, q1_open)
    if new_q1 != q1.value:
        q1.value = new_q1
        q1.transmit(cause=c104.Cot.SPONTANEOUS)
        print(f"Q1: {new_q1}")

    new_q2 = to_double(q2_closed, q2_open)
    if new_q2 != q2.value:
        q2.value = new_q2
        q2.transmit(cause=c104.Cot.SPONTANEOUS)
        print(f"Q2: {new_q2}")

    new_wb = state_bits[7] == 1
    if new_wb != want_backup.value:
        want_backup.value = new_wb
        want_backup.transmit(cause=c104.Cot.SPONTANEOUS)
        print(f"WANT_BACKUP: {new_wb}")

    alarm_bits = []
    for n in range(7):
        alarm_bits.append((alarm >> n) & 1)

    for i, name in enumerate(ALARM_NAMES):
        new = alarm_bits[i] == 1
        p = alarms[name]
        if new != p.value:
            p.value = new
            p.transmit(cause=c104.Cot.SPONTANEOUS)
            print(f"{new}: {name}")

    print(f"U_MAIN = {u_main_mv}, U_BACKUP = {u_backup_mv}, TEMP = {temp_c}, STATE = {state}, ALARM = {alarm}")

    time.sleep(1)
