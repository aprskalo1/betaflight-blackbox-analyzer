"""Motor-speed screens before and after the crash; flags are candidates, not diagnoses."""
import json
import post_crash as pc
from post_crash import np,pd,di,BASE,OUT
from scipy.ndimage import minimum_filter1d,maximum_filter1d
from scipy.signal import find_peaks
from scipy.optimize import linear_sum_assignment

def investigate(name):
    x=di.load(name,BASE);t=x['t'];fs=x['fs'];rpm=x['rpm'];cmd=x['motor'];valid=x['usable'].copy()
    # Do not use any gap-adjacent samples for lagged comparisons.
    for p in np.flatnonzero(np.diff(t)>.005):valid[(t>=t[p]-.2)&(t<=t[p+1]+.2)]=False
    result={'file':name,'valid_seconds':float(valid.sum()/fs),'motor_summary':[],'rapid_drop_candidates':[],'stable_command_drop_candidates':[],'rapid_rise_candidates':[]}
    for a in range(4):
        result['motor_summary'].append({'motor':a+1,'min_rpm':float(rpm[valid,a].min()),'max_rpm':float(rpm[valid,a].max()),'rpm_percentiles':np.percentile(rpm[valid,a],[1,50,99]).tolist(),'zero_samples':int(np.sum(rpm[valid,a]==0)),'time_below2500_s':float(np.sum(valid&(rpm[:,a]<2500))/fs)})
        lag=round(.02*fs);prior=np.roll(rpm[:,a],lag);ratio=rpm[:,a]/np.maximum(prior,1)
        priorcmd=np.roll(cmd[:,a],lag)
        eligible=valid&np.roll(valid,lag)&(t>.1)&(prior>8000)&(cmd[:,a]>300)&(cmd[:,a]>=.8*priorcmd)
        # A stable-command subset accounts for motor response delayed after earlier braking.
        size=round(.08*fs);lo=minimum_filter1d(cmd[:,a],size=size,origin=(size-1)//2);hi=maximum_filter1d(cmd[:,a],size=size,origin=(size-1)//2)
        stable=(hi-lo<.2*np.maximum(hi,1))&(lo>300)
        for field,mask,score in [('rapid_drop_candidates',eligible&(ratio<.6),1-ratio),('stable_command_drop_candidates',eligible&stable&(ratio<.6),1-ratio),('rapid_rise_candidates',eligible&stable&(ratio>1.4),ratio-1)]:
            values=np.where(mask,score,0);peaks,_=find_peaks(values,height=.4,distance=round(.4*fs))
            for p in sorted(peaks,key=lambda p:values[p],reverse=True)[:8]:
                m=(t>=t[p]-.1)&(t<=t[p]+.1)
                result[field].append({'motor':a+1,'t':float(t[p]),'start_t':float(t[p-lag]),'rpm_before':float(prior[p]),'rpm_after':float(rpm[p,a]),'command_before':float(priorcmd[p]),'command_after':float(cmd[p,a]),'prior80ms_command_min':float(lo[p]),'prior80ms_command_max':float(hi[p]),'throttle':float(x['th'][p]),'setpoint':x['sp'][p].tolist(),'max_error_nearby':float(abs(x['gyro'][m]-x['sp'][m]).max())})
    # Half-second low-command segments: compare loading among motors, not just group means.
    windows=[]
    for start in np.arange(5,t[-1]-5.5,.5):
        m=(t>=start)&(t<start+.5)
        if m.sum()<.49*fs or not valid[m].all() or abs(x['sp'][m]).max()>60 or x['th'][m].std()>2 or not(20<x['th'][m].mean()<50):continue
        meanrpm=rpm[m].mean(axis=0);meancmd=cmd[m].mean(axis=0)
        windows.append({'t':float(start),'throttle':float(x['th'][m].mean()),'speed':float(x['speed'][m].mean()),'voltage':float(x['volt'][m].mean()),'setpoint_mean':x['sp'][m].mean(axis=0).tolist(),'rpm':meanrpm.tolist(),'command':meancmd.tolist(),'rpm_relative_to_four_mean':(meanrpm/meanrpm.mean()).tolist(),'command_relative_to_four_mean':(meancmd/meancmd.mean()).tolist()})
    result['steady_window_count']=len(windows)
    if windows:
        result['steady_median_rpm_relative_to_four_mean']=np.median([r['rpm_relative_to_four_mean'] for r in windows],axis=0).tolist()
        result['steady_median_command_relative_to_four_mean']=np.median([r['command_relative_to_four_mean'] for r in windows],axis=0).tolist()
    (OUT/f'{name}_steady_motor_windows.json').write_text(json.dumps(windows,indent=2))
    if name=='LOG00011':
        candidates=sorted(result['rapid_drop_candidates'],key=lambda r:r['rpm_after']/r['rpm_before'])
        for r in candidates[:2]:pc.event(x,r['t']-.3,r['t']+.3,f'rpm_drop_M{r["motor"]}_{r["t"]:.2f}s')
    return result

if __name__=='__main__':
    out=[investigate(n) for n in ['LOG00008','LOG00009','LOG00011']]
    (OUT/'motor_response.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
    post=json.loads((OUT/'LOG00011_steady_motor_windows.json').read_text());matched=[]
    def covars(rows):return np.array([[r['throttle'],r['speed'],r['voltage'],*r['setpoint_mean']] for r in rows])
    for name in ['LOG00008','LOG00009']:
        pre=json.loads((OUT/f'{name}_steady_motor_windows.json').read_text())
        delta=(covars(pre)[:,None,:]-covars(post)[None,:,:])/np.array([5,10,.7,20,20,20])
        cost=np.sqrt(np.mean(delta**2,axis=2));cost[np.max(abs(delta),axis=2)>1]=1e6
        ai,bi=linear_sum_assignment(cost);ok=cost[ai,bi]<1e5;aa=[pre[i] for i in ai[ok]];bb=[post[i] for i in bi[ok]]
        matched.append({'before_file':name,'after_file':'LOG00011','pairs':len(aa),'before':{k:np.median([r[k] for r in aa],axis=0).tolist() for k in ['rpm_relative_to_four_mean','command_relative_to_four_mean']},'after':{k:np.median([r[k] for r in bb],axis=0).tolist() for k in ['rpm_relative_to_four_mean','command_relative_to_four_mean']},'pairs_data':list(zip(aa,bb))})
    (OUT/'matched_motor_balance.json').write_text(json.dumps(matched,indent=2))
