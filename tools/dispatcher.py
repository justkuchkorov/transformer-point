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
    print(point.io_address, point.value, message.cot, point.recorded_at)
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
while True:
    time.sleep(3)
    ack.value = True
    result = ack.transmit(cause=c104.Cot.ACTIVATION)
    print("ACK confirmed: ", result)