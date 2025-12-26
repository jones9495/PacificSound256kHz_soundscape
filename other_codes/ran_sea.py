import numpy as np
   
    
def ran_sea(range_max,wind_sp):    
    alpha = 8.1*1e-3 
    beta = 0.74
    g = 9.8
    U = wind_sp
    kl_sq = beta*g**2/U**4
    
    kl  = np.sqrt(kl_sq)
    kmax = 16*kl
    lmax = range_max
    deltak = 2*np.pi/lmax
    kmin = deltak
    k_start = kmin
    
    kbw=kmax-kmin
    nk=int(np.floor(kbw/deltak))
    k_end=kmax+deltak
    k=np.linspace(k_start,k_end,nk)
    k_qube=k**3
    k_sq=k**2
    Sh=alpha/(2*k_qube)*np.exp(-kl_sq/k_sq)
    
    rand_vec=np.random.randn(nk)+1j*np.random.randn(nk)
    rand_abs=np.abs(rand_vec)
    rand_phs=np.angle(rand_vec)
    rand_amp=rand_abs*np.exp(1j*rand_phs)
    
    
    ht_f_pos=1/2*np.sqrt(Sh*deltak)*rand_amp
    ht_f_neg=np.conj(ht_f_pos)
    ht_f_neg=np.flip(ht_f_neg)
    ht_f=np.concatenate(([0+0j],ht_f_pos,ht_f_neg))
    
    ht_r=(2*nk+1)*np.fft.ifft(ht_f)
    ht_r=ht_r.real
    deltar=lmax/(2*nk+1)
    rvec=np.linspace(0,lmax,2*nk+1)
    
    return ht_r,rvec
    