"""Short motor-correction bursts, including intervals omitted from steady-flight matching."""
import json
import post_crash as pc
from post_crash import np,plt,di,BASE,OUT,uniform_filter1d
from scipy.signal import butter,sosfiltfilt,find_peaks,welch
from scipy.ndimage import maximum_filter1d

def inspect(name):
    x=di.load(name,BASE);t=x['t'];fs=x['fs']
    # Remove collective command to concentrate on differential attitude corrections.
    differential=x['motor']-x['motor'].mean(axis=1,keepdims=True)
    hp=sosfiltfilt(butter(3,[100,450],btype='bandpass',fs=fs,output='sos'),differential,axis=0)
    env=np.sqrt(np.maximum(0,uniform_filter1d(np.mean(hp**2,axis=1),size=round(.1*fs))))
    valid=x['usable'];quiet=valid&(maximum_filter1d(np.max(abs(x['sp']),axis=1),size=round(.4*fs))<180)&(np.max(x['sp_env'][:,:2],axis=1)<8)
    def extract(mask):
        peaks,_=find_peaks(env,distance=round(1.5*fs),prominence=2)
        peaks=sorted([p for p in peaks if mask[p]],key=lambda p:env[p],reverse=True)[:6]
        rows=[]
        for p in peaks:
            m=(t>=t[p]-.15)&(t<=t[p]+.15)
            f,power=welch(differential[m],fs=fs,nperseg=min(256,m.sum()),axis=0)
            band=(f>=100)&(f<=450);k=np.flatnonzero(band)[np.argmax(power[band].mean(axis=1))]
            rows.append({'t':float(t[p]),'motor_correction_rms_units':float(env[p]),'motor_correction_percent_of_range':float(env[p]/1999*100),'dominant_recorded_correction_hz':float(f[k]),'throttle':float(x['th'][p]),'rpm':x['rpm'][p].tolist(),'command':x['motor'][p].tolist(),'setpoint':x['sp'][p].tolist(),'gyro':x['gyro'][p].tolist(),'D_peak_abs':float(abs(x['D'][m]).max()),'error_peak_abs':float(abs(x['gyro'][m]-x['sp'][m]).max()),'acc_peak_g':float(x['acc'][m].max())})
        return rows
    out={'file':name,'manual_motor_hf_rms_percentiles':dict(zip(['p50','p90','p99','max'],np.percentile(env[valid],[50,90,99,100]).tolist())),'all_bursts':extract(valid),'low_command_bursts':extract(quiet)}
    if name=='LOG00011':
        for r in out['low_command_bursts'][:3]:
            pc.event(x,r['t']-.7,r['t']+.7,f'corrections_{r["t"]:.2f}s')
        c=out['low_command_bursts'][0]['t'];m=(t>=c-.1)&(t<=c+.1)
        fig,axs=plt.subplots(3,1,figsize=(12,7),sharex=True,layout='constrained')
        for a in range(4):axs[0].plot(t[m],x['motor'][m,a],label=f'M{a+1}')
        for a in range(2):
            axs[1].plot(t[m],x['D'][m,a],label=['Roll','Pitch'][a])
            axs[2].plot(t[m],x['gyro'][m,a]-x['sp'][m,a],label=['Roll','Pitch'][a])
        for ax in axs:ax.grid(alpha=.2);ax.legend(ncol=4)
        axs[0].set_ylabel('Motor command');axs[1].set_ylabel('D contribution');axs[2].set_ylabel('Tracking error deg/s');axs[-1].set_xlabel('Seconds since first recorded sample')
        fig.suptitle(f'LOG00011 short correction burst at {c:.3f}s\nRecorded corrections; acoustic pitch and prop slip are not measured')
        fig.savefig(OUT/'correction_detail.png',dpi=160);plt.close(fig)
    return out

if __name__=='__main__':
    results=[inspect(n) for n in ['LOG00008','LOG00011']]
    (OUT/'motor_bursts.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
