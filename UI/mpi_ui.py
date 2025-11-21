import matplotlib.pyplot as plt
import pyvisa
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

ctk.set_appearance_mode("light_gray")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Default values:
        self.waveform_generator = wave_gen.find_and_connect_waveform_generator()
        self.H_V_slope = None #mT/V
        self.H_I_slope = 419.8 *1e-3 # in mT/A
        self.V_I_sensitivity = 40 * 1e-3 #V/A
        self.tx_H_amplitude = 1.0 #mT
        self.tx_frequency = 1000 #making 1kHz the standard operating frequency for audio amp limit
        self.wavegen_channel = 1 #channel of waveform generator
        self.daq_trigger_channel: str = "/Dev1/pfi0"
        self.daq_current_channel: str = "Dev1/ai1"
        self.sample_rate = 10e+3
        self.num_periods = 100 #default of 100 periods
        self.H_cal = None
        self.V_cal = None
        self.coil_on = False

        self.serial_port = "COM4"
        self.xy_position = 0 #degrees
        self.z_position = 0 #meters
        self.xy_ratio = 2 #2:1 gear ratio used
        self.z_ratio = 10 * 1e-3 / 360 #10 mm for 360 degrees
        self.desired_height = 0.05
        self.desired_angle = 1080
        self.rot_time = 10 #seconds

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

        #Controls Parameters:
        self.controls_frame = ctk.CTkFrame(self, height=int(self.height *(5/12)), width=int(self.width*(17/32)),
                                           fg_color='gray')
        self.controls_frame.place(x=self.width//64, y=self.height*(3/32), anchor="nw")

        self.controls_title = ctk.CTkLabel(self, text="Controls Parameters",
                                           font=('Times New Roman', int(self.height * 0.04)),
                                           bg_color="gray")
        self.controls_title.place(x=self.width*(3/16), y=self.height*(4/32))

        self.xy_label = ctk.CTkLabel(self, text="XY Rotation Control",
                                     font=('Times New Roman', int(self.height * 0.03)),
                                     bg_color="gray")
        self.xy_label.place(x=self.width //8, y=self.height//4, anchor="center")
        self.xy_angle_lbl = ctk.CTkLabel(self,text="Desired turns [turns]",
                                   font=('Arial', int(self.height * 0.018)),
                                         bg_color="gray")
        self.xy_angle_lbl.place(x=self.width//16, y=self.height//3, anchor="center")
        self.xy_entry = ctk.CTkEntry(self, placeholder_text=f"{self.desired_angle * 1/360}",
                                         font=('Arial', int(self.height * 0.018)),
                                     bg_color="gray")
        self.xy_entry.configure(state="readonly")
        self.xy_entry.place(x=self.width/6, y=self.height/3, anchor="center")
        self.xy_slider = ctk.CTkSlider(
            self,
            from_=0,
            to=3,
            number_of_steps=6,
            command=self.xy_slider_callback
        )
        self.xy_slider.set(self.desired_angle)
        self.xy_slider.place(x=self.width*(7/64), y=self.height * (25 / 64), anchor="center")

        self.z_label = ctk.CTkLabel(self, text="Z Translation Control", font=('Times New Roman', int(self.height * 0.03)),
                                    bg_color="gray")
        self.z_label.place(x=self.width*(7/16), y=self.height//4, anchor="center")
        self.z_height_lbl = ctk.CTkLabel(self, text="Desired Z Height [mm]",
                                         font=('Arial', int(self.height * 0.018)),
                                         bg_color="gray")
        self.z_height_lbl.place(x=self.width*(3/8), y=self.height//3, anchor="center")
        self.z_entry = ctk.CTkEntry(self, placeholder_text=f"{self.desired_height*1e+3}",
                                    font=('Arial', int(self.height * 0.018)),
                                    bg_color="gray")
        self.z_entry.configure(state="readonly") #need to do this on a new line to load value first
        self.z_entry.place(x=self.width/2, y=self.height/3, anchor="center")
        self.z_slider = ctk.CTkSlider(
            self,
            from_=0,
            to=250,
            number_of_steps=250,
            command=self.z_slider_callback
        )
        self.z_slider.set(self.desired_height * 1e+3)
        self.z_slider.place(x=self.width*(7/16), y=self.height * (25 / 64), anchor="center")

        self.time_lbl = ctk.CTkLabel(self, text="Time [s]", font=('Arial', int(self.height * 0.018)),
                                     bg_color="gray")
        self.time_lbl.place(x=self.width*(3/16), y=self.height*(7/16), anchor="center")
        self.time_entry = ctk.CTkEntry(self, placeholder_text=f"{self.rot_time}",
                                       font=('Arial', int(self.height * 0.018)),
                                       bg_color="gray")
        self.time_entry.place(x=self.width*(9/32), y=self.height*(7/16), anchor="center")
        self.time_entry.bind("<KeyRelease>", self.time_entry_update)

        #Tx Coil Parameters:
        self.tx_frame = ctk.CTkFrame(self, height=int(self.height *(4/12)), width=int(self.width*(17/32)),
                                           fg_color='gray')
        self.tx_frame.place(x=self.width//64, y=self.height*(28/32), anchor="sw")

        self.tx_frame.title = ctk.CTkLabel(self, text="Drive Coil Parameters",
                                           font=('Times New Roman', int(self.height * 0.04)),
                                           bg_color="gray")
        self.tx_frame.title.place(x=self.width*(3/16), y=self.height*(18/32))

        self.tx_frame.amplitude_lbl = ctk.CTkLabel(self, text="Amplitude [mT_pk]",
                                                   font=('Arial', int(self.height * 0.018)),
                                                   bg_color="gray")
        self.tx_frame.amplitude_lbl.place(x=self.width //16, y=self.height*(21/32), anchor="center")
        self.tx_frame.amplitude_entry = ctk.CTkEntry(self, placeholder_text=f"{self.tx_H_amplitude}",
                                       font=('Arial', int(self.height * 0.018)),
                                       bg_color="gray")
        self.tx_frame.amplitude_entry.place(x=self.width*(1/6), y=self.height*(21/32), anchor="center")

        self.tx_frame.frequency_lbl = ctk.CTkLabel(self, text="Frequency [Hz]",
                                                   font=('Arial', int(self.height * 0.018)),
                                                   bg_color="gray")
        self.tx_frame.frequency_lbl.place(x=self.width//16, y=self.height*(23/32), anchor="center")
        self.tx_frame.frequency_entry = ctk.CTkEntry(self, placeholder_text=f"{self.tx_frequency}",
                                                     font=('Arial', int(self.height * 0.018)),
                                                     bg_color="gray")
        self.tx_frame.frequency_entry.place(x=self.width*(1/6), y=self.height*(23/32), anchor="center")

        self.tx_frame.current_channel_lbl = ctk.CTkLabel(self, text="Current DAQ Channel",
                                                         font=('Arial', int(self.height * 0.018)),
                                                         bg_color="gray")
        self.tx_frame.current_channel_lbl.place(x=self.width*(3/8), y=self.height*(21/32), anchor="center")
        self.tx_frame.current_channel_dropdown = ctk.CTkOptionMenu(self,
                                                                   values =["Dev1/ai1", "Dev0/ai0",
                                                                            "Dev0/ai1", "Dev1/ai0",
                                                                            "Dev2/ai0", "Dev2/ai1"],
                                                                   font=('Arial', int(self.height * 0.018)),
                                                                   bg_color="gray")
        self.tx_frame.current_channel_dropdown.place(x=self.width*(1/2), y=self.height*(21/32), anchor="center")
        self.tx_frame.wavegen_lbl = ctk.CTkLabel(self, text="Wave Generator Channel",
                                                 font=('Arial', int(self.height * 0.018)),
                                                 bg_color="gray")
        self.tx_frame.wavegen_lbl.place(x=self.width*(3/8), y=self.height*(23/32), anchor="center")
        self.tx_frame.wavegen_dropdown = ctk.CTkOptionMenu(self,
                                                   width=self.tx_frame.current_channel_dropdown.cget("width"),
                                                   dynamic_resizing=False,
                                                   values=pyvisa.ResourceManager().list_resources(),
                                                   font=('Arial', int(self.height * 0.018)),
                                                   bg_color="gray"
                                                   )
        self.tx_frame.wavegen_dropdown.place(x=self.width*(1/2), y=self.height*(23/32), anchor="center")

        #Save Button for drive coil parameters:
        self.tx_frame.save_btn = ctk.CTkButton(self, text="Save Parameters",
                                               font=('Arial', int(self.height * 0.018)),
                                               command=self.save_tx_parameters,
                                               bg_color="gray")
        self.tx_frame.save_btn.place(x=self.width*(9/32), y=self.height*(25/32), anchor="center")

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
        elif button == 3:
            self.run_tx_coil()
        elif button == 4:
            self.turn_off()

    # Z Slider callback
    def z_slider_callback(self, value):
        value_int = int(value)
        self.z_entry.configure(state="normal")
        self.z_entry.delete(0, "end")
        self.z_entry.insert(0, str(value_int))
        self.desired_height = value_int*1e-3
        self.z_entry.configure(state="readonly")

    #XY slider callback:
    def xy_slider_callback(self, value):
        value = value
        angle = int(value * 360)
        self.xy_entry.configure(state="normal")
        self.xy_entry.delete(0, "end")
        self.xy_entry.insert(0, str(value))
        self.desired_angle = angle
        self.xy_entry.configure(state="readonly")

    #Time entry callback:
    def time_entry_update(self, event=None):
        value = self.time_entry.get()
        try:
            self.rot_time = float(value)
        except ValueError:
            self.time_entry.configure(placeholder_text=f"{self.rot_time}")
            pass #in case input is not a number use the previous time

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

            H_magnitude = self.H_I_slope * i_rms * np.sqrt(2) #This is the amplitude (peak)

            self.H_cal.append(H_magnitude)
            self.V_cal.append(v_amplitude)

            v_amplitude += 0.05
            time.sleep(0.1)

        wave_gen.turn_off(self.waveform_generator, channel=wavegen_channel)
        #Plotting:
        self.ax1.clear()
        self.ax1.set_title("H_V Calibrated", fontsize=11)
        self.ax1.set_xlabel("V", fontsize=10)
        self.ax1.set_ylabel("H", fontsize=10)

        self.ax1.plot(self.V_cal, self.H_cal)

        self.canvas1.draw()

        self.H_V_slope, _ = np.polyfit(self.V_cal, self.H_cal, 1)
        print(self.H_V_slope)

    def run_tx_coil(self):
        H_amplitude = self.tx_H_amplitude
        coefficient = self.H_V_slope #mT/V
        frequency = self.tx_frequency
        instr = self.waveform_generator
        channel = self.wavegen_channel

        voltage = (1/coefficient) * H_amplitude

        #Daq parameters:
        current_channel = self.daq_current_channel
        sample_rate = self.sample_rate
        num_periods = int(self.num_periods)
        samps_per_period = sample_rate / self.tx_frequency
        num_samples = int(num_periods * samps_per_period)

        #turn the channel on:
        wave_gen.send_voltage(instr, voltage, frequency, channel)
        self.coil_on = True

        #Loop to collect current:
        while self.coil_on:
            # get the current:
            i_rms = analyze.get_rms_current(current_channel, sample_rate, num_samples,
                                            sensitivity=self.V_I_sensitivity)

            H_magnitude = self.H_I_slope * i_rms * np.sqrt(2)  # This is the actual amplitude (peak)

            self.update()
            print(f"H_amplitude (mT_pk): {H_magnitude}")

    def turn_off(self):
        self.coil_on = False
        wave_gen.turn_off(self.waveform_generator, channel=self.wavegen_channel)

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
        self.desired_height = 0.02 #20 mm
        self.desired_angle = 0
        self.rot_time = 2 #seconds

    def run_steppers(self):
        ser = serial.Serial(self.serial_port, 9600, timeout=1)
        time.sleep(2)  # allow Arduino reset to finish

        current_height = self.z_position
        current_angle = self.xy_position

        xy_angle = self.desired_angle - current_angle
        xy_motor_angle = self.xy_ratio * xy_angle

        z_height = self.desired_height - current_height
        print(f"z_height: {z_height}")
        z_angle = int(z_height / self.z_ratio)

        # send commands
        if z_height == 0:
            ser.write(f"0,{xy_motor_angle},{self.rot_time},f0\n".encode())

        elif xy_angle == 0:
            ser.write(f"1,{-z_angle},{self.rot_time},f0\n".encode())

        else:
            ser.write(f"{xy_motor_angle},{-z_angle},{self.rot_time},f1\n".encode())

        # read response
        raw = ser.readline()
        message = raw.decode("utf-8", errors="ignore").strip()
        print("Arduino replied:", message)

        if message:
            self.z_position = self.desired_height
            self.xy_position = self.desired_angle

        ser.close()

    def save_tx_parameters(self):
        #Retrieving all the parameters:
        try:
            self.tx_H_amplitude = float(self.tx_frame.amplitude_entry.get())
        except ValueError:
            self.tx_H_amplitude = float(self.tx_frame.amplitude_entry.cget("placeholder_text")) #in case it hasn't been changed
        try:
            self.tx_frequency = float(self.tx_frame.frequency_entry.get())
        except ValueError:
            self.tx_frequency = float(self.tx_frame.frequency_entry.cget("placeholder_text"))
        try:
            connection_channel = self.tx_frame.wavegen_dropdown.get()
            self.waveform_generator = wave_gen.connect_waveform_generator(connection_channel)
        except ValueError:
            self.waveform_generator = wave_gen.find_and_connect_waveform_generator() #try to find something else
        try:
            self.daq_current_channel = self.tx_frame.current_channel_dropdown.get()
        except ValueError:
            print(f"daq_current_channel fetch failed") # this should never happen
        #print(self.tx_H_amplitude, self.tx_frequency, self.daq_current_channel)

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