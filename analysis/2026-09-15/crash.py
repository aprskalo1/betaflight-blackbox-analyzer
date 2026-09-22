"""Inspect raw crash signals without filtering or interpolating across missing frames."""
from pathlib import Path
import sys, json
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'2026-09-13'))
from compare import np,pd,plt,find_peaks,header
OUT=BASE/'crash';OUT.mkdir(exist_ok=True)

def load(name):
    d=pd.read_csv(BASE/'decoded'/f'{name}.I.csv');h=header(name,BASE)
    t=(d.time.to_numpy()-d.time.iloc[0])/1e6
    x={'name':name,'d':d,'t':t,'h':h}
    for key,field,n in [('gyro','gyroADC',3),('raw','gyroUnfilt',3),('sp','setpoint',3),('rpm','eRPM',4),('motor','motor',4)]:
        x[key]=d[[f'{field}[{a}]' for a in range(n)]].to_numpy(float)
    x['rpm']*=200/int(h['motor_poles'])
    x['acc']=np.linalg.norm(d[[f'accSmooth[{a}]' for a in range(3)]].to_numpy(float),axis=1)/int(h['acc_1G'])
    x['th']=(d['rcCommand[3]'].to_numpy()-1000)/10
    x['error']=np.max(abs(x['gyro']-x['sp']),axis=1)
    x['g']=pd.read_csv(BASE/'decoded'/f'{name}.G.csv')
    x['s']=pd.read_csv(BASE/'decoded'/f'{name}.S.csv')
    x['meta']=json.loads((BASE/'decoded'/f'{name}.metadata.json').read_text())
    x['gaps']=[(float(t[p]),float(t[p+1])) for p in np.flatnonzero(np.diff(t)>.005)]
    return x

def snap(x,p):
    d=x['d'];g=x['g'];gps=g[g.time<=d.time.iloc[p]].tail(1)
    return {'t':float(x['t'][p]),'throttle_pct':float(x['th'][p]),'gyro':x['gyro'][p].tolist(),'raw':x['raw'][p].tolist(),'setpoint':x['sp'][p].tolist(),'acc_g':float(x['acc'][p]),'motor':x['motor'][p].tolist(),'rpm':x['rpm'][p].tolist(),'voltage':float(d.vbatLatest.iloc[p]/100),'current':float(d.amperageLatest.iloc[p]/100),'gps_kmh':float(gps.GPS_speed.iloc[0]*.036) if len(gps) else None,'gps_age_s':float((d.time.iloc[p]-gps.time.iloc[0])/1e6) if len(gps) else None}

def plot(x,start,end,label):
    t=x['t'];m=(t>=start)&(t<=end);d=x['d'];fig,axs=plt.subplots(8,1,figsize=(13,14),sharex=True,layout='constrained')
    def draw(ax,values,**kwargs):
        v=np.asarray(values,dtype=float).copy()
        for a,b in x['gaps']:v[(t>=a)&(t<=b)]=np.nan
        ax.plot(t[m],v[m],**kwargs)
    draw(axs[0],x['th']);axs[0].set_ylabel('Stick throttle %')
    for a in range(3):
        draw(axs[a+1],x['sp'][:,a],color='black',label='Setpoint',lw=1)
        draw(axs[a+1],x['gyro'][:,a],label='Gyro',lw=.8)
        draw(axs[a+1],x['raw'][:,a],label='Raw gyro',alpha=.4,lw=.6)
        axs[a+1].set_ylabel(['Roll','Pitch','Yaw'][a]+' deg/s');axs[a+1].legend(ncol=3,fontsize=8)
    draw(axs[4],x['acc']);axs[4].set_ylabel('Accel magnitude g')
    for a in range(4):
        draw(axs[5],x['motor'][:,a],label=f'M{a+1}',lw=.8)
        draw(axs[6],x['rpm'][:,a],label=f'M{a+1}',lw=.8)
    axs[5].set_ylabel('Motor command');axs[6].set_ylabel('Reported RPM')
    for ax in axs[5:7]:ax.legend(ncol=4,fontsize=8)
    draw(axs[7],d.vbatLatest.to_numpy()/100);axs[7].set_ylabel('Battery V')
    ax2=axs[7].twinx();draw(ax2,d.amperageLatest.to_numpy()/100,color='tab:orange');ax2.set_ylabel('Current A')
    for ax in axs:
        ax.grid(alpha=.2)
        for a,b in x['gaps']:
            if a<end and b>start:ax.axvspan(a,b,color='red',alpha=.15)
    axs[-1].set_xlabel('Seconds since first recorded sample')
    fig.suptitle(f'{x["name"]} | {label} | Idle 35, Damping 1.10\nRed shading: missing samples; M1–M4 are logical motor channels')
    fig.savefig(OUT/f'{x["name"]}_{label}.png',dpi=140);plt.close(fig)

def main():
    reports=[]
    for name in ['LOG00009','LOG00010','LOG00011']:
        x=load(name);t=x['t']
        peaks,_=find_peaks(x['error'],height=200,distance=700,prominence=100)
        r={'file':name,'gaps':x['gaps'],'tracking_events':[snap(x,p) for p in peaks],'last_samples':[snap(x,np.argmin(abs(t-stamp))) for stamp in [t[-1]-5,t[-1]-2,t[-1]-.5,t[-1]-.1,t[-1]]],'max_acc':snap(x,int(np.argmax(x['acc']))),'gap_edges':[[snap(x,int(np.argmin(abs(t-a)))),snap(x,int(np.argmin(abs(t-b))))] for a,b in x['gaps']]}
        reports.append(r)
        if name=='LOG00009':
            m=t>t[-1]-5
            r['last5s']={'max_tracking_error_dps':float(x['error'][m].max()),'max_acc_g':float(x['acc'][m].max()),'min_rpm':float(x['rpm'][m].min()),'min_voltage':float(x['d'].vbatLatest[m].min()/100)}
            plot(x,21.8,24.5,'recording_gap')
        if name=='LOG00011':
            search=t>254.5
            checks={'zero_throttle':x['th']<1,'acc_over_2g':x['acc']>2,'raw_tracking_error_over100':np.max(abs(x['raw']-x['sp']),axis=1)>100,'gyro_error_over100':x['error']>100,'motor_max':np.any(x['motor']>=2047,axis=1)}
            onset={k:snap(x,np.flatnonzero(search & m)[0]) for k,m in checks.items() if np.any(search&m)}
            (OUT/'impact_thresholds.json').write_text(json.dumps(onset,indent=2))
            plot(x,254.7,255.077,'impact_detail')
            rows=x['d'][t>=254.7].copy();rows.insert(0,'elapsed_s',t[t>=254.7]);rows.to_csv(OUT/'LOG00011_impact_samples.csv',index=False)
        if name=='LOG00010':continue
        plot(x,0,float(t[-1]),'overview')
        plot(x,max(0,float(t[-1])-8),float(t[-1]),'ending')
        for i,p in enumerate(sorted(peaks,key=lambda p:x['error'][p],reverse=True)[:2],1):plot(x,max(0,float(t[p])-1.5),min(float(t[-1]),float(t[p])+2),f'tracking_{i}')
    (OUT/'scan.json').write_text(json.dumps(reports,indent=2))
    print(json.dumps(reports,indent=2))

if __name__=='__main__':main()
