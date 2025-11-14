import matplotlib.pyplot as plt
import numpy as np
import time
import customtkinter as ctk
from tkinter import Listbox
import threading
import wave_gen
import receive_and_analyze as analyze
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))

root_dir = os.path.abspath(os.path.join(current_dir, ".."))
stepper_dir = os.path.join(root_dir, "Stepper_Motors")
sys.path.append(stepper_dir)
import motor_controller

ctk.set_appearance_mode("light_gray")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Default values:
        self.waveform_generator = wave_gen.find_and_connect_waveform_generator()
        self.H_V_slope = None
        self.H_I_slope = 419.8 *1e-3 # in mT/A
        self.V_I_sensitivity = 40 * 1e-3 #V/A
        self.tx_frequency = 1000 #making 1kHz the standard operating frequency for audio amp limit
        self.wavegen_channel = 1 #channel of waveform generator
        self.daq_trigger_channel: str = "/Dev1/pfi0"
        self.daq_current_channel: str = "Dev1/ai1"
        self.sample_rate = 10e+3
        self.num_periods = 100 #default of 100 periods
        self.H_cal = None
        self.V_cal = None

        self.serial_port = "COM5"
        self.xy_position = 0 #degrees
        self.z_position = 0 #meters
        self.xy_ratio = 2 #2:1 gear ratio used
        self.z_ratio = 10 * 1e-3 / 360 #10 mm for 360 degrees
        self.desired_height = 0
        self.desired_angle = 0
        self.rot_time = 2 #seconds

        #Initiating Application:
        self.title(f"MPI Platform App")
        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()

        self.geometry(f"{self.width}x{self.height}")
        self.configure(fg="#333333")

        #Title Bar:
        self.title_bar = ctk.CTkFrame(self, height=self.height // 18, width=self.width, corner_radius=0,
                                      fg_color='gray')
        self.title_bar.place(x=self.width // 2, y=self.height // 36, anchor="center")

        # Button properties
        btn_width = int(self.width * 0.10)  # Slightly wider to accommodate longer labels
        btn_height = int(self.height * 0.04)
        btn_y = self.height // 36

        title_bar_names = ["Settings", "Calibrate", "Run Steppers", "Run Coil", "Stop", "Auto Mode"]
        self.title_bar.buttons = []

        # Total number of buttons (including Settings)
        num_buttons = len(title_bar_names)
        total_spacing_width = self.width * 0.8  # spread buttons across 80% of window
        start_x = (self.width - total_spacing_width) / 2
        btn_spacing = total_spacing_width / (num_buttons - 1)

        for btn in range(num_buttons):
            self.title_bar.buttons.append(ctk.CTkButton(self.title_bar, text=title_bar_names[btn],
                                                        font=('Arial', int(self.height * 0.018)),
                                                        command=lambda b=btn: self.title_bar_command(b),
                                                        height=btn_height, width=btn_width))
            self.title_bar.buttons[btn].place(x=start_x + btn_spacing*btn, y=btn_y, anchor="center")

        #Need two Figures:
        x_fig = 6
        y_fig = 4

        self.fig1 = plt.figure(figsize=(x_fig, y_fig))
        self.ax1 = self.fig1.add_subplot(111)

        self.fig2 = plt.figure(figsize=(x_fig, y_fig))
        self.ax2 = self.fig2.add_subplot(111)

        x_canvas = [int(self.width * 0.95), int(self.width * 0.95)]
        y_canvas = [int(self.height * 0.32), int(self.height * 0.85)]

        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self)
        self.canvas1.get_tk_widget().place(x=x_canvas[0], y=y_canvas[0], anchor='center')

        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self)
        self.canvas2.get_tk_widget().place(x=x_canvas[1], y=y_canvas[1], anchor='center')

        #For each canvas:
        # For each canvas
        self.toolbar1 = NavigationToolbar2Tk(self.canvas1, self)
        self.toolbar1.update()
        self.toolbar1.place(x=x_canvas[0]+int(self.width *0.075), y=y_canvas[0] - int(self.height * 0.21), anchor='center')

        self.toolbar2 = NavigationToolbar2Tk(self.canvas2, self)
        self.toolbar2.update()
        self.toolbar2.place(x=x_canvas[1]+int(self.width *0.075), y=y_canvas[1] - int(self.height * 0.21), anchor='center')

        # Add a button for each figure to open the plot in a new window
        self.add_plot_button(self.fig1, x_canvas[0]-self.width*0.08, y_canvas[0]+self.height*0.15)
        self.add_plot_button(self.fig2, x_canvas[1]-self.width*0.08, y_canvas[1]+self.height*0.04)

        #Clear Comparison Button:
        self.clear_plot_button(self.ax1, x_canvas[0]-self.width*0.15, y_canvas[0]+self.height*0.15)
        self.clear_plot_button(self.ax2, x_canvas[1]-self.width*0.15, y_canvas[1]+self.height*0.04)

    def clear_plot_button(self, ax, x, y):
        button = ctk.CTkButton(self, text="Clear", command=lambda: self.clear_plot(ax), width=0)
        button.place(x=x, y=y, anchor="center")

    def clear_plot(self, ax):
        ax.clear()
        ax.figure.canvas.draw_idle()

    def add_plot_button(self, figure, x, y):
        button = ctk.CTkButton(self, text="View Full Plot", command=lambda: self.open_plot_window(figure), width=0)
        button.place(x=x, y=y, anchor="center")

    def open_plot_window(self, figure):
        # Create a new top-level window with customtkinter
        new_window = ctk.CTkToplevel(self)
        new_window.title("Full Plot")
        new_window.geometry(f"{self.width}x{self.height}")
        new_window.attributes("-topmost", True)

        # Create a CTkFrame for better layout management
        frame = ctk.CTkFrame(new_window, bg_color="gray", fg_color="gray", width=self.width, height=self.height)
        frame.pack(fill="both", expand=True)

        # Create a new figure for the new window (copy the content from the original figure)
        new_figure = plt.Figure(figsize=figure.get_size_inches())
        new_ax = new_figure.add_subplot(111)

        # Copy plot data (lines, labels, etc.)
        for line in figure.axes[0].lines:
            new_ax.plot(line.get_xdata(), line.get_ydata(), label=line.get_label())

        # Copy axis properties
        new_ax.set_xlabel(figure.axes[0].get_xlabel())
        new_ax.set_ylabel(figure.axes[0].get_ylabel())
        new_ax.set_title(figure.axes[0].get_title())

        # Create a canvas to render the new figure in the new window
        canvas = FigureCanvasTkAgg(new_figure, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        # Create and pack toolbar below the canvas
        toolbar = NavigationToolbar2Tk(canvas, frame)
        toolbar.update()
        toolbar.pack(side="bottom", fill="x")

    def title_bar_command(self, button):
        print(button)
        if button == 0: #settings
            self.open_settings_dropdown()
        elif button == 1: #calibrate
            self.calibrateH_V()
        elif button == 2: #run steppers
            self.run_steppers()

    def calibrateH_V(self):
        self.H_cal = []
        self.V_cal = []

        v_amplitude = 0 #start at 0
        sample_rate = self.sample_rate #no need for more since the f_max = 40kHz
        num_periods = int(self.num_periods)
        samps_per_period = sample_rate/self.tx_frequency
        num_samples = int(num_periods * samps_per_period)

        #Channels and communication parameters:
        daq_trigger = self.daq_trigger_channel
        current_channel = self.daq_current_channel

        #Waveform generator parameters:
        frequency = float(self.tx_frequency)
        wavegen_channel =int(self.wavegen_channel)

        for l in range(49):
            wave_gen.send_voltage(self.waveform_generator, v_amplitude, frequency, wavegen_channel)

            if v_amplitude > 3:
                v_amplitude = 0

            #get the current:
            i_rms = analyze.get_rms_current(current_channel, sample_rate, num_samples,
                                            sensitivity = self.V_I_sensitivity)

            H_magnitude = self.H_I_slope * i_rms * np.sqrt(2)

            self.H_cal.append(H_magnitude)
            self.V_cal.append(v_amplitude)

            v_amplitude += 0.05
            time.sleep(0.1)

        #wave_gen.turn_off(self.waveform_generator, channel=wavegen_channel)
        #Plotting:
        self.ax1.clear()
        self.ax1.set_title("H_V Calibrated", fontsize=11)
        self.ax1.set_xlabel("V", fontsize=10)
        self.ax1.set_ylabel("H", fontsize=10)

        self.ax1.plot(self.V_cal, self.H_cal)

        self.canvas1.draw()

        self.H_V_slope, _ = np.polyfit(self.V_cal, self.H_cal, 1)
        print(self.H_V_slope)

    def open_settings_dropdown(self):
        dropdown_window = ctk.CTkToplevel(self)
        dropdown_window.title("Select Option")
        dropdown_window.geometry("200x150")

        dropdown_window.attributes("-topmost", True)
        frame = ctk.CTkFrame(dropdown_window)
        frame.pack(fill="both", expand=True)

        scrollbar = ctk.CTkScrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        listbox = Listbox(frame, height=6, yscrollcommand=scrollbar.set, font=('Arial', 14))
        options = ['Save Results', 'Motor Controllers', 'Connections Settings', 'Plot Settings']

        for option in options:
            listbox.insert("end", option)
        listbox.pack(fill="both", expand=True)
        scrollbar.configure(command=listbox.yview)

        #All functions:
        def on_select(event):
            selected = listbox.get(listbox.curselection())
            dropdown_window.destroy()
            if selected == "Save Results":
                threading.Thread(target=self.save_results).start()
            elif selected == "Motor Controllers":
                threading.Thread(target=self.motor_controllers_settings).start()
            elif selected == "Connection Settings":
                threading.Thread(target=self.connections_settings).start()
            elif selected == "Plot Settings":
                threading.Thread(target=self.plot_settings).start()
        listbox.bind("<<ListboxSelect>>", on_select)

    def initialize_parameters(self):
        #Starting with detecting the waveform generator;
        self.waveform_generator = wave_gen.find_and_connect_waveform_generator()
        self.wavegen_channel = 1

        #Waveform Generator parameters:
        self.tx_frequency = 1000 #making 1kHz the standard operating frequency for audio amp limit
        self.num_periods = 100 #default of 100 periods

        #Daq card parameters:
        self.daq_current_channel = "Dev1/ai0"
        self.daq_trigger_channel = "/Dev1/pfi0"
        self.sample_rate = 10e+3
        self.num_periods = 100 #default of 100 periods

        #Calibration data:
        self.H_V_slope = None
        self.H_I_slope = 419.8e-3 #mT/A

        #motors info:
        self.serial_port = "COM1"
        self.xy_position = 0 #degrees
        self.z_position = 0 #meters
        self.xy_ratio = 2 #2:1 gear ratio used
        self.z_ratio = 10 * 1e-3 / 360 #10 mm for 360 degrees
        self.desired_height = 0
        self.desired_angle = 0
        self.rot_time = 2 #seconds

    def run_steppers(self):
        #Current Steppers Parameters
        current_height = self.z_position
        current_angle = self.xy_position
        x_y_ratio = self.xy_ratio
        z_ratio = self.z_ratio

        #Expected Angle:
        desired_angle = self.desired_angle
        desired_height = self.desired_height

        #computing required angles for each motor:
        xy_angle = desired_angle - current_angle
        xy_motor_angle = self.xy_ratio * xy_angle
        z_height = desired_height - current_height
        z_angle = 360 * z_height/z_ratio

        #send_data to serial:
        if desired_height == current_height:
            motor_controller.continuous_stepper_rotation(rot_time=self.rot_time, angle=xy_motor_angle,
                                                         stepper_number=0, usb_port = self.serial_port)
        if desired_angle == current_angle:
            motor_controller.continuous_stepper_rotation(rot_time = self.rot_time, angle=z_angle,
                                                         stepper_number=1, usb_port = self.serial_port)
        elif desired_height != current_height and desired_angle != current_angle:
            motor_controller.continuous_double_rotation(rot_time=self.rot_time, angle_xy=xy_motor_angle,
                                                       angle_z = z_angle, usb_port = 'COM1')
        #Checking if it worked:
        message = motor_controller.read_serial(port = self.serial_port, baudrate=9600)
        if message is not None: #success
            self.z_position = desired_height
            self.xy_position = desired_angle

    def save_results(self):
        pass
    def motor_controllers_settings(self):
        pass
    def connections_settings(self):
        pass
    def plot_settings(self):
        pass


if __name__ == "__main__":
    app = App()
    app.mainloop()