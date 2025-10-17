clear
clc

%%Analytical Calculations for Solenoid Specs

%We want the center of the magnetic field to be 14.24mT
%for now, the following measurements will be used for the rest of the coil
%The height of the coil and the magnetic field are 

numlayer = 3;
r = 0.08; %[m] radius of the coil
L = 0.11; %[m] Height of the coil
B = 0.01424; %[T] Magnetic field at the center of the coil in the x, y, AND z direction
N = 147; %[Turns] Number of turns of the coild

% Ultimately, we will need to find the current running through the coil, as
% well as the optimum number of turns of the coil and the length of the coil
%Let us make the number of turns and length into a ratio n

n = N/L;
u = 4*pi*10^(-7); % magnetic permativity of air
ur = 1; %magnetic permativity of copper

%For our purposes, the angles will be equal in magnitude since we want the magnetic field at the
%center of the coil.

y = L/2;
theta2 = asin(y/(sqrt(y^2 + r^2)));
theta1 = asin((-y)/(sqrt((-y)^2 + r^2)));

%Using Ampere's Law, the  equation was derived...

I = (2*B)/(u * n * (sin(theta2) - sin(theta1)))

%Since we want the amperage less tfollowinghan 15A to accomodate for 14 gauge wire,
%we should optimize the number of turns/radius of the coil

%% Calculating Inductance
%There are four layers of coils concentric to eachother
wt = 0.003; %litz wire thickness[m]
r1 = r + wt/2; 
r2 = r1 + wt;
r3 = r2 + wt;
r4 = r3 + wt;

induct1 = (u*ur*(N/4)^2*pi*r1^2)/(L);
induct2 = (u*ur*(N/4)^2*pi*r2^2)/(L);
induct3 = (u*ur*(N/4)^2*pi*r3^2)/(L);
induct4 = (u*ur*(N/4)^2*pi*r4^2)/(L);
series1 = induct1 + induct2;
series2 = induct3 + induct4;

induct = (series1*series2)/(series1 + series2)

%% Magnetic Field Calculations

%As stated earlier, we want to create a coil to have a maximum magnetic
%field of 15.47 mT. Let's see the strength of the magnetic field through the center of the coil. 

ylim = 0 : 0.005: 0.20;
Bvar = [];

for y2 = (0: 0.005: 0.20)
    
    theta2 = atan(y2 / r);
    y1 = L - y2;
    theta1 = atan(-y1 / r);
    Bvar = [Bvar, (u * I * n * (sin(theta2) - sin(theta1)))/2];

end

%Scaling quantities on graph
Bvar = Bvar * 1000;
ylim = ylim * 100;

plot(ylim, Bvar)
title('Magnetic Field Strength Through the Center of the Solenoid')
ylabel('Strength of Magnetic Field (mT)')
xlabel('Distance from the Top of the Coil (cm)')

%% Simulating Capacitors

%We are simulating our capacitances to match the impedance of the
%inductance, which works from a range of 10uF - 10nF.
%Each capacitor is rated for 300V, which means that we need to calculate
%the voltage drop accross each

capvals = [0.470*10^-6, 0.330*10^-6, 0.330*10^-6, 0.330*10^-6, 0.330*10^-6, 0.330*10^-6, 0.330*10^-6];
num_cap = size(capvals, 2); %number of capacitors in series
count = 1;
total = 0;
for eqcap = (1 : 1 : num_cap)
    
    inv_imped = 1/capvals(count);
    total = total + inv_imped;
    count = count + 1;

end
    
total_cap = 1/total
op_freq = sqrt(1 / (total_cap * induct)) / (2 * pi)

%Next, finding total change across the caps
%QT = Q1 = Q2 = Q3 = ... = Qn
%There are three ranges of voltages: 800V, 1500V, 2000V

vsup = [800, 1500, 2000];
num_drops = size(vsup, 2) * num_cap;
count = 1;
count2 = 1;
for charge = [1 : 1 : size(vsup, 2)]

    Q(count) = vsup(count) * total_cap;
    
    for drops = [1 : 1 : num_cap]
        vdrop(count2) = Q(count)/capvals(count);
        plot_cap(count2) = capvals(count);
        count2 = count2 + 1;
    end
 
    count = count + 1;
end

vdrop






