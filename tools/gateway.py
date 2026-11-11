import c104
import time

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

server.start()
print("GateWay running...")

while True:
    want_backup.value = not want_backup.value
    want_backup.transmit(cause=c104.Cot.SPONTANEOUS)
    alarms["TEMP_ALARM"].value = want_backup.value
    alarms["TEMP_ALARM"].transmit(cause=c104.Cot.SPONTANEOUS)

    time.sleep(5)
