import numpy as np
import json
from collections import defaultdict
import plotly.graph_objects as go
import plotly.io as pio
from scipy.interpolate import RegularGridInterpolator

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

def get_current_ratios(P1y, P1z, P2y, P2z, P3y, P3z):
    # the x-component is along the FFL
    # B(rffl) = P1(rffl) + alpha * P2(rffl) + beta * P3(rffl)
    #0 = P1y + alpha * P2y + beta * P3y
    #0 = P1z + alpha * P2z + beta * P3z
    A = np.array([[P2y, P3y], [P2z, P3z]])
    B = np.array([-P1y, -P1z]) #since we solve with constants on the other side of the equation...
    return np.linalg.solve(A, B) #outputs alpha, beta

def get_P(P_dict):
    P1x = np.array(P_dict["c1", "u"])
    P2x = np.array(P_dict["c2", "u"])
    P3x = np.array(P_dict["c3", "u"])

    P1y = np.array(P_dict["c1", "v"])
    P2y = np.array(P_dict["c2", "v"])
    P3y = np.array(P_dict["c3", "v"])

    P1z = np.array(P_dict["c1", "w"])
    P2z = np.array(P_dict["c2", "w"])
    P3z = np.array(P_dict["c3", "w"])
    return P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z

grid_vals, P_vals = read_json_data(fname='magnetic_field_data(6).json')
#field_matrix = get_B_from_P(P_vals, i1, i2, i3)
P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z = get_P(P_vals)

#Setting position of FFL at (0, 5, 3) cm:
x_array = np.array(grid_vals["x"])
y_array = np.array(grid_vals["y"])
z_array = np.array(grid_vals["z"])

target_x = 0
mask = np.isclose(x_array, target_x)

#Filter the y, z, and Bz data to only include the points on this slice
y_slice = y_array[mask]
z_slice = z_array[mask]

target_y = 0.05102041
target_z = 0.02857143

mask2 = np.isclose(y_slice, target_y)
z_line = z_slice[mask2] #gives back one line

P1x_slice = P1x[mask]
P2x_slice = P2x[mask]
P3x_slice = P3x[mask]
P1y_slice = P1y[mask]
P2y_slice = P2y[mask]
P3y_slice = P3y[mask]
P1z_slice = P1z[mask]
P2z_slice = P2z[mask]
P3z_slice = P3z[mask]

P1x_line = P1x_slice[mask2]
P2x_line = P2x_slice[mask2]
P3x_line = P3x_slice[mask2]
P1y_line = P1y_slice[mask2]
P2y_line = P2y_slice[mask2]
P3y_line = P3y_slice[mask2]
P1z_line = P1z_slice[mask2]
P2z_line = P2z_slice[mask2]
P3z_line = P3z_slice[mask2]

#third mask to find z:
mask3 = np.isclose(z_line, target_z)

P1x_point = P1x_line[mask3]
P2x_point = P2x_line[mask3]
P3x_point = P3x_line[mask3]
P1y_point = P1y_line[mask3]
P2y_point = P2y_line[mask3]
P3y_point = P3y_line[mask3]
P1z_point = P1z_line[mask3]
P2z_point = P2z_line[mask3]
P3z_point = P3z_line[mask3]

#Now get the alpha and beta values:
alpha, beta = get_current_ratios(P1y_point[0], P1z_point[0], P2y_point[0], P2z_point[0], P3y_point[0], P3z_point[0])
print(alpha, beta)

#Computing I2 and I3:
I1 = 25
I2 = alpha*I1
I3 = beta*I1

field_matrix = get_B_from_P(P_vals, I1, I2, I3)

B_magnitude = get_B_mag(field_matrix["Bx"], field_matrix["By"], field_matrix["Bz"])
B_mag_slice = B_magnitude[mask]

fig = go.Figure(data=go.Contour(
    x=y_slice,  # Horizontal axis
    y=z_slice,  # Vertical axis
    z=B_mag_slice*1e+3, # Field intensity/contour colors
    connectgaps=True # Helps if the filtered grid has any minor gaps
))

fig.show()