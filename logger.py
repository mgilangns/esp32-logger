import datetime
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import serial
import serial.tools.list_ports


class ESP32LoggerGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 Data Logger (Jamur Tiram)")
        self.root.geometry("600x450")
        self.root.minsize(500, 350)

        self.ser = None
        self.logging_active = False
        self.csv_file = None

        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        # --- Top Frame: Connection Controls ---
        control_frame = tk.LabelFrame(self.root, text=" Connection Settings ", padding=10)
        control_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(control_frame, text="COM Port:").grid(row=0, column=0, sticky="w", padx=5)
        
        self.port_combobox = ttk.Combobox(control_frame, width=15, state="readonly")
        self.port_combobox.grid(row=0, column=1, padx=5)

        self.btn_refresh = ttk.Button(control_frame, text="🔄 Refresh", command=self.refresh_ports, width=10)
        self.btn_refresh.grid(row=0, column=2, padx=5)

        self.btn_toggle = ttk.Button(control_frame, text="▶ Start Logging", command=self.toggle_logging, width=15)
        self.btn_toggle.grid(row=0, column=3, padx=10)

        # --- Middle Frame: Status Indicators ---
        status_frame = tk.Frame(self.root, padding=5)
        status_frame.pack(fill="x", padx=15)

        self.lbl_status = tk.Label(status_frame, text="Status: Disconnected", fg="red", font=("Helvetica", 10, "bold"))
        self.lbl_status.pack(side="left")

        self.lbl_filename = tk.Label(status_frame, text="", fg="gray", font=("Helvetica", 9, "italic"))
        self.lbl_filename.pack(side="right")

        # --- Bottom Frame: Real-time Terminal Monitor ---
        monitor_frame = tk.LabelFrame(self.root, text=" Data Stream Monitor ", padding=10)
        monitor_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.txt_monitor = tk.Text(monitor_frame, wrap="word", state="disabled", background="#1e1e1e", foreground="#ffffff", font=("Consolas", 9))
        self.txt_monitor.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(monitor_frame, command=self.txt_monitor.yview)
        scrollbar.pack(fill="y", side="right")
        self.txt_monitor.config(yscrollcommand=scrollbar.set)

    def refresh_ports(self):
        """Scans the system for active COM ports and updates the drop-down list."""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combobox["values"] = ports
        if ports:
            self.port_combobox.current(0)
        else:
            self.port_combobox.set("No Ports Found")

    def log_to_monitor(self, message):
        """Appends text smoothly to the GUI text terminal box."""
        self.txt_monitor.config(state="normal")
        self.txt_monitor.insert(tk.END, message + "\n")
        self.txt_monitor.see(tk.END)
        self.txt_monitor.config(state="disabled")

    def toggle_logging(self):
        if not self.logging_active:
            self.start_logging()
        else:
            self.stop_logging()

    def start_logging(self):
        selected_port = self.port_combobox.get()
        if not selected_port or selected_port == "No Ports Found":
            messagebox.showerror("Error", "Please select a valid COM port!")
            return

        try:
            self.ser = serial.Serial(selected_port, 115200, timeout=1)
            
            # Create the CSV data file locally
            file_timestamp = f"{datetime.datetime.now():%Y%m%d_%H%M%S}"
            self.filename = f"ground_truth_log_{file_timestamp}.csv"
            
            self.csv_file = open(self.filename, "w", encoding="utf-8")
            self.csv_file.write(
                "uptime_s,temp_C,hum_pct,lux,fan_pct,led_pct,"
                "humidifier,kondisi,latency_ms,sensor_accuracy_pct,"
                "network_pdr_pct,valid\n"
            )
            self.csv_file.flush()

            # Update System State
            self.logging_active = True
            self.btn_toggle.config(text="⏹ Stop Logging")
            self.port_combobox.config(state="disabled")
            self.btn_refresh.config(state="disabled")
            self.lbl_status.config(text=f"Status: Connected to {selected_port}", fg="green")
            self.lbl_filename.config(text=f"Logging to: {self.filename}")
            
            self.txt_monitor.config(state="normal")
            self.txt_monitor.delete("1.0", tk.END)
            self.txt_monitor.config(state="disabled")
            self.log_to_monitor(f"[SYSTEM] Connected successfully to {selected_port}.")
            self.log_to_monitor("[SYSTEM] Waiting for data frames from ESP32...")

            # Run network reading loop inside a separate background thread to prevent UI freezing
            self.thread = threading.Thread(target=self.read_serial_loop, daemon=True)
            self.thread.start()

        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Could not open port {selected_port}.\n{str(e)}")
            self.stop_logging()

    def read_serial_loop(self):
        while self.logging_active and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("CSV,"):
                    row = line[4:]  # Remove the 'CSV,' prefix string
                    
                    # Write immediately to hard disk storage frame
                    if self.csv_file:
                        self.csv_file.write(row + "\n")
                        self.csv_file.flush()
                    
                    # Pass the message to the main GUI thread safely
                    self.root.after(0, self.log_to_monitor, f"[LOGGED DATAFRAME]: {row}")
            except Exception:
                break
        
        # If loop breaks unexpectedly (device unplugged)
        if self.logging_active:
            self.root.after(0, self.handle_unexpected_disconnect)

    def handle_unexpected_disconnect(self):
        self.stop_logging()
        messagebox.showwarning("Disconnected", "The ESP32 was disconnected unexpectedly.")

    def stop_logging(self):
        self.logging_active = False
        
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            if self.csv_file:
                self.csv_file.close()
        except Exception:
            pass

        self.btn_toggle.config(text="▶ Start Logging")
        self.port_combobox.config(state="readonly")
        self.btn_refresh.config(state="normal")
        self.lbl_status.config(text="Status: Disconnected", fg="red")
        self.log_to_monitor("[SYSTEM] Session stopped. File saved successfully.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32LoggerGUI(root)
    root.mainloop()
