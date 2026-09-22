from pathlib import Path
import sys, os, json
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'tools/pythonpkgs'))
os.environ['MPLCONFIGDIR']=str(BASE.parent/'tools/mplconfig')
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt, find_peaks, welch
from scipy.ndimage import uniform_filter1d, maximum_filter1d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inventory import header
OUT=BASE/'results';OUT.mkdir(exist_ok=True)

def rms(a):return np.sqrt(np.mean(a*a,axis=0))
def load(name,base=None):
    folder=Path(base) if base is not None else BASE
    d=pd.read_csv(folder/'decoded'/f'{name}.I.csv');g=pd.read_csv(folder/'decoded'/f'{name}.G.csv');h=header(name,folder)
    t=(d.time.to_numpy()-d.time.iloc[0])/1e6;fs=1/np.median(np.diff(t))
    x={'name':name,'d':d,'t':t,'fs':fs,'h':h,'group':'Default' if h['simplified_d_gain']=='100' else 'D 1.10'}
    x['gyro']=d[[f'gyroADC[{a}]' for a in range(3)]].to_numpy(float)
    x['raw']=d[[f'gyroUnfilt[{a}]' for a in range(3)]].to_numpy(float)
    x['sp']=d[[f'setpoint[{a}]' for a in range(3)]].to_numpy(float)
    x['D']=d[[f'axisD[{a}]' for a in range(2)]].to_numpy(float)
    x['motor']=d[[f'motor[{a}]' for a in range(4)]].to_numpy(float)
    x['rpm']=d[[f'eRPM[{a}]' for a in range(4)]].to_numpy(float)*200/int(h['motor_poles'])
    x['th']=(d['rcCommand[3]'].to_numpy(float)-1000)/10
    x['volt']=d.vbatLatest.to_numpy(float)/100;x['current']=d.amperageLatest.to_numpy(float)/100
    x['acc']=np.linalg.norm(d[[f'accSmooth[{a}]' for a in range(3)]].to_numpy(float),axis=1)/int(h['acc_1G'])
    x['speed']=np.interp(t,(g.time.to_numpy()-d.time.iloc[0])/1e6,g.GPS_speed.to_numpy()*.036)
    for label,limits in [('shake',[8,80]),('high',[100,450])]:
        filt=butter(3,limits,btype='bandpass',fs=fs,output='sos')
        for field in ['gyro','raw','D','sp']:
            x[label+'_'+field]=sosfiltfilt(filt,x[field],axis=0)
        x[label+'_err']=x[label+'_gyro']-x[label+'_sp']
    x['env']=np.sqrt(np.maximum(0,uniform_filter1d(x['shake_err']**2,size=round(.15*fs),axis=0)))
    x['sp_env']=np.sqrt(np.maximum(0,uniform_filter1d(x['shake_sp']**2,size=round(.15*fs),axis=0)))
    x['usable']=(t>5)&(t<t[-1]-5)&(maximum_filter1d(x['acc'],size=round(2*fs))<10)
    return x

def stats(x,start,end):
    m=(x['t']>=start)&(x['t']<end)
    motor_min,motor_max=map(float,x['h']['motorOutput'].split(','))
    r={'file':x['name'],'group':x['group'],'start':start,'end':end,'th_mean':float(x['th'][m].mean()),'th_std':float(x['th'][m].std()),'speed':float(x['speed'][m].mean()),'voltage':float(x['volt'][m].mean()),'sp_max':float(abs(x['sp'][m]).max()),'acc_max':float(x['acc'][m].max()),'current':float(x['current'][m].mean()),'rpm_mean':float(x['rpm'][m].mean()),'rpm_min':float(x['rpm'][m].min()),'motor_top_pct':float(100*np.mean(np.any(x['motor'][m]>=motor_max,axis=1))),'motor_bottom_pct':float(100*np.mean(np.any(x['motor'][m]<=motor_min,axis=1)))}
    for field in ['shake_err','shake_gyro','shake_sp','high_gyro','high_raw','high_D','D']:
        val=rms(x[field][m])
        for a,v in enumerate(val):r[field+'_'+['roll','pitch','yaw'][a]]=float(v)
    r['shake_combined']=float(np.sqrt(np.mean(x['shake_err'][m,:2]**2)))
    r['shake_peak']=float(np.max(x['env'][m,:2]))
    r['shake_peak_t']=float(x['t'][np.flatnonzero(m)[np.argmax(np.max(x['env'][m,:2],axis=1))]])
    r['shake_time_gt8']=float(np.mean(np.max(x['env'][m,:2],axis=1)>8))
    return r

def plot_event(x,center,path,title):
    t=x['t'];m=(t>=center-1.7)&(t<=center+1.7)
    fig,axs=plt.subplots(6,1,figsize=(12,12),sharex=True,layout='constrained')
    axs[0].plot(t[m],x['th'][m]);axs[0].set_ylabel('Stick throttle (%)')
    for a in range(2):
        axs[a+1].plot(t[m],x['sp'][m,a],label='Setpoint',color='black',lw=1)
        axs[a+1].plot(t[m],x['gyro'][m,a],label='Gyro',lw=.8)
        axs[a+1].set_ylabel(['Roll','Pitch'][a]+' (deg/s)');axs[a+1].legend(loc='upper right')
    axs[3].plot(t[m],x['env'][m,0],label='Roll');axs[3].plot(t[m],x['env'][m,1],label='Pitch');axs[3].legend();axs[3].set_ylabel('8-80 Hz error\nRMS (deg/s)')
    for a in range(2):axs[4].plot(t[m],x['D'][m,a],label=['Roll','Pitch'][a],lw=.7)
    axs[4].legend();axs[4].set_ylabel('D contribution')
    for a in range(4):axs[5].plot(t[m],x['rpm'][m,a],label=f'M{a+1}',lw=.7)
    axs[5].legend(ncol=4);axs[5].set_ylabel('Mechanical RPM');axs[5].set_xlabel('Seconds since first recorded sample')
    for ax in axs:ax.grid(alpha=.2);ax.axvline(center,ls='--',color='gray',alpha=.5)
    fig.suptitle(title);fig.savefig(path,dpi=140);plt.close(fig)

