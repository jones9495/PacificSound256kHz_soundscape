from ran_sea import ran_sea
import numpy as np
import shutil
import subprocess
import matplotlib.pyplot as plt
import scipy.interpolate as interp

freq = 500
zs = 10
zr = 10
range_max = 10*1000
dr = 10
dr_samp = 1
zmax = 2000
dz = 1
dz_samp = 1
zmplt = 800
c0 = 1500
np_ = 4
ns = 1
rs = 0.0
zb = 200
wind_sp = 20


rand_h,rvec = ran_sea(range_max,wind_sp)

rint = np.arange(0,range_max+dr,dr)
f_interp = interp.interp1d(rvec, rand_h, kind='linear', fill_value='extrapolate')
rand_h_int = f_interp(rint)

rand_h = rand_h_int
r = rint
max_h = np.max(rand_h)

with open('ip_file.in','w') as fid:
    fid.write("Rough surface \t Name of file\n")
    fid.write(f"{freq:4.2f} {zs:3.2f} {zr:3.2f} \t Frequency zs zr \n")
    fid.write(f"{range_max:4.2f} {dr:3.2f} {dr_samp:d} \t Range deltar ndeltar \n")
    fid.write(f"{zmax:4.2f} {dz:1.2f} {dz_samp:d} {zmplt:3.2f}\t Max_depth dz ndz max_dep_plt \n")
    fid.write(f"{c0:4.2f} {np_:d} {ns:d} {rs:3.2f}\t c0 np ns rs\n")
    fid.write('\n')
    
    nrr=len(r)
    for k in range(nrr):
        if(k==0):
            fid.write(f"{r[k]:1.2f} {-rand_h[k]+max_h:1.2f} \t range zsrf(r)\n")
        else:
            fid.write(f"{r[k]:1.2f} {-rand_h[k]+max_h:1.2f}\n")

    fid.write("-1 -1\n")
    fid.write(f"0.0 {zb:3.2f} \t rb zb\n")
    fid.write("-1 -1\n")
    fid.write("0.0 1500 \t z cw\n")
    fid.write("-1 -1\n")
    fid.write("0.0 1700 \t z cb\n")
    fid.write("-1 -1\n")
    fid.write("100.0  2 \t z rhob\n")
    fid.write("-1 -1\n")

    attn = 2
    fid.write(f"100 {attn:1.1f} \t z attn \n")
    fid.write("-1 -1\n")


shutil.copy('ip_file.in','ramsurf.in')

with open('log.o','w') as outfile:
    subprocess.run(['./ramsurf'], stdout=outfile, text=True)
    
filename='samp.grid'
samp=np.loadtxt(filename)
ranges=samp[:,0]
TL=samp[:,1:].T
rr = np.arange(dr, range_max + dr * dr_samp, dr * dr_samp)
rd = np.arange(0, zmplt + dz * dz_samp, dz * dz_samp)

plt.figure(figsize=(8,6))

im=plt.imshow(TL, extent=[ranges[0]/1000, ranges[-1]/1000,rd[-1],rd[0]],
              aspect='auto',
              cmap=plt.cm.jet_r,
              vmin=30, vmax=150)

X, Y=np.meshgrid(ranges/1000,rd)
cf=plt.contourf(X,Y,TL,
                levels=np.arange(30,151,10),
                cmap=plt.cm.jet_r,
                antialiased=False)

cbar=plt.colorbar(im)
cbar.set_label('TL (dB)')

plt.xlabel('Range (km)')
plt.ylabel('Depth (m)')
plt.title('RAMsurf output')

plt.grid(True)
plt.show()



