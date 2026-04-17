import numpy as np
import json
from collections import defaultdict

from pyvisa.rname import PXIMemacc

with open('magnetic_field_data.json', 'r') as f:
    data = json.load(f)

P = defaultdict(list) #will hold the unit fields

for coil in data["unit_fields"]:
    for dim in data["unit_fields"][coil]:
        for dim_data in data["unit_fields"][coil][dim]:
            P[coil, dim].append(dim_data)

#print(P["c1", "u"])
#currents:
i1, i2, i3, =1,1,1
alpha = i2/i1
beta = i3/i1

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

field_matrix = get_B_from_P(P, i1, i2, i3)