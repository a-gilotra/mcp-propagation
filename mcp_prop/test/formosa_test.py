#! /usr/bin/env python

## Test script to show how to generate particles from a random distribution,
## propagate throught the magnetic field, and simulate their incidence
## on an external Milliqan detector.
##
## For the purposes of visualization, the external detector has been moved
## much closer and enlarged to a 3m x 3m square.
##
## use mode "VIS" to generate a few trajectries and then visualize with matplotlib
## use mode "STATS" to collect statistics on particle hits on the detector, and output
## to a text file
##
## The output format is (Q,m,p,pT,eta,phi,theta,thetaW,thetaV,w,v,pInt), one per column
##  -Q is the charge (program randomly chooses each to be pos/neg)
##  -m is the particle mass
##  -p/pT are the initial (transverse) momentum in MeV
##  -theta/phi are the initial theta/phi of the particle
##  -theta is the of incidence on the detector plane, w.r.t. the normal
##  -w,v are coordinates in the detector plane, where (0,0) is the center.
##  -thetaW, thetaV are the angles of incidence projected on the w,v directions
##  -pInt is the momentum magnitude upon incidence with the detector plane
##
## The above variables are somewhat obscure and were used for testing/debugging.
## To get more useful variables, run the tools/formatOutput.py script.

from __future__ import print_function 
import math
import time
import os.path
import sys
import numpy as np
import matplotlib.pyplot as plt
import ROOT
from formosa_sim.Environment import Environment
from formosa_sim.Integrator import Integrator
from formosa_sim.Detector import *
import formosa_sim.Drawing as Drawing
from formosa_sim.MilliTree import MilliTree
import run_params as rp

# do you want to VISualize, or collect STATS?
mode = rp.mode

if mode=="VIS":
    ntrajs = rp.ntrajs
    trajs = []
if mode=="STATS":
    # in STATS mode, this is the number of hits on the detector to generate
    # the total number of trajectories simulated will be greater
    ntrajs = rp.ntrajs
    trajs = []
    print("Simulating {0} hits on the detector.".format(ntrajs))
    print(' ')
visWithStats = False
outname = "formosa_test.txt"
if mode=="STATS":
    print("Outputting to "+outname)

pyVersion = sys.version_info[0]
if pyVersion == 2:
    bFile = "../bfield/bfield_coarse.pkl"
else:
    bFile = "../bfield/bfield_coarse_p3.pkl"
env = Environment(
    mat_setup = 'atlas',
    bfield = rp.bfield_type,
    bfield_file = bFile,
    rock_begins = rp.rock_begins,
    rock_ends = rp.distToDetector-0.10,
    mat_function = rp.matFunction if rp.useCustomMaterialFunction else None
)

itg = Integrator(
    environ = env,
    Q = rp.particleQ,
    m = rp.particleM,
    dt = rp.dt,
    nsteps = rp.max_nsteps,
    cutoff_dist = rp.cutoff,
    cutoff_axis = 'r',
    use_var_dt = rp.use_var_dt,
    lowv_dx = 0.01,
    multiple_scatter = 'pdg',
    do_energy_loss = True,
    randomize_charge_sign = False,
    )

det = PlaneDetector(
    dist_to_origin = rp.distToDetector,
    theta = rp.theta,
    phi = 0.0,
    width = rp.detWidth,
    height = rp.detHeight,
)

mdet = FormosaDetector(
    dist_to_origin = rp.distToDetector,
    theta = rp.theta,
    phi = 10.0,
    nrows = 2,
    ncols = 2,
    nlayers = 4,
    bar_width = 1.0,
    bar_height = 1.0,
    bar_length = 2.0, 
    bar_gap = 0.5,
    layer_gap = 0.4,
)


# make sure numbers are new each run
seed = 0
ROOT.gRandom.SetSeed(seed)
np.random.seed(seed)

rootfile = ROOT.TFile(rp.pt_spect_filename)
# this is a 1D pT distribution (taken from small-eta events)
pt_dist = rootfile.Get("pt")

mt = MilliTree()

# setup output file
suffix = sys.argv[1] if len(sys.argv) > 1 else "test"
try:
    os.makedirs("output_data")
except:
    pass
outname = "output_data/output_{0}.txt".format(suffix)
outnameCustom = "customOutput_{0}.txt".format(suffix)

if mode=="STATS":
    # if file already exists, check if we want to overwrite or append
    if os.path.isfile(outname):
        ow = 'q'
        while ow not in 'yYnN':
            ow = input("Overwrite file? (y/n) ")
        if ow in 'yY':
            txtfile = open(outname,'w')
            if rp.useCustomOutput:
                txtfile2 = open(outnameCustom, 'w')
        else:
            print("OK, appending")
            txtfile = open(outname,'a')
            if rp.useCustomOutput:
                txtfile2 = open(outnameCustom, 'a')
    else:
        txtfile = open(outname,'w')
        if rp.useCustomOutput:
            txtfile2 = open(outnameCustom, 'w')
    txtfile.close()
    if rp.useCustomOutput:
        txtfile2.close()


starttime = time.time()

intersects = []
bar_intersects = []
ntotaltrajs = 0
tmp = 0
p1 = np.loadtxt('/Users/ayushg/Documents/GitHub/mcp-propagation/mcp_prop/p_array.txt')
pm = np.array([])
for i in range(len(p1)):
    pm = np.append(pm, np.sqrt(p1[i][0]**2+p1[i][1]**2+p1[i][2]**2)/100)

