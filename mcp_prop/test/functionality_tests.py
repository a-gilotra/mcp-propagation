#! /usr/bin/env python

## This scripts runs a few basic functionality tests to test that
## the b-field propagation, multiple scattering, and energy loss
## are all behaving as expected

from __future__ import print_function 
import numpy as np
import matplotlib.pyplot as plt
from formosa_sim.Environment import Environment
from formosa_sim.Integrator import Integrator
from formosa_sim.Detector import *
import formosa_sim.Drawing as Drawing
import sys
try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x:x

pyVersion = sys.version_info[0]
if pyVersion == 2:
    bFile = "../bfield/bfield_coarse.pkl"
else:
    bFile = "../bfield/bfield_coarse_p3.pkl"
env = Environment(
    mat_setup="atlas", 
    bfield="cms", 
    bfield_file=bFile, 
    rock_begins=17.0
    )

itg = Integrator(
    environ = env,
    m = 105.0,
    Q = 1.0,
    dt = 0.2,
    nsteps = 5000,
    cutoff_dist = 20.,
    cutoff_axis = 'R',
    use_var_dt = True,
    lowv_dx = 0.01,
    multiple_scatter = 'pdg',
    do_energy_loss = True,
    randomize_charge_sign = True
    )

det = PlaneDetector(
    dist_to_origin = 3.0,
    theta = 25.0,
    phi = 0.0,
    width = 5.0,
    height = 5.0,
)

# FORESEE output momenta
p_mag = np.loadtxt('/Users/ayushg/Documents/GitHub/mcp-propagation/mcp_prop/p_array.txt')

print("Using FORESEE-generated momenta...")
trajs = []
intersects = []
rand=np.random.uniform(0, len(p_mag), 20)
for i in tqdm(range(len(rand))):

    px = p_mag[i][0] 
    py = p_mag[i][1]
    pz = p_mag[i][2]


    x0 = np.array([0, 0, 0, px, py, pz])
    traj,_ = itg.propagate(x0)

    trajs.append(traj)

    intersects.append(det.find_intersection(traj))

plt.figure(figsize=(15,7))
Drawing.Draw3Dtrajs(trajs, subplot=121)

c1,c2,c3,c4 = det.get_corners()
Drawing.DrawLine(c1,c2,is3d=True)
Drawing.DrawLine(c2,c3,is3d=True)
Drawing.DrawLine(c3,c4,is3d=True)
Drawing.DrawLine(c4,c1,is3d=True)
for inter in intersects:
    if inter is None:
        continue
    Drawing.DrawLine(inter["x_int"],inter["x_int"],is3d=True,linestyle='None',marker='o',color='r')
Drawing.DrawXYslice(trajs, subplot=122)

plt.figure(figsize=(11.7,7))
Drawing.DrawXZslice(trajs, drawBFieldFromEnviron=env, drawColorbar=True)

print("Propagating muons through blocks of silicon/iron to test Bethe-Bloch energy loss...")
# test dE/dx energy loss
env.bfield = None
env.mat_setup = 'atlas'
plt.figure()
for p0,c in zip([2000,3000,5000,10000,20000],list("rgbcm")):
    traj,_ = itg.propagate([0,0,0,p0,0,0])
    plt.plot(traj[0,:], np.linalg.norm(traj[3:,:],axis=0)/1000, '-'+c, label="{0} GeV".format(p0/1000))
plt.gca().set_xlim(0,18)
plt.gca().set_ylim(0,20)
plt.plot([4,4],[0,20],'k--')
plt.xlabel("x (m)")
plt.ylabel("Momentum (GeV/c)")
plt.legend()

# plot multiple scattering through iron
print("Propagating muons through 20m solid iron to visualize multiple scattering...")
env.bfield = None
env.mat_setup = 'unif_fe'
itg.do_energy_loss = False
plt.figure()
for p0,c in zip([2000,3000,5000,10000,20000],list("rgbcm")):
    traj,_ = itg.propagate([0,0,0,p0,0,0])
    plt.plot(traj[0,:], traj[1,:], '-'+c, label="{0} GeV".format(p0/1000))
plt.xlabel("x (m)")
plt.ylabel("Transverse displacement (m)")
plt.legend()

# histogram deviation from multiple scattering through 2m of iron
print("Propagating many muons through 2m iron to histogram deviation due to multiple scattering...")
env.bfield = None
env.mat_setup = 'unif_fe'
itg.do_energy_loss = False
itg.cutoff_dist = 2.0
itg.dt = 0.1
plt.figure()
for p0,c in zip([3000,5000,7000,10000],list("rgbc")):
    devs = []
    print("Momentum:", p0, "MeV")
    for i in tqdm(range(200)):
        traj,_ = itg.propagate([0,0,0,p0,0,0])
        devs.append(np.linalg.norm(traj[1:3,-1]) * 100)
    plt.hist(devs, bins=100, range=(0,25), histtype='step', color=c, label="{0} GeV".format(p0/1000))
plt.xlabel("Transverse displacement (cm)")
plt.legend()


plt.show()
