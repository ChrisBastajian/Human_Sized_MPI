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


def get_P(P_dict):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])
    return P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z


def get_B_field(Px, Py, Pz, i):
    return {"Bx": i * Px, "By": i * Py, "Bz": i * Pz}


def get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3):
    B1 = get_B_field(P1x, P1y, P1z, i1)
    B2 = get_B_field(P2x, P2y, P2z, i2)
    B3 = get_B_field(P3x, P3y, P3z, i3)

    return {
        "Bx": B1["Bx"] + B2["Bx"] + B3["Bx"],
        "By": B1["By"] + B2["By"] + B3["By"],
        "Bz": B1["Bz"] + B2["Bz"] + B3["Bz"]
    }

def get_B_from_P(P_dict, i1, i2, i3):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])
    return get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3)

def build_interpolator(flat_array, grid_info):
    #helper function to build a single interpolator
    grid_3d = np.zeros((grid_info["nx"], grid_info["ny"], grid_info["nz"]))
    grid_3d[grid_info["ix"], grid_info["iy"], grid_info["iz"]] = flat_array

    return RegularGridInterpolator(
        (grid_info["x_coords"], grid_info["y_coords"], grid_info["z_coords"]),
        grid_3d,
        method='linear',
        bounds_error=False,
        fill_value=None
    )

def setup_unit_interpolators(grid_vals, P_vals):
    #Packages the grid mapping and builds interpolators for the unit fields
    x_array = np.array(grid_vals["x"])
    y_array = np.array(grid_vals["y"])
    z_array = np.array(grid_vals["z"])

    x_coords, y_coords, z_coords = np.unique(x_array), np.unique(y_array), np.unique(z_array)

    grid_info = {
        "x_coords": x_coords, "y_coords": y_coords, "z_coords": z_coords,
        "ix": np.searchsorted(x_coords, x_array),
        "iy": np.searchsorted(y_coords, y_array),
        "iz": np.searchsorted(z_coords, z_array),
        "nx": len(x_coords), "ny": len(y_coords), "nz": len(z_coords)
    }

    _, _, _, P1y, P2y, P3y, P1z, P2z, P3z = get_P(P_vals)

    interpolators = {
        "P1y": build_interpolator(P1y, grid_info),
        "P1z": build_interpolator(P1z, grid_info),
        "P2y": build_interpolator(P2y, grid_info),
        "P2z": build_interpolator(P2z, grid_info),
        "P3y": build_interpolator(P3y, grid_info),
        "P3z": build_interpolator(P3z, grid_info)
    }

    return interpolators, grid_info

def get_target_ratios(interpolators, target_pos):
    P1y_point = interpolators["P1y"]([target_pos])[0]
    P1z_point = interpolators["P1z"]([target_pos])[0]
    P2y_point = interpolators["P2y"]([target_pos])[0]
    P2z_point = interpolators["P2z"]([target_pos])[0]
    P3y_point = interpolators["P3y"]([target_pos])[0]
    P3z_point = interpolators["P3z"]([target_pos])[0]

    A = np.array([[P2y_point, P3y_point], [P2z_point, P3z_point]])
    B = np.array([-P1y_point, -P1z_point])

    alpha, beta = np.linalg.solve(A, B)
    return alpha, beta

def get_sliced_data(grid_info, P_values, currents=(25, 1, 1), fine=1000):
    field_matrix = get_B_from_P(P_values, currents[0], currents[1], currents[2])

    # Building interpolators for the final B-field components
    interp_Bx = build_interpolator(field_matrix["Bx"], grid_info)
    interp_By = build_interpolator(field_matrix["By"], grid_info)
    interp_Bz = build_interpolator(field_matrix["Bz"], grid_info)

    fine_y = np.linspace(grid_info["y_coords"].min(), grid_info["y_coords"].max(), fine)
    fine_z = np.linspace(grid_info["z_coords"].min(), grid_info["z_coords"].max(), fine)
    YY, ZZ = np.meshgrid(fine_y, fine_z, indexing='ij')
    XX = np.zeros_like(YY)

    slice_points = np.vstack([XX.ravel(), YY.ravel(), ZZ.ravel()]).T

    slice_Bx = interp_Bx(slice_points)
    slice_By = interp_By(slice_points)
    slice_Bz = interp_Bz(slice_points)

    return slice_Bx, slice_By, slice_Bz, fine_y, fine_z

#Loading data:
grid_vals, P_vals = read_json_data(fname='magnetic_field_data(7).json')

#Setting up unit interpolators + getting grid data for them
unit_interpolators, grid_info = setup_unit_interpolators(grid_vals, P_vals)

# 1. Pre-calculate the data for all frames
all_z_data = []

for l in range(100):
    # Defining target FFL position and getting ratios
    target_pos = (0, -0.1 + 0.2 * l / 100, 0.01)  # moving the ffl along y
    alpha, beta = get_target_ratios(unit_interpolators, target_pos)

    # Computing final fields with scaled currents
    I1 = 25
    I2 = alpha * I1
    I3 = beta * I1

    slice_Bx, slice_By, slice_Bz, fine_y, fine_z = get_sliced_data(grid_info, P_vals, (I1, I2, I3))

    slice_B_mag = np.sqrt(slice_Bx ** 2 + slice_By ** 2 + slice_Bz ** 2)

    # Reshape, transpose, and convert to mT immediately, then store it
    slice_B_mag_2d = slice_B_mag.reshape((1000, 1000)).T * 1e3
    all_z_data.append(slice_B_mag_2d)

# Find the global maximum to lock the colorbar so it doesn't flash between frames
global_max = np.max(all_z_data)

# 2. Create the base figure (Starting on Frame 0)
fig = go.Figure(
    data=go.Heatmap(
        x=fine_y,
        y=fine_z,
        z=all_z_data[0],
        colorscale="viridis",
        zsmooth="best",
        zmin=0,  # Lock the bottom of the scale
        zmax=global_max,  # Lock the top of the scale
        colorbar=dict(
            title="B [mT]",
            tickmode="auto",
            outlinewidth=0
        )
    )
)

# 3. Create the animation frames
frames = []
for i, z_data in enumerate(all_z_data):
    frames.append(
        go.Frame(
            data=[go.Heatmap(z=z_data)],
            name=f"frame_{i}"
        )
    )

fig.frames = frames

# 4. Add the "Play" button to the layout
fig.update_layout(
    title="FFL Sweep Animation",
    updatemenus=[dict(
        type="buttons",
        showactive=False,
        y=-0.15,  # Position the button slightly below the plot
        x=0.5,
        xanchor="center",
        yanchor="top",
        buttons=[dict(
            label="▶ Play Video",
            method="animate",
            # duration sets speed (in milliseconds per frame). redraw=True is required for heatmaps.
            args=[None, {"frame": {"duration": 200, "redraw": True}, "fromcurrent": True}]
        )]
    )]
)

fig.show()