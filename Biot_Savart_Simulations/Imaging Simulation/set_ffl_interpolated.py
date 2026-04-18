import numpy as np
import json
from collections import defaultdict
import plotly.graph_objects as go
import plotly.io as pio
from scipy.interpolate import RegularGridInterpolator

pio.renderers.default = 'browser'

def read_json_data(fname='magnetic_field_data.json'):
    with open(fname, 'r') as f:
        data = json.load(f)

    P = defaultdict(list)
    grid = defaultdict(list)

    for coil in data["unit_fields"]:
        for dim in data["unit_fields"][coil]:
            for dim_data in data["unit_fields"][coil][dim]:
                P[coil, dim].append(dim_data)

    for dim in data["grid"]:
        for grid_data in data["grid"][dim]:
            grid[dim].append(grid_data)

    return grid, P

def get_B_field(Px, Py, Pz, i):
    return {"Bx": i * Px, "By": i * Py, "Bz": i * Pz}

def get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3):
    B1 = get_B_field(P1x, P1y, P1z, i1)
    B2 = get_B_field(P2x, P2y, P2z, i2)
    B3 = get_B_field(P3x, P3y, P3z, i3)

    return {
        "Bx": B1["Bx"]+B2["Bx"]+B3["Bx"],
        "By": B1["By"]+B2["By"]+B3["By"],
        "Bz": B1["Bz"]+B2["Bz"]+B3["Bz"]
    }

def get_B_from_P(P_dict, i1, i2, i3):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])
    return get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3)

def get_B_mag(Bx, By, Bz):
    return np.sqrt(np.array(Bx)**2 + np.array(By)**2 + np.array(Bz)**2)

def get_current_ratios(P1y, P1z, P2y, P2z, P3y, P3z):
    A = np.array([[P2y, P3y], [P2z, P3z]])
    B = np.array([-P1y, -P1z])
    return np.linalg.solve(A, B)

def get_P(P_dict):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])
    return P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z

def build_interpolator(flat_array, nx, ny, nz, ix, iy, iz):
    grid_3d = np.zeros((nx, ny, nz))
    grid_3d[ix, iy, iz] = flat_array
    return RegularGridInterpolator((x_coords, y_coords, z_coords), grid_3d, method='linear', bounds_error=False, fill_value=None)

grid_vals, P_vals = read_json_data(fname='magnetic_field_data(6).json')
P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z = get_P(P_vals)

x_array = np.array(grid_vals["x"])
y_array = np.array(grid_vals["y"])
z_array = np.array(grid_vals["z"])

x_coords = np.unique(x_array)
y_coords = np.unique(y_array)
z_coords = np.unique(z_array)

ix = np.searchsorted(x_coords, x_array)
iy = np.searchsorted(y_coords, y_array)
iz = np.searchsorted(z_coords, z_array)

nx, ny, nz = len(x_coords), len(y_coords), len(z_coords)

interp_P1y = build_interpolator(P1y, nx, ny, nz, ix, iy, iz)
interp_P1z = build_interpolator(P1z, nx, ny, nz, ix, iy, iz)
interp_P2y = build_interpolator(P2y, nx, ny, nz, ix, iy, iz)
interp_P2z = build_interpolator(P2z, nx, ny, nz, ix, iy, iz)
interp_P3y = build_interpolator(P3y, nx, ny, nz, ix, iy, iz)
interp_P3z = build_interpolator(P3z, nx, ny, nz, ix, iy, iz)

target_pos = (0, 0.025, 0.05)
P1y_point = interp_P1y([target_pos])[0]
P1z_point = interp_P1z([target_pos])[0]
P2y_point = interp_P2y([target_pos])[0]
P2z_point = interp_P2z([target_pos])[0]
P3y_point = interp_P3y([target_pos])[0]
P3z_point = interp_P3z([target_pos])[0]

alpha, beta = get_current_ratios(P1y_point, P1z_point, P2y_point, P2z_point, P3y_point, P3z_point)
print("Alpha:", alpha, "Beta:", beta)

I1 = 25
I2 = alpha * I1
I3 = beta * I1

field_matrix = get_B_from_P(P_vals, I1, I2, I3)

interp_Bx = build_interpolator(field_matrix["Bx"], nx, ny, nz, ix, iy, iz)
interp_By = build_interpolator(field_matrix["By"], nx, ny, nz, ix, iy, iz)
interp_Bz = build_interpolator(field_matrix["Bz"], nx, ny, nz, ix, iy, iz)

#Creating a dense grid for Y-Z slice
fine_y = np.linspace(y_coords.min(), y_coords.max(), 1000)
fine_z = np.linspace(z_coords.min(), z_coords.max(), 1000)
YY, ZZ = np.meshgrid(fine_y, fine_z, indexing='ij')
XX = np.zeros_like(YY)

slice_points = np.vstack([XX.ravel(), YY.ravel(), ZZ.ravel()]).T

slice_Bx = interp_Bx(slice_points)
slice_By = interp_By(slice_points)
slice_Bz = interp_Bz(slice_points)

slice_B_mag = np.sqrt(slice_Bx**2 + slice_By**2 + slice_Bz**2)
slice_B_mag_2d = slice_B_mag.reshape((1000, 1000))

#plot
fig = go.Figure(
    data=go.Heatmap(
        x=fine_y,
        y=fine_z,
        z=slice_B_mag_2d.T * 1e3,
        colorscale="viridis",
        zsmooth="best",
        colorbar=dict(
            title="B [mT]",
            tickmode="auto",
            outlinewidth=0
        )
    )
)

fig.show()