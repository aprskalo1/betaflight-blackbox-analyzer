"""First-battery manoeuvre/recovery search; acoustic identification is unavailable."""
from pathlib import Path
import sys,json
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'2026-09-15'))
import dynamic_idle as di
from dynamic_idle import np,pd,plt,butter,sosfiltfilt,find_peaks
from scipy.ndimage import uniform_filter1d, binary_closing
OUT=BASE/'split_s';OUT.mkdir(exist_ok=True)

def runs(mask):
    a=np.diff(np.r_[False,mask,False].astype(int))
    return list(zip(np.flatnonzero(a==1),np.flatnonzero(a==-1)))

def main():
    x=di.load('LOG00002',BASE);t=x['t'];fs=x['fs'];th=x['th'];gyro=x['gyro'];sp=x['sp']
    if np.max(np.diff(t))>.005:raise ValueError('Discontinuous data')
    dt=np.r_[0,np.diff(t)]
    diff=x['motor']-x['motor'].mean(axis=1,keepdims=True)
    motorhf=sosfiltfilt(butter(3,[100,450],btype='bandpass',fs=fs,output='sos'),diff,axis=0)
    env=np.sqrt(np.maximum(0,uniform_filter1d(np.mean(motorhf**2,axis=1),size=round(.05*fs))))
    shake=x['env'][:,:2].max(axis=1)
    # Group fast rotations over short pauses. Body-axis integrals describe
    # angular travel; they are not Euler angles or proof of horizontal attitude.
    fast=binary_closing(np.max(abs(gyro[:,:2]),axis=1)>200,structure=np.ones(round(.12*fs)))
    rotations=[]
    for a,b in runs(fast):
        if t[b-1]-t[a]<.025:continue
        m=slice(max(0,a-round(.12*fs)),min(len(t),b+round(.12*fs)))
        rotations.append({'start':float(t[a]),'end':float(t[b-1]),'body_axis_signed_deg':np.sum(gyro[m]*dt[m,None],axis=0).tolist(),'peak_rate':np.max(abs(gyro[m]),axis=0).tolist()})
    # Throttle rises through 20%, recently cut <5%, then reaches >=35%.
    rows=[];last=-10
    for p in np.flatnonzero((th[1:]>=20)&(th[:-1]<20))+1:
        now=t[p]
        if now<5 or now>t[-1]-5 or now-last<.7:continue
        pre=(t>=now-2)&(t<now);post=(t>=now)&(t<now+.6)
        if np.sum(th[pre]<5)/fs<.08 or th[post].max()<35:continue
        last=now
        # Peak within recovery, not the preceding deliberate fast rotation.
        region=post&(np.max(abs(sp),axis=1)<200)
        if not region.any():continue
        ids=np.flatnonzero(region);peak=ids[np.argmax(env[region])]
        # Duration of a local motor-correction envelope above fixed threshold.
        a=peak;b=peak
        while a>0 and env[a-1]>15 and t[peak]-t[a-1]<1:a-=1
        while b+1<len(t) and env[b+1]>15 and t[b+1]-t[peak]<1:b+=1
        prior=(t>=now-5)&(t<now)
        near=(t>=t[peak]-.1)&(t<=t[peak]+.1)
        r={'trigger':float(now),'peak_t':float(t[peak]),'motor_hf_peak':float(env[peak]),'burst_above15_start':float(t[a]),'burst_above15_end':float(t[b]),'burst_above15_duration':float(t[b]-t[a]),'throttle_peak':float(th[post].max()),'throttle_at_burst':float(th[peak]),'shake_peak':float(shake[post].max()),'raw_tracking_error_peak_nearby':float(abs(gyro[near]-sp[near]).max()),'sp_at_burst':sp[peak].tolist(),'rpm_at_burst':x['rpm'][peak].tolist(),'previous_rotations':[v for v in rotations if v['end']>=now-5 and v['start']<now], 'pre5_body_axis_signed_deg':np.sum(gyro[prior]*dt[prior,None],axis=0).tolist(),'baro_delta_pre2_m':float((x['d'].baroAlt.to_numpy()[p]-x['d'].baroAlt.to_numpy()[np.flatnonzero(pre)[0]])/100)}
        r['duration_sensitivity_ms']={}
        for threshold in [10,15,20]:
            aa=peak;bb=peak
            while aa>0 and env[aa-1]>threshold and t[peak]-t[aa-1]<1:aa-=1
            while bb+1<len(t) and env[bb+1]>threshold and t[bb+1]-t[peak]<1:bb+=1
            r['duration_sensitivity_ms'][str(threshold)]=float((t[bb]-t[aa])*1000)
        rows.append(r)
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2))
    (OUT/'rotations.json').write_text(json.dumps(rotations,indent=2))
    # Save all recovery candidates so chronology and weak/strong events remain
    # available; no selection of only dramatic outcomes for a comparison.
    for r in sorted(rows,key=lambda r:r['motor_hf_peak'],reverse=True)[:12]:
        c=r['peak_t'];m=(t>=c-5)&(t<=c+1)
        fig,axs=plt.subplots(6,1,figsize=(13,12),sharex=True,layout='constrained')
        axs[0].plot(t[m],th[m]);axs[0].set_ylabel('Throttle %')
        for a in range(3):axs[1].plot(t[m],gyro[m,a],label=['Roll','Pitch','Yaw'][a],lw=.8)
        axs[1].set_ylabel('Rotation deg/s');axs[1].legend(ncol=3)
        for a in range(2):axs[2].plot(t[m],gyro[m,a]-sp[m,a],label=['Roll','Pitch'][a],lw=.7)
        axs[2].set_ylabel('Tracking error\ndeg/s');axs[2].legend(ncol=2)
        axs[3].plot(t[m],env[m]);axs[3].axhline(15,color='gray',ls=':');axs[3].set_ylabel('100-450 Hz motor\ncorrection RMS')
        for a in range(4):axs[4].plot(t[m],x['rpm'][m,a],label=f'M{a+1}',lw=.8)
        axs[4].set_ylabel('Motor RPM');axs[4].legend(ncol=4)
        axs[5].plot(t[m],x['d'].baroAlt.to_numpy()[m]/100);axs[5].set_ylabel('Baro altitude m')
        for ax in axs:ax.axvline(c,color='gray',ls='--');ax.grid(alpha=.2)
        axs[-1].set_xlabel('Elapsed seconds from first recorded sample')
        fig.suptitle(f'First battery LOG00002 | throttle-recovery correction at {c:.3f}s\nAudio and direct attitude are not recorded; altitude may be affected by airflow')
        fig.savefig(OUT/f'recovery_{c:.2f}.png',dpi=140);plt.close(fig)
    # A compact four-event visual and close-ups for the user's recollection.
    targets=[87.596,97.639,102.305,110.432]
    shortlist=[min(rows,key=lambda r:abs(r['peak_t']-target)) for target in targets]
    fig,axs=plt.subplots(3,4,figsize=(16,8),layout='constrained')
    for col,r in enumerate(shortlist):
        c=r['peak_t'];m=(t>=c-.35)&(t<=c+.45)
        axs[0,col].plot(t[m],th[m],color='black');axs[0,col].set_title(f'LOG00002 {int(c//60)}:{c%60:04.1f}')
        for a in range(2):axs[1,col].plot(t[m],gyro[m,a]-sp[m,a],label=['Roll','Pitch'][a],lw=.8)
        axs[2,col].plot(t[m],env[m]);axs[2,col].axhline(15,color='gray',ls=':')
        axs[2,col].axvspan(r['burst_above15_start'],r['burst_above15_end'],color='orange',alpha=.2)
        for ax in axs[:,col]:ax.axvline(c,color='gray',ls='--');ax.grid(alpha=.2)
        axs[2,col].set_xlabel('Elapsed seconds')
    axs[0,0].set_ylabel('Throttle %');axs[1,0].set_ylabel('Tracking error deg/s');axs[2,0].set_ylabel('Motor correction RMS')
    axs[1,0].legend();fig.suptitle('First battery: short correction bursts as power returns\nShaded duration measures recorded corrections above a threshold, not audible sound duration')
    fig.savefig(OUT/'shortlist_detail.png',dpi=150);plt.close(fig)
    (OUT/'shortlist.json').write_text(json.dumps(shortlist,indent=2))
    print(json.dumps([{k:r[k] for k in ['trigger','peak_t','motor_hf_peak','burst_above15_duration','shake_peak','pre5_body_axis_signed_deg','previous_rotations']} for r in rows],indent=2))

if __name__=='__main__':main()