def main():
    windows=[];recoveries=[];candidates=[];summary=[]
    for name in ['LOG00001','LOG00002','LOG00004','LOG00006','LOG00007']:
        x=load(name);t=x['t'];fs=x['fs'];th=x['th'];sp=x['sp']
        # Independent non-overlapping half-second windows; eligibility uses commands/flight state, not error.
        for start in np.arange(5,t[-1]-5.5,.5):
            m=(t>=start)&(t<start+.5)
            if not x['usable'][m].all():continue
            if not (10<th[m].mean()<65 and x['speed'][m].mean()>10 and abs(sp[m]).max()<180):continue
            r=stats(x,float(start),float(start+.5))
            if max(r['shake_sp_roll'],r['shake_sp_pitch'])>5:continue
            windows.append(r)
        # Recovery trigger = first crossing 20% after <10%, with >=0.10 s low throttle in last 1.5 s.
        # At least 0.25 s of the first 0.5 s after trigger must remain above 20%.
        crossings=np.flatnonzero((th[1:]>=20)&(th[:-1]<20))+1;last=-10
        for p in crossings:
            now=t[p]
            if now-last<1.5 or now<6 or now>t[-1]-6:continue
            pre=(t>=now-1.5)&(t<now);post=(t>=now+.05)&(t<now+1.05);early=(t>=now)&(t<now+.5)
            if np.sum(th[pre]<10)<.10*fs or np.mean(th[early]>=20)<.5:continue
            last=now
            r=stats(x,float(now+.05),float(now+1.05));r['trigger']=float(now)
            r['pre_th_min']=float(th[pre].min());r['pre_speed']=float(x['speed'][pre].mean());r['pre_sp_max']=float(abs(sp[pre]).max());r['pre_acc_max']=float(x['acc'][pre].max());r['pre_rpm_min']=float(x['rpm'][pre].min())
            r['eligible']=bool(x['usable'][post].all() and x['speed'][post].mean()>10 and abs(sp[post]).max()<250 and max(r['shake_sp_roll'],r['shake_sp_pitch'])<8 and th[post].mean()<70)
            recoveries.append(r)
        # Descriptive shake shortlist, never used as the sole comparison sample.
        eligible=x['usable']&(maximum_filter1d(np.max(abs(sp),axis=1),size=round(.4*fs))<180)&(np.max(x['sp_env'][:,:2],axis=1)<8)&(x['speed']>10)&(th>10)
        score=np.max(x['env'][:,:2],axis=1).copy();score[~eligible]=0
        peaks,_=find_peaks(score,height=5,distance=round(1.2*fs),prominence=2)
        cs=[]
        for p in peaks:
            r=stats(x,float(t[p]-.2),float(t[p]+.2));r['peak']=float(t[p]);r['score']=float(score[p]);cs.append(r)
        cs.sort(key=lambda r:r['score'],reverse=True);candidates.extend(cs)
        for r in cs[:3]:plot_event(x,r['peak'],OUT/f'{name}_shake_{r["peak"]:.2f}.png',f'{name} | {x["group"]} | shake candidate {r["peak"]:.2f}s')
        summary.append({'file':name,'group':x['group'],'usable_s':float(x['usable'].sum()/fs),'window_count':sum(r['file']==name for r in windows),'recovery_count':sum(r['file']==name and r['eligible'] for r in recoveries),'shake_candidate_count':len(cs),'top_shakes':[{k:r[k] for k in ['peak','score','th_mean','sp_max']} for r in cs[:5]]})
        # Flight overview incl endings and impacts.
        fig,ax=plt.subplots(5,1,figsize=(12,10),sharex=True,layout='constrained')
        ax[0].plot(t[::40],th[::40]);ax[0].set_ylabel('Throttle (%)')
        ax[1].plot(t[::40],x['speed'][::40]);ax[1].set_ylabel('GPS km/h')
        ax[2].plot(t[::40],x['volt'][::40]);ax[2].set_ylabel('Battery V')
        ax[3].plot(t[::10],np.max(x['env'][::10,:2],axis=1));ax[3].set_ylabel('Error 8-80 Hz\nRMS deg/s');ax[3].set_ylim(0,50)
        ax[4].plot(t[::5],x['acc'][::5]);ax[4].set_ylabel('Acceleration g');ax[4].set_xlabel('Seconds since first recorded sample')
        for a in ax:a.grid(alpha=.2)
        fig.suptitle(f'{name} | {x["group"]} | {t[-1]:.1f}s');fig.savefig(OUT/f'{name}_overview.png',dpi=130);plt.close(fig)
    for name,rows in [('windows',windows),('recoveries',recoveries),('shake_candidates',candidates)]:
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)
    (OUT/'flight_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
    for title,df in [('WINDOWS',pd.DataFrame(windows)),('RECOVERIES',pd.DataFrame([r for r in recoveries if r['eligible']]))]:
        print(title,df.groupby('group')[['shake_combined','shake_peak','shake_time_gt8','high_gyro_roll','high_gyro_pitch','high_D_roll','high_D_pitch','th_mean','speed','sp_max']].median().to_json())

if __name__=='__main__':main()