# loop until we get ntrajs trajectories (VIS) or hits (STATS)
while len(trajs)<ntrajs:
    tmp = tmp+1
    t = tmp
    # magp = -1
    magp = p1[tmp]
    theta = 0.03

    thetalow =  rp.thetabounds[0]
    thetahigh =  rp.thetabounds[1]

    # draw random pT values from the distribution. Set minimum at 10 GeV
    # while magp < rp.ptCut:
    #     magp = pt_dist.GetRandom()

    # theta distribution is uniform for smalltheta 
    th = np.random.rand()*(thetahigh-thetalow) + thetalow

    phimin, phimax =  rp.phibounds
    phi = np.random.rand() * (phimax-phimin) + phimin
    itg.Q *= np.random.randint(2)*2 - 1 
    phi *= itg.Q/abs(itg.Q)

    # convert to cartesian momentum in MeV
    p = 1000*magp * np.array([np.sin(th)*np.cos(phi),np.sin(th)*np.sin(phi),np.cos(th)])
    x0 = np.array([0,0,0,p[0],p[1],p[2]])
    print(x0)
    
    # simulate until nsteps steps is reached, or the particle passes x=10
    traj,tvec = itg.propagate(x0)
    ntotaltrajs += 1
    if mode=="VIS":
        trajs.append(traj)

    # compute the intersection. Will return None if no intersection
    idict = det.find_intersection(traj, tvec)
    bar_intersects.append(mdet.find_entries_exits(traj, assume_straight_line=True))
    if idict is not None:
        intersects.append((len(trajs)-1,idict["x_int"]))
        print(len(trajs), ": p =",magp, ", theta =", theta, ", phi =", phi, ", eff =", float(len(intersects))/ntotaltrajs)
        if mode=="VIS":
            pass
        elif mode=="STATS":
            if visWithStats:
                trajs.append(traj)
            else:
                trajs.append(0)
            magpint = np.linalg.norm(idict["p_int"])
            txtfile = open(outname,'a')
            txtfile.write("{0:f}\t{1:f}\t{2:f}\t{3:f}\t{4:f}\t{5:f}\t{6:f}\t{7:f}\t{8:f}\t{9:f}\t{10:f}\t{11:f}\t{12:f}\n".format(
                    t, itg.Q, itg.m, magp, magp*np.sin(th), theta, phi,
                    idict["theta"], idict["theta_w"], idict["theta_v"], idict["w"], idict["v"], magpint))
            txtfile.close()
            if rp.useCustomOutput:
                txtfile = open(outnameCustom, 'a')
                txtfile.write("\t".join(str(x) for x in rp.outputFunction(traj, det)) + '\n')
                txtfile.close()
            mt.SetValues(idict["x_int"],itg, idict["p_int"])
            mt.Fill()

endtime = time.time()

print("Efficiency:", float(len(intersects))/ntotaltrajs)
print("Total time: {0:.2f} sec".format(endtime-starttime))
print("Time/Hit: {0:.2f} sec".format((endtime-starttime)/ntrajs))

mt.Write("output_data/output_{0}.root".format(suffix))

fid = ROOT.TFile("output_data/output_{0}.root".format(suffix), "UPDATE")

hhits = ROOT.TH1F("hhits","",1,0,2)
hsims = ROOT.TH1F("hsims","",1,0,2)
hhits.Fill(1, ntrajs)
hsims.Fill(1, ntotaltrajs)
hhits.Write()
hsims.Write()

fid.Close()

if mode=="VIS" or visWithStats:
    plt.figure(num=1, figsize=(15,7))
    Drawing.Draw3Dtrajs(trajs, subplot=121)    

    # the four corners
    c1,c2,c3,c4 = det.get_corners()
    Drawing.DrawLine(c1,c2,is3d=True, c='k')
    Drawing.DrawLine(c2,c3,is3d=True, c='k')
    Drawing.DrawLine(c3,c4,is3d=True, c='k')
    Drawing.DrawLine(c4,c1,is3d=True, c='k')

    mdet.draw(plt.gca(), c='0.65', draw_containing_box=False)
    plt.gca().set_xlim(mdet.center_3d[0]-8, mdet.center_3d[0]+8)
    plt.gca().set_ylim(mdet.center_3d[2]-8, mdet.center_3d[2]+8)
    plt.gca().set_zlim(mdet.center_3d[1]-8, mdet.center_3d[1]+8)

    colors = ['r','g','b','c','m','y']

    # for i in range(len(intersects)):
    #     c = colors[intersects[i][0] % len(colors)]
    #     Drawing.DrawLine(intersects[i][1],intersects[i][1],is3d=True,linestyle='None',marker='o',color=c)

    hit_boxes = set()
    for i,isects in enumerate(bar_intersects):
        for isect in isects:
            hit_boxes.add(isect[0])
            c = colors[i % len(colors)]
            Drawing.DrawLine(isect[1], isect[1], is3d=True, linestyle='None', marker='o', mfc=c, mec='k')
            Drawing.DrawLine(isect[2], isect[2], is3d=True, linestyle='None', marker='o', mfc='w', mec=c)

    for ilayer,irow,icol in hit_boxes:
        mdet.bars[ilayer][irow][icol].draw(plt.gca(), c='k')

    Drawing.DrawXYslice(trajs, subplot=122)

    plt.figure(num=2, figsize=(11.7,7))
    Drawing.DrawXZslice(trajs, drawBFieldFromEnviron=env, drawColorbar=True)

    plt.figure(3)
    for traj in trajs:
        rvals = np.linalg.norm(traj[:3,:], axis=0)
        pvals = np.linalg.norm(traj[3:,:], axis=0)
        plt.plot(rvals,pvals)

    plt.show()
