import sys
from pymodbus.client import ModbusTcpClient

SERVER_IP = "192.168.100.48"
SERVER_PORT = 502

client = ModbusTcpClient(SERVER_IP, port=SERVER_PORT)

print(f"Connecting to ESP32 at {SERVER_IP}:{SERVER_PORT}...")
if not client.connect():
    print("Connection failed!")
    sys.exit(1)

print("\n--- Breaker Q1 Remote Control ---")
print("Type 'c' to CLOSE the breaker")
print("Type 'o' to OPEN the breaker")
print("Type 'q' to quit")
print("---------------------------------")

try:
    while True:
        # Wait for user keyboard input
        cmd = input("Enter command (c/o/q): ").strip().lower()

        if cmd == 'c':
            print("Sending CLOSE command (Coil 0 = True)...")
            client.write_coil(0, True)

        elif cmd == 'o':
            print("Sending OPEN command (Coil 1 = True)...")
            client.write_coil(1, True)

        elif cmd == 'q':
            break

        else:
            print("Unknown command! Use 'c', 'o', or 'q'.")

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    client.close()
    print("Connection closed.")
