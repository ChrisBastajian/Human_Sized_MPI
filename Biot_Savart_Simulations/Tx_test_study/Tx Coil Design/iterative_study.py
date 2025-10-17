import numpy as np
import matplotlib.pyplot as plt
import sympy as sp
from scipy.interpolate import RegularGridInterpolator
from scipy.integrate import quad, dblquad
import plotly.graph_objects as go
import plotly.io as pio
import scipy.optimize as optimize

pio.renderers.default = 'browser'
#Constants:
R = 10 * 1e-2 # the radius of the coil, assuming 90th percentile to be no bigger than 20 (overestimation)
mu0 = 4 * np.pi * 1e-7
wire_thickness = 3 * 1e-3

"""
I = 10 #current intensity in A
h = 20 * 1e-2 #~20cm, assuming 90th percentile to be no bigger than 18 (overestimation)

#finding thickness of litz wire:
num_layers = 4 #4 layers of coils
wire_thickness = 3 * 1e-3

#getting number of turns:
num_turns_per_layer = h/wire_thickness
num_turns = num_turns_per_layer * num_layers
print(f"Number of turns: {num_turns}")
"""
#Function that returns the integrand based on dimensions:
def get_integrand(radius, n_turns, height, I=1):
    phi, x, y, z = sp.symbols('phi,x,y,z')

    #recreate function of current path but in sympy to integrate:
    l = radius * sp.Matrix([sp.cos(phi), sp.sin(phi), (height/(radius * n_turns * 2 * np.pi))*phi])

    #distance away from path:
    r = sp.Matrix([x, y, z])

    #B(r) = ((mu0 * I)/(4piR)) * integral_along_curve\loop([(dl/dt x (r-l))/norm(r-l)^3)]dt
    #so we can simplify by defining r-l (vector of separation):
    difference = r-l
    #print(difference)

    #function to integrate (commented above):
    integrand = (mu0 * I / (4 * np.pi)) * sp.diff(l, phi).cross(difference)/ difference.norm()**3 #this will hold dB/dt for all 3 dimensions

    # need to lambdify all 3 functions into actual array representations of them:
    dBx = sp.lambdify([phi, x, y, z], integrand[0])
    dBy = sp.lambdify([phi, x, y, z], integrand[1])
    dBz = sp.lambdify([phi, x, y, z], integrand[2])

    return integrand, dBx, dBy, dBz

#function to get B from the integrand (integrate):
def B(xo, yo, zo, dBx, dBy, dBz, n_turns):
    return(np.array([
        quad(dBx, 0, n_turns * 2 * np.pi, args=(xo, yo, zo), limit=10000)[0],
        quad(dBy, 0, n_turns * 2 * np.pi, args=(xo, yo, zo), limit=10000)[0],
        quad(dBz, 0, n_turns * 2 * np.pi, args=(xo, yo, zo), limit=10000)[0],
    ]))

def get_inductance(radius, n_turns, height):
    mu_o = 4 * np.pi * 1e-7
    L = (np.pi * pow(n_turns,2) * pow(radius,2) * mu_o)/height
    return L
"""
#Example usage of functions

integrands, dBx, dBy, dBz = get_integrand(R, num_turns, h, I=I)
print(dBz(2*np.pi, 1, 1,1 )) #prints the z component at the given location
#calculate B at the center (0, 0, 0)
B_center = B(0, 0, h/2, dBx, dBy, dBz, num_turns)
print(B_center)


print(get_inductance(0.0175, 196, 0.07)) #validation of formula
"""
#Start of Iterative Process:
nl_range = [0,4] #range for layers
irms_range = [0,30] #range for ac current
height_range = [7, 12]
dps = 20

nl_values = range(nl_range[0]+1, nl_range[1]+1) #To get discrete values
irms_values = np.linspace(irms_range[0], irms_range[1], dps)
height_values = range(height_range[0], height_range[1])

results = {
    "height": [],
    "irms" : [],
    "n_turns" : [],
    "B" : [],
    "L": []
}
for h in height_values:
    num_turns_per_layer = (h * 1e-2) / wire_thickness
    height = h * 1e-2 #converting to meters for the functions
    for nl in nl_values:
        num_turns = num_turns_per_layer * nl
        for irms in irms_values:
            _, dBx, dBy, dBz = get_integrand(R, num_turns, height, I=irms)
            B_vec = B(0, 0, height/2, dBx, dBy, dBz, num_turns)
            B_mag = np.linalg.norm(B_vec) #the magnitude B_mag = sqrt(Bx^2+By^2+Bz^2)
            B_mag *= 1e+3 #converting to mT

            L = get_inductance(R, num_turns, height)
            L *= 1e+3 #converting to mH

            results["irms"].append(irms)
            results["n_turns"].append(num_turns)
            results["B"].append(B_mag)
            results["L"].append(L)
            results["height"].append(h) #this is in cm

# Plotting Magnetic Field
fig1 = go.Figure(data=[go.Scatter3d(
    x=results["irms"],
    y=results["n_turns"],
    z= results["B"],
    mode='markers',
    marker=dict(
        size=6,
        color=results["height"],
        colorscale='Viridis',
        colorbar=dict(title='h (cm)'),
    )
)])
fig1.update_layout(scene=dict(
    xaxis_title='AC Current (A)',
    yaxis_title='Number of Turns',
    zaxis_title='Magnetic Field at Center (mT)'
), title='Magnetic Field vs Current vs Turns')
fig1.show()

# Plotting Inductance:
fig2 = go.Figure(data=[go.Scatter3d(
    x=results["height"],
    y=results["n_turns"],
    z= results["L"],
    mode='markers',
    marker=dict(
        size=6,
        color=results["height"],
        colorscale='Viridis',
        colorbar=dict(title='h (cm)'),
    )
)])
fig2.update_layout(scene=dict(
    xaxis_title='Height (cm)',
    yaxis_title='Number of Turns',
    zaxis_title='Inductance of the Coil (mH)'
), title='Inductance vs Height vs Turns')
fig2.show()

# Plotting Inductance and B_field on same plot:
fig3 = go.Figure(data=[go.Scatter3d(
    x=results["L"],
    y=results["n_turns"],
    z= results["B"],
    mode='markers',
    marker=dict(
        size=6,
        color=results["irms"],
        colorscale='Viridis',
        colorbar=dict(title='I_rms (A)'),
    )
)])
fig3.update_layout(scene=dict(
    xaxis_title='Inductance of the coil (mH)',
    yaxis_title='Number of Turns',
    zaxis_title='Magnetic Field at the Center (mT)'
), title='Magnetic Field vs Inductance vs Turns')
fig3.show()

fig4 = go.Figure(data=[go.Scatter3d(
    x=results["height"],
    y=results["n_turns"],
    z= results["B"],
    mode='markers',
    marker=dict(
        size=6,
        color=results["irms"],
        colorscale='Viridis',
        colorbar=dict(title='I (A)'),
    )
)])
fig4.update_layout(scene=dict(
    xaxis_title='Height (cm)',
    yaxis_title='Number of Turns',
    zaxis_title='Magnetic Field at Center (mT)'
), title='Magnetic Field vs Height vs Turns')
fig4.show()

"""
fig1.write_html("magnetic_field_vs_current_vs_turns.html")
fig2.write_html("inductance_vs_height_vs_turns.html")
fig3.write_html("magnetic_field_vs_inductance_vs_turns.html")
fig4.write_html("magnetic_field_vs_height_vs_turns.html")
"""