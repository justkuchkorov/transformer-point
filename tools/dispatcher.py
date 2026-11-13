"""IEC 104 dispatcher (the control room) for the transformer point.

Connects to the gateway, asks for everything once, then prints every value it
receives with its reason (cause of transmission), trust flag and time stamp.
Sends one ACK command after 5 s.

Run with the Python 3.13 environment: .venv313/Scripts/python tools/dispatcher.py
"""
import c104
import time

client = c104.Client()
connection = client.add_connection(ip="127.0.0.1", port=2404, init=c104.Init.ALL)
station = connection.add_station(common_address=1)

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

def doorbell(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
    trust = "ok" if point.quality.is_good() else "INVALID"
    print(point.io_address, point.value, message.cot, trust, point.recorded_at)
    return c104.ResponseState.SUCCESS

q1.on_receive(callable=doorbell)
q2.on_receive(callable=doorbell)
want_backup.on_receive(callable=doorbell)
u_main.on_receive(callable=doorbell)
u_backup.on_receive(callable=doorbell)
temperature.on_receive(callable=doorbell)
for i, name in enumerate(ALARM_NAMES):
    p = station.add_point(io_address=202+i, type=c104.Type.M_SP_TB_1)
    alarms[name] = p
    p.on_receive(callable=doorbell)


client.start()
print("Dispatcher running...")

started = time.monotonic()
muted_for = 0
ack_sent = False
while True:
    time.sleep(1)

    # If the dispatcher was started before the gateway, c104 connects later but
    # stays muted (connected, no data). After 3 s like that: start it ourselves.
    if connection.state == c104.ConnectionState.OPEN_MUTED:
        muted_for += 1
        if muted_for >= 3:
            connection.unmute()
            connection.interrogation(common_address=1)
            muted_for = 0
    else:
        muted_for = 0

    if not ack_sent and connection.is_connected and time.monotonic() - started > 5:
        ack.value = True
        print("ACK confirmed:", ack.transmit(cause=c104.Cot.ACTIVATION))
        ack_sent = True
