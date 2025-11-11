import matplotlib.pyplot as plt
import numpy as np
import time
import customtkinter as ctk
from tkinter import Listbox, filedialog
import threading
import receive_and_analyze as analyze

ctk.set_appearance_mode("light_gray")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def title_bar_command(self, button):
        print(button)
        if button == 0: #settings
            self.open_settings_dropdown()

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