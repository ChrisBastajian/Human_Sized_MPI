"""
Minimal live current-sensor monitor.

Stripped-down version of the MPI platform app: no waveform generator,
no motor control, no calibration workflow. This GUI does exactly one
thing - reads the current sensor value from the DAQ card and plots it
against time as new readings come in.

Requires `receive_and_analyze.py` (the same module the original app used)
to be importable, since it does the actual DAQ acquisition + RMS current
calculation.
"""

import time
import threading
from collections import deque

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
import matplotlib.pyplot as plt

import receive_and_analyze as analyze

ctk.set_appearance_mode("light_gray")
ctk.set_default_color_theme("dark-blue")


class CurrentMonitorApp(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---- Default acquisition parameters (same defaults as the old app) ----
        self.daq_current_channel = "Dev94/ai1"
        self.sample_rate = 10e3        # Hz - DAQ sample rate per read
        self.samples_per_read = 1000   # samples per acquisition (sets update rate)
        self.sensitivity = 40e-3       # V/A - current sensor sensitivity
        self.time_window = 30.0        # seconds of history kept on screen

        self.acquiring = False
        self.acq_thread = None

        self.times = deque()
        self.currents = deque()
        self.start_time = None

        # ---- Window setup ----
        self.title("Current Sensor Live Monitor")
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{int(screen_w * 0.7)}x{int(screen_h * 0.75)}")

        self._build_controls()
        self._build_plot()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_controls(self):
        frame = ctk.CTkFrame(self, fg_color="gray")
        frame.pack(side="top", fill="x", padx=10, pady=10)

        label_font = ("Arial", 14)

        ctk.CTkLabel(frame, text="DAQ Current Channel", font=label_font).grid(
            row=0, column=0, padx=8, pady=(8, 0)
        )
        self.channel_dropdown = ctk.CTkOptionMenu(
            frame,
            values=["Dev94/ai1", "Dev94/ai0", "Dev1/ai1", "Dev1/ai0",
                    "Dev0/ai0", "Dev0/ai1", "Dev2/ai0", "Dev2/ai1"],
            font=label_font,
        )
        self.channel_dropdown.set(self.daq_current_channel)
        self.channel_dropdown.grid(row=1, column=0, padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Sample Rate [Hz]", font=label_font).grid(
            row=0, column=1, padx=8, pady=(8, 0)
        )
        self.sample_rate_entry = ctk.CTkEntry(frame, font=label_font)
        self.sample_rate_entry.insert(0, str(int(self.sample_rate)))
        self.sample_rate_entry.grid(row=1, column=1, padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Samples per Read", font=label_font).grid(
            row=0, column=2, padx=8, pady=(8, 0)
        )
        self.samples_entry = ctk.CTkEntry(frame, font=label_font)
        self.samples_entry.insert(0, str(self.samples_per_read))
        self.samples_entry.grid(row=1, column=2, padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Sensitivity [V/A]", font=label_font).grid(
            row=0, column=3, padx=8, pady=(8, 0)
        )
        self.sensitivity_entry = ctk.CTkEntry(frame, font=label_font)
        self.sensitivity_entry.insert(0, str(self.sensitivity))
        self.sensitivity_entry.grid(row=1, column=3, padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Time Window [s]", font=label_font).grid(
            row=0, column=4, padx=8, pady=(8, 0)
        )
        self.window_entry = ctk.CTkEntry(frame, font=label_font)
        self.window_entry.insert(0, str(self.time_window))
        self.window_entry.grid(row=1, column=4, padx=8, pady=(0, 8))

        self.start_btn = ctk.CTkButton(
            frame, text="Start", command=self.start_acquisition, font=label_font
        )
        self.start_btn.grid(row=1, column=5, padx=8, pady=(0, 8))

        self.stop_btn = ctk.CTkButton(
            frame, text="Stop", command=self.stop_acquisition, font=label_font
        )
        self.stop_btn.grid(row=1, column=6, padx=8, pady=(0, 8))

        self.clear_btn = ctk.CTkButton(
            frame, text="Clear", command=self.clear_plot, font=label_font
        )
        self.clear_btn.grid(row=1, column=7, padx=8, pady=(0, 8))

        self.reading_lbl = ctk.CTkLabel(
            frame, text="Current: -- A", font=("Arial", 18, "bold")
        )
        self.reading_lbl.grid(row=1, column=8, padx=20, pady=(0, 8))

    def _build_plot(self):
        self.fig = plt.figure(figsize=(10, 6))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Live Current Reading")
        self.ax.set_xlabel("Time [s]")
        self.ax.set_ylabel("Current [A]")
        self.ax.grid(True)
        (self.line,) = self.ax.plot([], [])

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(
            side="top", fill="both", expand=True, padx=10, pady=10
        )

        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()

    # ------------------------------------------------------------------
    # Acquisition control
    # ------------------------------------------------------------------
    def _read_parameters(self):
        self.daq_current_channel = self.channel_dropdown.get()
        try:
            self.sample_rate = float(self.sample_rate_entry.get())
        except ValueError:
            pass
        try:
            self.samples_per_read = int(self.samples_entry.get())
        except ValueError:
            pass
        try:
            self.sensitivity = float(self.sensitivity_entry.get())
        except ValueError:
            pass
        try:
            self.time_window = float(self.window_entry.get())
        except ValueError:
            pass

    def start_acquisition(self):
        if self.acquiring:
            return
        self._read_parameters()
        self.acquiring = True
        self.start_time = time.time()
        self.acq_thread = threading.Thread(target=self._acquisition_loop, daemon=True)
        self.acq_thread.start()

    def stop_acquisition(self):
        self.acquiring = False

    def clear_plot(self):
        self.times.clear()
        self.currents.clear()
        self.line.set_data([], [])
        self.canvas.draw_idle()

    def _acquisition_loop(self):
        """Runs on a background thread so the GUI never freezes while
        waiting on the DAQ card."""
        while self.acquiring:
            try:
                i_rms = analyze.get_rms_current(
                    self.daq_current_channel,
                    self.sample_rate,
                    self.samples_per_read,
                    sensitivity=self.sensitivity,
                )
            except Exception as e:
                print(f"DAQ read failed: {e}")
                self.acquiring = False
                break

            t = time.time() - self.start_time
            self.times.append(t)
            self.currents.append(i_rms)

            while self.times and (t - self.times[0]) > self.time_window:
                self.times.popleft()
                self.currents.popleft()

            # Hand the update back to the main thread - Tk is not thread-safe.
            self.after(0, self._update_plot, i_rms)

    def _update_plot(self, latest_value):
        self.reading_lbl.configure(text=f"Current: {latest_value:.4f} A")
        self.line.set_data(list(self.times), list(self.currents))

        if self.times:
            self.ax.set_xlim(self.times[0], max(self.times[-1], self.times[0] + 1))
        if self.currents:
            lo, hi = min(self.currents), max(self.currents)
            pad = max((hi - lo) * 0.1, 1e-6)
            self.ax.set_ylim(lo - pad, hi + pad)

        self.canvas.draw_idle()

    def _on_close(self):
        self.acquiring = False
        self.destroy()


if __name__ == "__main__":
    app = CurrentMonitorApp()
    app.mainloop()