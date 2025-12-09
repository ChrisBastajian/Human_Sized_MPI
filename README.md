# Human-Sized MPI Scanner Repository

## Description
This repository contains the software components developed for the human-sized, single-sided Magnetic Particle Imaging (MPI) platform designed for breast-imaging research. The system integrates electromagnetic simulations, coil-driving hardware, current monitoring, stepper-motor motion control, and a graphical user interface (GUI) for real-time operation. The platform serves as an experimental testbed to study magnetostimulation limits and field–frequency behavior in large tissue volumes and to validate the performance of a human-scale single-sided Field-Free Line (FFL) MPI scanner.

The codebase includes:
- Biot–Savart electromagnetic simulations for coil optimization
- Final Tx coil simulation parameters matching the wound coil used in experiments
- Automated RMS current extraction from a Hall-effect current sensor
- Arduino stepper-motor control for coordinated rotation and translation of the coil thanks to a dynamic gantry system
- A full user interface for live coil control, data collection, and system monitoring

---

## Prerequisites
The following software and hardware dependencies are recommended:

### Software
- Python 3.8+
- NumPy, SciPy, Matplotlib
- PySerial (for serial communication with Arduino)
- Tkinter and CustomTkinter (for User Interface)
- Arduino IDE (for stepper motor firmware)

### Hardware
- Human-sized MPI Tx coil (as specified in accompanying publication)
- Rotary union with electrical and water-cooling channels
- ACS712 (50B) Hall-effect current sensor
- NEMA 23 and NEMA 34 stepper motors with controllers
- Arduino microcontroller
- SENIS 3-axis Hall probe (for Tx calibration)

---

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/ChrisBastajian/Human_Sized_MPI
   ```
2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Upload the Arduino firmware located in `/stepper_motors/` to your Arduino using the Arduino IDE.
4. Confirm that the serial port configurations in the Python UI match the Arduino device.

---

## Biot–Savart Simulations
The electromagnetic simulations in this repository were developed to model a helical drive (Tx) coil used to probe the magnetostimulation limits for breast tissue. The design requirement was to achieve at least **20 mT-pp** across a usable field volume, with optimization for frequencies from 5 kHz to 40 kHz. These simulations correspond to the results presented in the attached manuscript.

### efficient_comparison.py
This script evaluates multiple coil configurations, including:
- Series winding configurations
- Parallel winding configurations
- Hybrid configurations (series–parallel)
- Varying number of layers
- Coil height and diameter
- Frequency sweeps up to 40 kHz

The simulation generates comparative plots for field intensity, inductance, voltage requirements, and frequency-dependent attenuation, enabling selection of the optimal coil geometry.

### final_coil_design.py
Contains the full electromagnetic simulation for the final Tx coil parameters that were physically wound and integrated into the MPI scanner. This includes:
- Final 4-layer hybrid winding structure
- Voltage limitations based on the rotary union (1.5 kV RMS)
- Maximum current of 30 A RMS
- Frequency sweep up to 40 kHz
- Magnetic field attenuation vs. distance from the coil

These simulations validated that the final wound coil achieves **>30 mT-pp** at 25 kHz at the coil center, matching the requirements for the testing study.

---

## Current Sensor
The `current_sensor/` directory contains code for acquiring real-time RMS current using the ACS712 50B Hall-effect sensor. Features include:
- Automated RMS calculation from sampled analog data
- Noise filtering
- Scaled output based on sensor sensitivity
- Serial streaming to the UI for visualization and logging

This module is used to verify drive-coil current during experiments and to correlate field intensity with measured current.

---

## Stepper Motors
The `stepper_motors/` directory contains the Arduino firmware used to control both rotational and translational motion of the coil assembly. The system supports:
- Simultaneous or independent motor motion
- Serial commands for speed, direction, homing, and step-size configuration
- Synchronized rotation–translation sequences for scanning routines

The firmware controls:
- A NEMA 34 motor for full coil rotation
- A NEMA 23 motor for vertical translation of the gantry

These motions enable 2D rotational sweeps and 3D positional offsets for full 3D imaging capability.

---

## User Interface
The UI provides a unified control center for driving the Tx coil, monitoring current, and commanding stepper motor movements.

### Core UI Features
**1. Drive Coil Control**
- Set drive frequency
- Adjust amplitude
- Enable/disable the Tx coil
- Real-time current monitoring and magnetic field display

**2. Current Sensor Display**
- Live RMS current reading from ACS712 module
- Filtering and stability indicator
- Logging option for experiment data

**3. Stepper Motor Controls**
- Independent rotation and translation controls
- Simultaneous rotation and translation functionality
- Angle and speed adjustment

---

## Repository Structure
```
Human_Sized_MPI/
│
├── biot_savart_simulations/
│   ├── efficient_comparison.py
│   └── final_coil_design.py
│
├── current_sensor/
│   └──current_sensor.py
│
├── stepper_motors/
│   ├── stepper_control.ino
│   └── serial_protocol.txt
│
├── ui/
│   ├── mpi_ui.py

```

---

## Contact
For inquiries or contributions, please contact me via email: chrisbastajian@gmail.com or through the GitHub profile.
