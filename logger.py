import datetime
import serial

# Configure your hardware connection parameters
port = "COM3"  # Adjust to match your ESP32 operating system port identifier
baud = 115200

try:
    ser = serial.Serial(port, baud, timeout=1)
    file_timestamp = f"{datetime.datetime.now():%Y%m%d_%H%M%S}"
    fname = f"ground_truth_log_{file_timestamp}.csv"

    with open(fname, "w", encoding="utf-8") as f:
        # Write precise scientific header mapping
        f.write(
            "uptime_s,temp_C,hum_pct,lux,fan_pct,led_pct,"
            "humidifier,kondisi,latency_ms,sensor_accuracy_pct,"
            "network_pdr_pct,valid\n"
        )
        print(f"Successfully connected! Logging data directly to local file: {fname}")
        print("Press Ctrl+C to terminate logging safely.")

        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("CSV,"):
                row = line[4:]  # Slice out the local 'CSV,' signature label
                f.write(row + "\n")
                f.flush()  # Hard save to file storage frame immediately
                print(f"[LOGGED DATAFRAME]: {row}")

except serial.SerialException as e:
    print(f"Connection Error: Could not bind to interface {port}. {e}")
except KeyboardInterrupt:
    print("\nLogging terminated cleanly by user command.")
