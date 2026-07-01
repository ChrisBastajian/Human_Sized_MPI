import matplotlib.pyplot as plt
import pyvisa
import numpy as np
import time
import customtkinter as ctk
from tkinter import Listbox
import wave_gen
import receive_and_analyze as analyze
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import os
import importlib
import sys
import socket
import threading

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
calibration_dir = os.path.join(root_dir, "Field Calibration")
sys.path.append(calibration_dir)

module_name = "H_field_mapper"
H_plotter = importlib.import_module(module_name)

ctk.set_appearance_mode("light_gray")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ── Default values ──────────────────────────────────────────────────
        self.waveform_generator = wave_gen.find_and_connect_waveform_generator()
        self.H_V_slope          = None
        self.H_I_slope          = 419.8e-3      # mT/A
        self.V_I_sensitivity    = 40e-3          # V/A
        self.tx_H_amplitude     = 1.0            # mT
        self.tx_frequency       = 1000           # Hz
        self.wavegen_channel    = 1
        self.daq_trigger_channel = "/Dev1/pfi0"
        self.daq_current_channel = "Dev1/ai1"
        self.sample_rate        = 100e3
        self.num_periods        = 100
        self.H_cal              = None
        self.V_cal              = None
        self.coil_on            = False

        self.xy_position    = 0                 # degrees
        self.z_position     = 0                 # metres
        self.xy_ratio       = 2.031219320636167 #2:1 Gear Ratio Used
        self.z_ratio        = 10e-3 / 360       #10 mm for 360 degrees
        self.desired_height = 0.05              # m
        self.desired_angle  = 1080              # degrees
        self.rot_time       = 10                # seconds

        #Arduino Connections
        self.arduino1_ip = "192.168.4.1"
        self.arduino1_port = 5000
        self.arduino1_socket = None
        self.arduino1_lock = threading.Lock()
        threading.Thread(target=self.connect_arduino1, daemon=True).start()

        self.arduino2_serial_port = "COM5"
        self.serial_lock = threading.Lock()
        threading.Thread(target=self.connect_arduino2, daemon=True).start()

        self.operating_modes = {
            "Mode 1 - 5193 Hz": {"freq": 5193, "impedance": 1},
            "Mode 2 - 14680 Hz": {"freq": 14680, "impedance": 2},
            "Mode 3 - 21670 Hz": {"freq": 21670, "impedance": 3},
            "Mode 4 - 26170 Hz": {"freq": 26170, "impedance": 4},
            "Mode 5 - 29160 Hz": {"freq": 29160, "impedance": 5},
            "Mode 6 - 34150 Hz": {"freq": 34150, "impedance": 6},
        }

        # ── Window setup ────────────────────────────────────────────────────
        self.title("MPI Platform App")
        self.iconbitmap("mpi_logo.ico")         # Windows taskbar icon (MPI LOGO)
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.state("zoomed")                    # Maximize window on start



        # ── Font helper ─────────────────────────────────────────────────────
        # Design reference: 1080 p. Everything scales from there.
        self._scale = sh / 1080

        def F(size):
            """Return a scaled font tuple."""
            return ('Arial', max(int(size * self._scale), 8))

        def FT(size):
            """Times New Roman scaled."""
            return ('Times New Roman', max(int(size * self._scale), 8))

        # ── Root layout: title bar + content ────────────────────────────────
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Title / nav bar ─────────────────────────────────────────────────
        nav = ctk.CTkFrame(self, corner_radius=0, fg_color='gray')
        nav.grid(row=0, column=0, sticky="ew")

        btn_names = ["Settings", "Calibrate", "Run Steppers",
                     "Run Coil",  "Stop",       "Auto Mode"]
        for i, name in enumerate(btn_names):
            nav.grid_columnconfigure(i, weight=1)
            b = ctk.CTkButton(
                nav, text=name, font=F(14),
                command=lambda idx=i: self.title_bar_command(idx),
                height=max(int(36 * self._scale), 28)
            )
            b.grid(row=0, column=i, padx=6, pady=6, sticky="ew")

        # ── Content area: left panel | right panel (plots) ───────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        content.grid_columnconfigure(0, weight=3)   # left controls
        content.grid_columnconfigure(1, weight=5)   # right plots
        content.grid_rowconfigure(0, weight=1)

        # ── LEFT PANEL ───────────────────────────────────────────────────────
        left = ctk.CTkFrame(content, fg_color='lightgray', corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.grid_columnconfigure((0, 1), weight=1)

        # ---- Controls Parameters section ----
        ctk.CTkLabel(left, text="Controls Parameters", font=FT(22)
                     ).grid(row=0, column=0, columnspan=2, pady=(10, 4))

        # XY sub-header
        ctk.CTkLabel(left, text="XY Rotation Control", font=FT(17)
                     ).grid(row=1, column=0, columnspan=2, pady=(6, 2))

        ctk.CTkLabel(left, text="Desired turns [turns]", font=F(13)
                     ).grid(row=2, column=0, padx=8, sticky="e")

        self.xy_entry = ctk.CTkEntry(left, font=F(13),
                                     placeholder_text=f"{self.desired_angle / 360:.2f}")
        self.xy_entry.configure(state="readonly")
        self.xy_entry.grid(row=2, column=1, padx=8, pady=3, sticky="w")

        self.xy_slider = ctk.CTkSlider(left, from_=0, to=3, number_of_steps=6,
                                       command=self.xy_slider_callback)
        self.xy_slider.set(self.desired_angle / 360)
        self.xy_slider.grid(row=3, column=0, columnspan=2, padx=16, pady=4, sticky="ew")

        # Z sub-header
        ctk.CTkLabel(left, text="Z Translation Control", font=FT(17)
                     ).grid(row=4, column=0, columnspan=2, pady=(10, 2))

        ctk.CTkLabel(left, text="Desired Z Height [mm]", font=F(13)
                     ).grid(row=5, column=0, padx=8, sticky="e")

        self.z_entry = ctk.CTkEntry(left, font=F(13),
                                    placeholder_text=f"{self.desired_height * 1e3:.0f}")
        self.z_entry.configure(state="readonly")
        self.z_entry.grid(row=5, column=1, padx=8, pady=3, sticky="w")

        self.z_slider = ctk.CTkSlider(left, from_=0, to=250, number_of_steps=250,
                                      command=self.z_slider_callback)
        self.z_slider.set(self.desired_height * 1e3)
        self.z_slider.grid(row=6, column=0, columnspan=2, padx=16, pady=4, sticky="ew")

        # Time entry
        ctk.CTkLabel(left, text="Time [s]", font=F(13)
                     ).grid(row=7, column=0, padx=8, pady=(10, 3), sticky="e")
        self.time_entry = ctk.CTkEntry(left, font=F(13),
                                       placeholder_text=f"{self.rot_time}")
        self.time_entry.grid(row=7, column=1, padx=8, pady=(10, 3), sticky="w")
        self.time_entry.bind("<KeyRelease>", self.time_entry_update)

        # Separator line
        sep = ctk.CTkFrame(left, height=2, fg_color="darkgray")
        sep.grid(row=8, column=0, columnspan=2, sticky="ew", padx=8, pady=10)

        # ---- Drive Coil Parameters section ----
        ctk.CTkLabel(left, text="Drive Coil Parameters", font=FT(22)
                     ).grid(row=9, column=0, columnspan=2, pady=(4, 6))


        # Amplitude
        ctk.CTkLabel(left, text="Amplitude [mT_pk]", font=F(13)
                     ).grid(row=10, column=0, padx=8, pady=3, sticky="e")
        self.amplitude_entry = ctk.CTkEntry(left, font=F(13),
                                            placeholder_text=f"{self.tx_H_amplitude}")
        self.amplitude_entry.grid(row=10, column=1, padx=8, pady=3, sticky="w")

        # Frequency
        ctk.CTkLabel(left, text="Frequency", font=F(13)
                     ).grid(row=11, column=0, padx=8, pady=3, sticky="e")

        self.frequency_entry = ctk.CTkEntry(left, font = F(13), placeholder_text=f"{self.tx_frequency}")

        self.frequency_entry.grid(row=11, column=1, padx=8, pady=3, sticky="w")

        # Current DAQ channel
        ctk.CTkLabel(left, text="Current DAQ Channel", font=F(13)
                     ).grid(row=12, column=0, padx=8, pady=3, sticky="e")
        self.current_channel_dropdown = ctk.CTkOptionMenu(
            left, font=F(13),
            values=["Dev94/ai1", "Dev94/ai0", "Dev1/ai1", "Dev0/ai0",
                    "Dev0/ai1", "Dev1/ai0", "Dev2/ai0", "Dev2/ai1"]
        )
        self.current_channel_dropdown.grid(row=12, column=1, padx=8, pady=3, sticky="ew")

        # Wave generator resource
        ctk.CTkLabel(left, text="Wave Generator", font=F(13)
                     ).grid(row=13, column=0, padx=8, pady=3, sticky="e")
        self.wavegen_dropdown = ctk.CTkOptionMenu(
            left, font=F(13), dynamic_resizing=False,
            values=list(pyvisa.ResourceManager().list_resources()) or ["No device found"]
        )
        self.wavegen_dropdown.grid(row=13, column=1, padx=8, pady=3, sticky="ew")

        # Buttons row
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.grid(row=14, column=0, columnspan=2, pady=10)
        ctk.CTkButton(btn_frame, text="Save Parameters", font=F(13),
                      command=self.save_tx_parameters
                      ).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Find Tuning Frequency", font=F(13),
                      command=self.find_tuning_frequency
                      ).pack(side="left", padx=6)

        # ── RIGHT PANEL (two plots stacked) ─────────────────────────────────
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.fig1, self.ax1 = plt.subplots(tight_layout=True)
        self.fig2, self.ax2 = plt.subplots(tight_layout=True)

        for row_idx, (fig, ax, label) in enumerate(
            [(self.fig1, self.ax1, "Plot 1"), (self.fig2, self.ax2, "Plot 2")]
        ):
            pframe = ctk.CTkFrame(right, fg_color='gray', corner_radius=6)
            pframe.grid(row=row_idx, column=0, sticky="nsew", pady=(0, 4))
            pframe.grid_rowconfigure(1, weight=1)
            pframe.grid_columnconfigure(0, weight=1)

            # Button row above each plot
            btn_row = ctk.CTkFrame(pframe, fg_color="transparent")
            btn_row.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
            ctk.CTkButton(btn_row, text="View Full Plot", width=110, font=F(11),
                          command=lambda f=fig: self.open_plot_window(f)
                          ).pack(side="left", padx=4)
            ctk.CTkButton(btn_row, text="Clear", width=70, font=F(11),
                          command=lambda a=ax: self.clear_plot(a)
                          ).pack(side="left", padx=4)

            canvas = FigureCanvasTkAgg(fig, master=pframe)
            canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

            toolbar_frame = ctk.CTkFrame(pframe, fg_color="transparent")
            toolbar_frame.grid(row=2, column=0, sticky="ew")
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()

            if row_idx == 0:
                self.canvas1 = canvas
            else:
                self.canvas2 = canvas

    # ── Helpers ─────────────────────────────────────────────────────────────

    # Send Communication to Arduino1 over WIFI
    def send_arduino1(self, msg):
        try:
            with self.arduino1_lock:
                if self.arduino1_socket is None:
                    threading.Thread(target=self.connect_arduino1, daemon=True).start()
                    return

                self.arduino1_socket.sendall((msg + "\n").encode())
                print("Sent Arduino1:", msg)

        except Exception as e:
            print("Arduino1 send failed:", e)
            self.arduino1_socket = None

    # Wifi Connect to Motor Driving Arduino (Arduino1)
    def connect_arduino1(self):
        try:
            print("Connecting Arduino1...")
            self.arduino1_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.arduino1_socket.connect((self.arduino1_ip, self.arduino1_port))
            print("Arduino1 WiFi connected")
        except Exception as e:
            print("Arduino1 connection failed:", e)
            self.arduino1_socket = None

    def connect_arduino2(self):
        try:
            print("Connecting Arduino2...")
            self.arduino2 = serial.Serial(self.arduino2_serial_port, 9600, timeout=1)
            time.sleep(2)
            print("Arduino2 Serial Connected")
        except Exception as e:
            print("Arduino2 Serial failed:", e)
            self.arduino2 = None

    def clear_plot(self, ax):
        ax.clear()
        ax.figure.canvas.draw_idle()

    def open_plot_window(self, figure):
        win = ctk.CTkToplevel(self)
        win.title("Full Plot")
        win.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}")
        win.attributes("-topmost", True)

        frame = ctk.CTkFrame(win, fg_color="gray")
        frame.pack(fill="both", expand=True)

        new_fig = plt.Figure()
        new_ax  = new_fig.add_subplot(111)
        for line in figure.axes[0].lines:
            new_ax.plot(line.get_xdata(), line.get_ydata(), label=line.get_label())
        new_ax.set_xlabel(figure.axes[0].get_xlabel())
        new_ax.set_ylabel(figure.axes[0].get_ylabel())
        new_ax.set_title(figure.axes[0].get_title())
        if figure.axes[0].get_legend():
            new_ax.legend()

        canvas = FigureCanvasTkAgg(new_fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        NavigationToolbar2Tk(canvas, frame).pack(side="bottom", fill="x")

    # ── Nav-bar commands ─────────────────────────────────────────────────────

    def title_bar_command(self, button):
        actions = {
            0: self.open_settings_dropdown,
            1: lambda: threading.Thread(target=self.calibrateH_V, daemon=True).start(),
            2: lambda: threading.Thread(target=self.run_steppers,  daemon=True).start(),
            3: lambda: threading.Thread(target=self.run_tx_coil,   daemon=True).start(),
            4: self.turn_off,
            5: lambda: threading.Thread(target=self.auto_mode,     daemon=True).start(),
        }
        actions.get(button, lambda: None)()

    # ── Slider / entry callbacks ─────────────────────────────────────────────

    def z_slider_callback(self, value):
        v = int(value)
        self.z_entry.configure(state="normal")
        self.z_entry.delete(0, "end")
        self.z_entry.insert(0, str(v))
        self.z_entry.configure(state="readonly")
        self.desired_height = v * 1e-3

    def xy_slider_callback(self, value):
        self.xy_entry.configure(state="normal")
        self.xy_entry.delete(0, "end")
        self.xy_entry.insert(0, f"{value:.2f}")
        self.xy_entry.configure(state="readonly")
        self.desired_angle = int(value * 360)

    def time_entry_update(self, event=None):
        try:
            self.rot_time = float(self.time_entry.get())
        except ValueError:
            pass

    # ── Calibration ──────────────────────────────────────────────────────────

    def calibrateH_V(self):
        self.H_cal = []
        self.V_cal = []

        v_amplitude    = 0.0
        sample_rate    = self.sample_rate
        num_periods    = int(self.num_periods)
        num_samples    = int(num_periods * sample_rate / self.tx_frequency)
        frequency      = float(self.tx_frequency)
        wavegen_ch     = int(self.wavegen_channel)

        for _ in range(49):
            wave_gen.send_voltage(self.waveform_generator, v_amplitude, frequency, wavegen_ch)
            if v_amplitude > 3:
                v_amplitude = 0.0

            i_rms       = analyze.get_rms_current(self.daq_current_channel, sample_rate,
                                                   num_samples, sensitivity=self.V_I_sensitivity)
            H_magnitude = self.H_I_slope * i_rms * np.sqrt(2)

            self.H_cal.append(H_magnitude)
            self.V_cal.append(v_amplitude)
            v_amplitude += 0.02
            time.sleep(0.1)

        wave_gen.turn_off(self.waveform_generator, channel=wavegen_ch)

        self.ax1.clear()
        self.ax1.set_title("H–V Calibration")
        self.ax1.set_xlabel("Voltage (V)")
        self.ax1.set_ylabel("H (mT)")
        self.ax1.plot(self.V_cal, self.H_cal)
        self.canvas1.draw()

        self.H_V_slope, _ = np.polyfit(self.V_cal, self.H_cal, 1)
        print(f"H_V slope: {self.H_V_slope}")

    # ── Coil control ─────────────────────────────────────────────────────────

    def run_tx_coil(self):
        voltage  = (1 / self.H_V_slope) * self.tx_H_amplitude
        num_samp = int(self.num_periods * self.sample_rate / self.tx_frequency)

        wave_gen.send_voltage(self.waveform_generator, voltage, self.tx_frequency, self.wavegen_channel)
        self.coil_on = True

        while self.coil_on:
            i_rms       = analyze.get_rms_current(self.daq_current_channel, self.sample_rate,
                                                   num_samp, sensitivity=self.V_I_sensitivity)
            H_magnitude = self.H_I_slope * i_rms * np.sqrt(2)

            if not np.isclose(H_magnitude, self.tx_H_amplitude, atol=0.1):
                voltage = self.tx_H_amplitude / (H_magnitude / voltage)
                wave_gen.send_voltage(self.waveform_generator, voltage,
                                      self.tx_frequency, self.wavegen_channel)
            self.update()
            print(f"H_amplitude (mT_pk): {H_magnitude:.4f}")

    def turn_off(self):
        self.coil_on = False
        wave_gen.turn_off(self.waveform_generator, channel=self.wavegen_channel)

    # ── Stepper motors ───────────────────────────────────────────────────────

    def run_steppers(self):

        xy_angle = self.desired_angle - self.xy_position
        xy_motor_angle = self.xy_ratio * xy_angle

        z_height = self.desired_height - self.z_position
        z_angle = int(z_height / self.z_ratio)

        if z_height == 0:
            cmd = f"0,{xy_motor_angle},{self.rot_time},f0"
        elif xy_angle == 0:
            cmd = f"1,{-z_angle},{self.rot_time},f0"
        else:
            cmd = f"{xy_motor_angle},{-z_angle},{self.rot_time},f1"

        self.send_arduino1(cmd)

        self.z_position = self.desired_height
        self.xy_position = self.desired_angle

    # ── Auto mode ────────────────────────────────────────────────────────────

    def auto_mode(self):

        voltage = (1 / self.H_V_slope) * self.tx_H_amplitude
        num_samp = int(self.num_periods * self.sample_rate / self.tx_frequency)

        wave_gen.send_voltage(self.waveform_generator, voltage,
                              self.tx_frequency, self.wavegen_channel)

        xy_angle = self.desired_angle - self.xy_position
        xy_motor_angle = self.xy_ratio * xy_angle

        z_height = self.desired_height - self.z_position
        z_angle = int(z_height / self.z_ratio)

        if z_height == 0:
            cmd = f"0,{xy_motor_angle},{self.rot_time},f0"
        elif xy_angle == 0:
            cmd = f"1,{-z_angle},{self.rot_time},f0"
        else:
            cmd = f"{xy_motor_angle},{-z_angle},{self.rot_time},f1"

        self.send_arduino1(cmd)

        print("Arduino1 auto command sent:", cmd)

        ax = self.ax1
        ax.clear()
        self.line, = ax.plot([], [])
        ax.set_title("Magnetic Field Through Solenoid (LIVE)")
        ax.set_xlabel("Magnetic Field (mT)")
        ax.set_ylabel("Height (cm)")
        ax.grid(True)

        L        = 0.11
        z_center = (L / 2) * 100
        self.center_line = ax.axhline(z_center, linestyle="--", color="gray")
        self.bottom_line = ax.axhline(0,         linestyle=":",  color="blue")
        self.top_line    = ax.axhline(L * 100,   linestyle=":",  color="blue")
        self.fig1.tight_layout()

        current_height = self.z_position
        start_time     = time.time()
        self.coil_on   = True

        while self.coil_on:
            i_rms   = analyze.get_rms_current(self.daq_current_channel, self.sample_rate,
                                               num_samp, sensitivity=self.V_I_sensitivity)
            elapsed = time.time() - start_time
            if elapsed < self.rot_time:
                height = current_height + (elapsed / self.rot_time) * (self.desired_height - current_height)
            else:
                height        = self.desired_height
                self.coil_on  = False

            zgvals, Bvals = H_plotter.Bfield(i_rms, height)
            self.line.set_data(Bvals, zgvals)
            ax.set_xlim(min(Bvals), max(Bvals))
            ax.set_ylim(0, 40)

            offset = height * 100
            self.center_line.set_ydata([z_center + offset] * 2)
            self.bottom_line.set_ydata([offset] * 2)
            self.top_line.set_ydata([(L * 100) + offset] * 2)

            self.canvas1.draw()
            self.update()

        self.z_position  = self.desired_height
        self.xy_position = self.desired_angle
        wave_gen.turn_off(self.waveform_generator, channel=self.wavegen_channel)

    # ── Frequency tuning ─────────────────────────────────────────────────────

    def find_tuning_frequency(self):
        voltage  = (1 / self.H_V_slope) * self.tx_H_amplitude
        num_samp = int(self.num_periods * self.sample_rate / self.tx_frequency)

        wave_gen.send_voltage(self.waveform_generator, voltage,
                              self.tx_frequency, self.wavegen_channel)
        self.coil_on = True

        direction     = 1
        freq_step     = 500
        max_iter      = 50
        min_step      = 5
        i_rms_prev    = 0.0
        best_freq     = self.tx_frequency
        tolerance     = 1e-4

        for _ in range(max_iter):
            if not self.coil_on:
                break
            wave_gen.send_voltage(self.waveform_generator, voltage,
                                  self.tx_frequency, self.wavegen_channel)
            i_rms_new = analyze.get_rms_current(self.daq_current_channel, self.sample_rate,
                                                 num_samp, sensitivity=self.V_I_sensitivity)

            if i_rms_new > i_rms_prev + tolerance:
                i_rms_prev        = i_rms_new
                best_freq         = self.tx_frequency
                self.tx_frequency += direction * freq_step
            else:
                direction  = -direction
                freq_step /= 2
                if freq_step < min_step:
                    print("Step size too small — stopping.")
                    break
                self.tx_frequency += direction * freq_step

            self.update()
            print(f"Frequency: {self.tx_frequency:.1f} Hz  |  I_rms: {i_rms_prev:.5f} A")

        print(f"Best frequency found: {best_freq:.1f} Hz")

    # ── Save / settings stubs ─────────────────────────────────────────────────

    def save_tx_parameters(self):
        def _get(entry, attr):
            try:
                return float(entry.get())
            except ValueError:
                return float(entry.cget("placeholder_text"))

        self.tx_H_amplitude = _get(self.amplitude_entry, "tx_H_amplitude")
        self.tx_frequency = _get(self.frequency_entry, "tx_frequency")

        try:
            self.waveform_generator = wave_gen.connect_waveform_generator(
                self.wavegen_dropdown.get())
        except Exception:
            self.waveform_generator = wave_gen.find_and_connect_waveform_generator()

        self.daq_current_channel = self.current_channel_dropdown.get()

        operating_mode = self.determine_zmatch(self.tx_frequency)          #Determine best ZMATCH circuit, and set Impedance to ARDUINO
        self.set_impedance(operating_mode['impedance'])

        print(f"Resonant Frequency: {operating_mode['freq']} Hz")
        print(f"Operating Frequency: {self.tx_frequency} Hz")

    def determine_zmatch(self, frequency):
        return min(
            self.operating_modes.values(),
            key=lambda mode: abs(mode["freq"] - frequency)
        )

    def set_impedance(self, z_index):
        if self.arduino2 is None:
            print("Arduino not connected")
            return
        try:
            with self.serial_lock:
                self.arduino2.reset_input_buffer()
                cmd = f"Z{z_index}\n"
                self.arduino2.write(cmd.encode())
                self.arduino2.flush()
                print(f"\nSent: {cmd.strip()}")

                # wait for Arduino response
                reply = self.arduino2.readline().decode(errors="ignore").strip()
                print(f"Arduino replied: {reply}")

        except Exception as e:
            print("Impedance switch failed:", e)

    def open_settings_dropdown(self):
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("220x180")
        win.attributes("-topmost", True)

        frame = ctk.CTkFrame(win)
        frame.pack(fill="both", expand=True)

        sb  = ctk.CTkScrollbar(frame)
        sb.pack(side="right", fill="y")
        lb  = Listbox(frame, height=6, yscrollcommand=sb.set, font=('Arial', 14))
        for opt in ['Save Results', 'Motor Controllers', 'Connection Settings', 'Plot Settings']:
            lb.insert("end", opt)
        lb.pack(fill="both", expand=True)
        sb.configure(command=lb.yview)

        def on_select(event):
            sel = lb.get(lb.curselection())
            win.destroy()
            mapping = {
                'Save Results':        self.save_results,
                'Motor Controllers':   self.motor_controllers_settings,
                'Connection Settings': self.connections_settings,
                'Plot Settings':       self.plot_settings,
            }
            fn = mapping.get(sel)
            if fn:
                threading.Thread(target=fn, daemon=True).start()

        lb.bind("<<ListboxSelect>>", on_select)

    def save_results(self):            pass
    def motor_controllers_settings(self): pass
    def connections_settings(self):    pass
    def plot_settings(self):           pass


if __name__ == "__main__":
    app = App()
    app.mainloop()