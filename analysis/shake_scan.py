from pathlib import Path
import sys,os,json
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'tools/pythonpkgs'))
os.environ['MPLCONFIGDIR']=str(BASE/'tools/mplconfig')
import numpy as np
import pandas as pd
from scipy.signal import butter,sosfiltfilt,find_peaks,welch
from scipy.ndimage import uniform_filter1d,maximum_filter1d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=BASE/'shaking';OUT.mkdir(exist_ok=True)
all_events=[]
for name in ['LOG00026','LOG00025','LOG00023','LOG00021']:
 d=pd.read_csv(BASE/f'decoded/{name}.I.csv');t=(d.time.to_numpy()-d.time.iloc[0])/1e6;fs=1/np.median(np.diff(t));n=len(t)
 gyro=d[[f'gyroADC[{i}]' for i in range(3)]].to_numpy(dtype=float);sp=d[[f'setpoint[{i}]' for i in range(3)]].to_numpy(dtype=float)
 th=(d['rcCommand[3]'].to_numpy()-1000)/10;mix=d['setpoint[3]'].to_numpy()/10
 filt=butter(3,[8,80],btype='bandpass',fs=fs,output='sos');band=sosfiltfilt(filt,gyro-sp,axis=0);gb=sosfiltfilt(filt,gyro,axis=0);sb=sosfiltfilt(filt,sp,axis=0)
 win=int(.15*fs);rms=np.sqrt(np.maximum(0,uniform_filter1d(band**2,size=win,axis=0)));srms=np.sqrt(np.maximum(0,uniform_filter1d(sb**2,size=win,axis=0)))
 # Exclude rapid manoeuvres and their immediate stops, and strong oscillatory commands.
 commandmax=maximum_filter1d(np.max(abs(sp),axis=1),size=int(.4*fs))
 score=np.max(rms[:,:2],axis=1);axis=np.argmax(rms[:,:2],axis=1)
 eligible=(commandmax<180)&(np.max(srms[:,:2],axis=1)<8)&(t>5)&(t<t[-1]-2)
 score[~eligible]=0
 peaks,_=find_peaks(score,height=4,distance=int(1.1*fs),prominence=2)
 events=[]
 for p in peaks:
  a=int(axis[p]);lo=max(0,p-int(.5*fs));hi=min(n,p+int(.5*fs));recent=max(0,p-int(1.2*fs))
  drop=float(th[recent:p+1].max()-th[p]);before=float(th[recent:p+1].max())
  event={'file':name,'t':round(float(t[p]),3),'axis':['roll','pitch'][a],'rms_8_80_dps':round(float(rms[p,a]),2),'command_band_rms':round(float(srms[p,a]),2),'throttle_at_peak':round(float(th[p]),1),'throttle_recent_max':round(before,1),'recent_drop_pp':round(drop,1),'gyro_minmax_300ms':[float(gyro[max(0,p-int(.15*fs)):min(n,p+int(.15*fs)),a].min()),float(gyro[max(0,p-int(.15*fs)):min(n,p+int(.15*fs)),a].max())]}
  # Dominant frequency is a descriptor of this short interval, not a fault diagnosis.
  f,power=welch(band[lo:hi,a],fs=fs,nperseg=min(512,hi-lo));sel=(f>=8)&(f<=80);event['dominant_hz']=round(float(f[sel][np.argmax(power[sel])]),1)
  events.append(event)
 events.sort(key=lambda e:e['rms_8_80_dps'],reverse=True);all_events+=events
 print(name,json.dumps(events[:18]))
 for ev in events[:6]:
  center=ev['t'];m=(t>=center-1.5)&(t<=center+1.5)
  fig,ax=plt.subplots(5,1,figsize=(13,11),sharex=True,layout='constrained')
  ax[0].plot(t[m],th[m],label='Stick throttle');ax[0].plot(t[m],mix[m],label='Mixer throttle',alpha=.7);ax[0].set_ylabel('Throttle (%)');ax[0].legend(loc='upper right')
  for i in range(2):
   ax[i+1].plot(t[m],sp[m,i],label='Commanded',lw=1.2);ax[i+1].plot(t[m],gyro[m,i],label='Measured gyro',lw=.9);ax[i+1].set_ylabel(['Roll','Pitch'][i]+' (deg/s)');ax[i+1].legend(loc='upper right')
  a=['roll','pitch'].index(ev['axis'])
  for term in ['P','I','D','F']:ax[3].plot(t[m],d.loc[m,f'axis{term}[{a}]'],label=term,lw=.8)
  ax[3].set_ylabel(ev['axis']+' PID units');ax[3].legend(ncol=4,loc='upper right')
  for i in range(4):ax[4].plot(t[m],d.loc[m,f'eRPM[{i}]']*200/14,label=f'Motor {i+1}',lw=.8)
  ax[4].set_ylabel('Mechanical RPM');ax[4].legend(ncol=4,loc='upper right');ax[4].set_xlabel('Seconds since first recorded sample')
  for aa in ax:aa.grid(alpha=.2);aa.axvline(center,color='black',alpha=.25,ls='--')
  fig.suptitle(f'{name} | Candidate shake at {center:.3f} s | {ev["axis"]}')
  fig.savefig(OUT/f'{name}_{center:.3f}.png',dpi=140);plt.close(fig)
(OUT/'candidates.json').write_text(json.dumps(all_events,indent=2))
pd.DataFrame(all_events).to_csv(OUT/'candidates.csv',index=False)
