import numpy as np
import json
from collections import defaultdict
import plotly.graph_objects as go
import plotly.io as pio
from scipy.interpolate import RegularGridInterpolator

pio.renderers.default = 'browser'

# =====================================================================
# 1. CONFIGURATION INPUTS
# =====================================================================
target_y = 0.025                # Desired Y coordinate [m]
target_z = 0.03                 # Desired Z coordinate [m]
desired_gradient = 0.3         # Set your exact target gradient [T/m]

lookup_file = 'gradient_results.json'
field_file = 'magnetic_field_data.json'

# =====================================================================
# 2. CORE PHYSICS & MATH FUNCTIONS
# =====================================================================
def read_json_data(fname):
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

def get_P(P_dict):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])
    return P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z

def build_interpolator(flat_array, nx, ny, nz, ix, iy, iz):
    grid_3d = np.zeros((nx, ny, nz))
    grid_3d[ix, iy, iz] = flat_array
    return RegularGridInterpolator((x_coords, y_coords, z_coords), grid_3d, method='linear', bounds_error=False, fill_value=None)


# =====================================================================
# 3. FAST LOOKUP FROM JSON MAP (No derivatives calculated here)
# =====================================================================
print("Looking up nearest point in gradient map...")
with open(lookup_file, 'r') as f:
    map_data = json.load(f)

best_match = None
min_distance = float('inf')

for item in map_data["results"]:
    if item["max_gradient"] is None:
        continue
    distance = np.sqrt((item["y"] - target_y)**2 + (item["z"] - target_z)**2)
    if distance < min_distance:
        min_distance = distance
        best_match = item

max_grad = best_match["max_gradient"]
scaling_factor = desired_gradient / max_grad

# Linearly scale the currents from the map
I1_target = best_match["currents"]["I1"] * scaling_factor
I2_target = best_match["currents"]["I2"] * scaling_factor
I3_target = best_match["currents"]["I3"] * scaling_factor

print(f"Closest Map Point : Y = {best_match['y']}, Z = {best_match['z']}")
print(f"Required Currents : I1={I1_target:.2f}A, I2={I2_target:.2f}A, I3={I3_target:.2f}A")


# =====================================================================
# 4. LOAD BASE FIELD DATA & INTERPOLATE
# =====================================================================
print("Loading field data and preparing visualization...")
grid_vals, P_vals = read_json_data(fname=field_file)
P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z = get_P(P_vals)

x_array = np.array(grid_vals["x"])
y_array = np.array(grid_vals["y"])
z_array = np.array(grid_vals["z"])

x_coords, y_coords, z_coords = np.unique(x_array), np.unique(y_array), np.unique(z_array)
ix, iy, iz = np.searchsorted(x_coords, x_array), np.searchsorted(y_coords, y_array), np.searchsorted(z_coords, z_array)
nx, ny, nz = len(x_coords), len(y_coords), len(z_coords)


# =====================================================================
# 5. GENERATE FINAL PLOT USING LOOKUP CURRENTS
# =====================================================================
field_matrix = get_B_from_P(P_vals, I1_target, I2_target, I3_target)

interp_Bx = build_interpolator(field_matrix["Bx"], nx, ny, nz, ix, iy, iz)
interp_By = build_interpolator(field_matrix["By"], nx, ny, nz, ix, iy, iz)
interp_Bz = build_interpolator(field_matrix["Bz"], nx, ny, nz, ix, iy, iz)

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


# =====================================================================
# 6. VISUALIZATION
# =====================================================================
fig = go.Figure(
    data=go.Heatmap(
        x=fine_y,
        y=fine_z,
        z=slice_B_mag_2d.T * 1e3, # Transpose for Plotly & convert to mT
        colorscale="viridis",
        zsmooth="best",
        colorbar=dict(
            title="B Field [mT]",
            tickmode="auto",
            outlinewidth=0
        )
    )
)

fig.update_layout(
    title=f"Magnetic Field Profile: FFL at Y={target_y}, Z={target_z} with {desired_gradient} T/m",
    xaxis_title="Y Coordinate [m]",
    yaxis_title="Z Coordinate [m]"
)

fig.show()