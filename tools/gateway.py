"""IEC 104 gateway (the RTU) for the transformer point.

Reads the PLC's five SCADA registers over Modbus TCP every second and serves
them to a dispatcher as IEC 60870-5-104, station 1, port 2404.

Trust flags: values that come from the ESP32 are marked Invalid while the PLC
reports COMMS_LOST, the temperature also while SENSOR_FAULT is on, and every
point is marked Invalid while the PLC itself cannot be read.

Run with the Python 3.13 environment: .venv313/Scripts/python tools/gateway.py
"""
import time

import c104
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

PLC_IP = "127.0.0.1"
PLC_PORT = 502
DEADBAND_MV = 20.0
DEADBAND_C = 0.2

ALARM_NAMES = [
    "COMMS_LOST", "Q1_FAIL", "Q2_FAIL", "TEMP_ALARM",
    "SENSOR_FAULT", "MAIN_WIRE_BAD", "BACKUP_WIRE_BAD",
]
# The PLC works these out from the ESP32's data, so they are only as
# trustworthy as that data. COMMS_LOST, Q1_FAIL and Q2_FAIL are the PLC's own.
FIELD_ALARMS = {"TEMP_ALARM", "SENSOR_FAULT", "MAIN_WIRE_BAD", "BACKUP_WIRE_BAD"}

GOOD = c104.Quality()
INVALID = c104.Quality.Invalid

server = c104.Server(ip="0.0.0.0", port=2404)
station = server.add_station(common_address=1)

q1 = station.add_point(io_address=101, type=c104.Type.M_DP_TB_1)
q2 = station.add_point(io_address=102, type=c104.Type.M_DP_TB_1)
want_backup = station.add_point(io_address=201, type=c104.Type.M_SP_TB_1)
alarms = {}
for i, name in enumerate(ALARM_NAMES):
    alarms[name] = station.add_point(io_address=202 + i, type=c104.Type.M_SP_TB_1)
u_main = station.add_point(io_address=301, type=c104.Type.M_ME_TF_1)
u_backup = station.add_point(io_address=302, type=c104.Type.M_ME_TF_1)
temperature = station.add_point(io_address=303, type=c104.Type.M_ME_TF_1)
ack = station.add_point(io_address=401, type=c104.Type.C_SC_NA_1)

ALL_POINTS = [q1, q2, want_backup, u_main, u_backup, temperature] + list(alarms.values())

# Until the first PLC read nothing is known, so every point starts as Invalid.
q1.value = c104.Double.INDETERMINATE
q2.value = c104.Double.INDETERMINATE
for p in ALL_POINTS:
    p.quality = INVALID


def to_double(closed, opened):
    """Two position contacts -> one IEC 104 double point."""
    if closed == 1 and opened == 0:
        return c104.Double.ON
    elif closed == 0 and opened == 1:
        return c104.Double.OFF
    elif closed == 0 and opened == 0:
        return c104.Double.INTERMEDIATE
    else:
        return c104.Double.INDETERMINATE


def update(point, label, new_value, quality, deadband=None):
    """Store a new value and trust flag; send them only if something changed.

    A number counts as changed only when it moved by at least its deadband,
    so the ADC's few millivolts of wobble are not sent.
    """
    if deadband is None:
        moved = new_value != point.value
    else:
        moved = abs(new_value - point.value) >= deadband
    if moved or point.quality != quality:
        point.value = new_value
        point.quality = quality
        point.transmit(cause=c104.Cot.SPONTANEOUS)
        flag = "" if quality == GOOD else "  (invalid)"
        print(f"{label}: {new_value}{flag}")


def mark_all_invalid():
    """Keep the last values but tell the dispatcher not to trust any of them."""
    for p in ALL_POINTS:
        if p.quality != INVALID:
            p.quality = INVALID
            p.transmit(cause=c104.Cot.SPONTANEOUS)


def on_ack(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
    # Passing the ACK on to the PLC (step 4.7) is not built, so the gateway
    # refuses the command instead of confirming something it did not do.
    print("ACK received, refused: passing it on to the PLC is not built yet")
    return c104.ResponseState.FAILURE


ack.on_receive(callable=on_ack)

plc = ModbusTcpClient(PLC_IP, port=PLC_PORT)
server.start()
print(f"Gateway running on port 2404, reading the PLC at {PLC_IP}:{PLC_PORT}")

plc_readable = None  # None until the first read, then True or False
try:
    while True:
        try:
            rr = plc.read_input_registers(0, count=5)
            if rr.isError():
                raise ModbusException(str(rr))
        except ModbusException as error:
            if plc_readable is not False:
                print(f"PLC not readable ({error}): every point marked invalid")
                mark_all_invalid()
                plc_readable = False
            time.sleep(1)
            continue
        if plc_readable is not True:
            print("PLC readable")
            plc_readable = True

        # 1. Unpack everything first.
        u_main_mv, u_backup_mv, raw_temp, state, alarm = rr.registers
        if raw_temp > 32767:
            raw_temp -= 65536
        temp_c = raw_temp / 10

        state_bits = []
        for n in range(12):
            state_bits.append((state >> n) & 1)
        alarm_bits = []
        for n in range(7):
            alarm_bits.append((alarm >> n) & 1)

        # 2. Decide how far the field values can be trusted.
        comms_lost = alarm_bits[0] == 1
        sensor_fault = alarm_bits[4] == 1
        field = INVALID if comms_lost else GOOD
        temp_quality = INVALID if comms_lost or sensor_fault else GOOD

        # 3. Update the points. Each one is sent only if it changed.
        update(q1, "Q1", to_double(state_bits[0], state_bits[1]), field)
        update(q2, "Q2", to_double(state_bits[2], state_bits[3]), field)
        update(want_backup, "WANT_BACKUP", state_bits[7] == 1, GOOD)
        update(u_main, "U_MAIN", float(u_main_mv), field, DEADBAND_MV)
        update(u_backup, "U_BACKUP", float(u_backup_mv), field, DEADBAND_MV)
        update(temperature, "TEMP", float(temp_c), temp_quality, DEADBAND_C)
        for i, name in enumerate(ALARM_NAMES):
            quality = field if name in FIELD_ALARMS else GOOD
            update(alarms[name], name, alarm_bits[i] == 1, quality)

        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping the gateway")
finally:
    server.stop()
    plc.close()
