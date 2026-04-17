import numpy as np
import json
from collections import defaultdict
import plotly.graph_objects as go
import plotly.io as pio

pio.renderers.default = 'browser'

#currents:
i1, i2, i3, =100,50,-50
alpha = i2/i1
beta = i3/i1

def read_json_data(fname='magnetic_field_data.json'):
    with open(fname, 'r') as f:
        data = json.load(f)

    P = defaultdict(list)  # will hold the unit fields
    grid = defaultdict(list) #will hold all positions of the grid

    for coil in data["unit_fields"]:
        for dim in data["unit_fields"][coil]:
            for dim_data in data["unit_fields"][coil][dim]:
                P[coil, dim].append(dim_data)

    #Getting the positional values (x,y,z):
    for dim in data["grid"]:
        for grid_data in data["grid"][dim]:
            grid[dim].append(grid_data)

    return grid, P

#Let's say that we want the FFL to be located at (any_pos, 0, 10cm) along x:
def get_B_field(Px, Py, Pz, i):
    Bx = i * Px
    By = i * Py
    Bz = i * Pz
    B_field = {
        "Bx": Bx,
        "By": By,
        "Bz": Bz,
    }
    return B_field

def get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3):
    B1 = get_B_field(P1x, P1y, P1z, i1)
    B2 = get_B_field(P2x, P2y, P2z, i2)
    B3 = get_B_field(P3x, P3y, P3z, i3)

    Bx_total = B1["Bx"]+B2["Bx"]+B3["Bx"]
    By_total = B1["By"]+B2["By"]+B3["By"]
    Bz_total = B1["Bz"]+B2["Bz"]+B3["Bz"]

    B_total = {
        "Bx": Bx_total,
        "By": By_total,
        "Bz": Bz_total
    }
    return B_total

def get_B_from_P(P_dict, i1, i2, i3):
    P1x = np.array(P_dict["c1", "u"])
    P2x = np.array(P_dict["c2", "u"])
    P3x = np.array(P_dict["c3", "u"])

    P1y = np.array(P_dict["c1", "v"])
    P2y = np.array(P_dict["c2", "v"])
    P3y = np.array(P_dict["c3", "v"])

    P1z = np.array(P_dict["c1", "w"])
    P2z = np.array(P_dict["c2", "w"])
    P3z = np.array(P_dict["c3", "w"])
    return get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3)

def get_B_mag(Bx, By, Bz):
    B_mag = []
    for n in range(len(Bx)):
        B_mag.append(np.sqrt(Bx[n]**2 + By[n]**2 + Bz[n]**2))
    return np.array(B_mag)

grid_vals, P_vals = read_json_data(fname='magnetic_field_data(6).json')
field_matrix = get_B_from_P(P_vals, i1, i2, i3)

# Convert grid lists and field values to NumPy arrays for easy filtering
x_array = np.array(grid_vals["x"])
y_array = np.array(grid_vals["y"])
z_array = np.array(grid_vals["z"])

# 1. Define the specific X-position for your YZ slice (e.g., 0.0)
target_x = 0

# 2. Create a boolean mask to find indices where x is at the target position
# We use np.isclose instead of '==' to avoid floating point precision issues (e.g., 0.000000001 != 0.0)
mask = np.isclose(x_array, target_x)

# 3. Filter the y, z, and Bz data to only include the points on this slice
y_slice = y_array[mask]
z_slice = z_array[mask]

B_magnitude = get_B_mag(field_matrix["Bx"], field_matrix["By"], field_matrix["Bz"])
B_mag_slice = B_magnitude[mask]

fig = go.Figure(data=go.Contour(
    x=y_slice,  # Horizontal axis
    y=z_slice,  # Vertical axis
    z=B_mag_slice*1e+3, # Field intensity/contour colors
    connectgaps=True # Helps if the filtered grid has any minor gaps
))

fig.show()