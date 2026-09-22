"""First-battery Dynamic Idle comparison, reusing the September 13 signal definitions."""
from pathlib import Path
import sys,json
BASE=Path(__file__).resolve().parent
OLD=BASE.parent/'2026-09-13'
sys.path.insert(0,str(OLD))
import compare as core
from compare import np,pd,plt,butter,sosfiltfilt,find_peaks,maximum_filter1d
from scipy.optimize import linear_sum_assignment
OUT=BASE/'results';OUT.mkdir(exist_ok=True)

def load(name,base):
    x=core.load(name,base)
    x['group']='Idle 35' if x['h']['dyn_idle_min_rpm']=='35' else 'Idle off'
    x['base']=base
    # Exclude all non-ARM-only modes plus two seconds around each mode transition.
    meta=json.loads((base/'decoded'/f'{name}.metadata.json').read_text())
    s=pd.read_csv(base/'decoded'/f'{name}.S.csv')
    times=(s.last_main_time.to_numpy()-x['d'].time.iloc[0])/1e6
    flags=s.flightModeFlags.to_numpy(int)
    x['excluded_modes']=[]
    for i in range(len(times)):
        end=float(times[i+1]) if i+1<len(times) else float(x['t'][-1])
        if flags[i]!=1:
            x['usable']&=~((x['t']>=times[i]-2)&(x['t']<=end+2))
            x['excluded_modes'].append([float(times[i]),end,int(flags[i])])
    x['minrpm']=np.min(x['rpm'],axis=1)
    return x

def stats(x,start,end):
    r=core.stats(x,start,end);m=(x['t']>=start)&(x['t']<end)
    for a,name in enumerate(['roll','pitch']):
        r['motor_activity_'+name]=r['high_D_'+name]
    r['rpm_min_p05']=float(np.percentile(x['minrpm'][m],5))
    return r

def extract(x):
    t=x['t'];fs=x['fs'];th=x['th'];sp=x['sp'];windows=[];rec=[]
    for start in np.arange(5,t[-1]-5.5,.5):
        m=(t>=start)&(t<start+.5)
        if not x['usable'][m].all():continue
        if not (10<th[m].mean()<65 and x['speed'][m].mean()>10 and abs(sp[m]).max()<180):continue
        r=stats(x,float(start),float(start+.5))
        if max(r['shake_sp_roll'],r['shake_sp_pitch'])>5:continue
        windows.append(r)
    crossings=np.flatnonzero((th[1:]>=20)&(th[:-1]<20))+1;last=-10
    for p in crossings:
        now=t[p]
        if now-last<1.5 or now<6 or now>t[-1]-6:continue
        pre=(t>=now-1.5)&(t<now);post=(t>=now+.05)&(t<now+1.05);early=(t>=now)&(t<now+.5)
        if np.sum(th[pre]<10)<.10*fs or np.mean(th[early]>=20)<.5:continue
        last=now
        # Apply eligibility to both the approach and recovery so GPS Rescue cannot leak in.
        if not x['usable'][pre|post].all():continue
        r=stats(x,float(now+.05),float(now+1.05));r['trigger']=float(now)
        r['pre_th_min']=float(th[pre].min());r['pre_speed']=float(x['speed'][pre].mean());r['pre_sp_max']=float(abs(sp[pre]).max());r['pre_acc_max']=float(x['acc'][pre].max());r['pre_rpm_min']=float(x['rpm'][pre].min())
        low=pre&(th<10)
        r['pre_low_rpm_p05']=float(np.percentile(x['minrpm'][low],5));r['pre_low_rpm_median']=float(np.median(x['minrpm'][low]))
        r['pre_low_duration']=float(low.sum()/fs)
        r['eligible']=bool(x['speed'][post].mean()>10 and abs(sp[post]).max()<250 and max(r['shake_sp_roll'],r['shake_sp_pitch'])<8 and th[post].mean()<70)
        rec.append(r)
    return windows,rec

def matching(df,cols,scales,limit):
    a=df[df.group=='Idle off'].reset_index(drop=True);b=df[df.group=='Idle 35'].reset_index(drop=True)
    delta=a[cols].to_numpy()[:,None,:]/scales-b[cols].to_numpy()[None,:,:]/scales
    dist=np.sqrt(np.mean(delta**2,axis=2));dist[np.max(abs(delta),axis=2)>limit]=1e6
    ai,bi=linear_sum_assignment(dist);good=dist[ai,bi]<1e5;ai=ai[good];bi=bi[good]
    return a.iloc[ai].reset_index(drop=True),b.iloc[bi].reset_index(drop=True),dist[ai,bi]

def summary(df):
    cols=['shake_combined','shake_peak','shake_time_gt8','high_gyro_roll','high_gyro_pitch','high_D_roll','high_D_pitch','th_mean','speed','sp_max','voltage']
    cols += [c for c in ['pre_low_rpm_p05','pre_low_rpm_median','pre_rpm_min','pre_low_duration','pre_sp_max','pre_speed'] if c in df.columns]
    return {g:{'n':len(d),'median':d[cols].median().to_dict(),'mean':d[cols].mean().to_dict(),'p90':d[cols].quantile(.9).to_dict()} for g,d in df.groupby('group')}

def idle_stats(x):
    out={}
    for label,limit in [('zero',1),('low',10)]:
        m=x['usable']&(x['th']<limit)&(x['speed']>10)
        v=x['minrpm'][m]
        out[label]={'seconds':float(m.sum()/x['fs']),'min_motor_rpm_percentiles':dict(zip(['min','p01','p05','p50','p95'],np.percentile(v,[0,1,5,50,95]).tolist())),'min_motor_below3000_pct':float(100*np.mean(v<3000)),'min_motor_below3500_pct':float(100*np.mean(v<3500)),'any_command_below158_pct':float(100*np.mean(np.any(x['motor'][m]<158,axis=1))),'max_axis_error_rms':float(np.max(np.sqrt(np.mean((x['gyro'][m]-x['sp'][m])**2,axis=0))))}
    return out

def main():
    xs={name:load(name,base) for name,base in [('LOG00006',OLD),('LOG00007',OLD),('LOG00008',BASE)]}
    ws=[];rs=[];idle={};candidates=[]
    for name,x in xs.items():
        w,r=extract(x);ws+=w;rs+=r;idle[name]=idle_stats(x)
        t=x['t'];sp=x['sp'];fs=x['fs']
        eligible=x['usable']&(maximum_filter1d(np.max(abs(sp),axis=1),size=round(.4*fs))<180)&(np.max(x['sp_env'][:,:2],axis=1)<8)&(x['speed']>10)&(x['th']>10)
        score=np.max(x['env'][:,:2],axis=1).copy();score[~eligible]=0
        peaks,_=find_peaks(score,height=5,distance=round(1.2*fs),prominence=2)
        for p in peaks:candidates.append({'file':name,'group':x['group'],'t':float(t[p]),'score':float(score[p])})
    windows=pd.DataFrame(ws);allrec=pd.DataFrame(rs);rec=allrec[allrec.eligible].copy()
    windows.to_csv(OUT/'windows.csv',index=False);allrec.to_csv(OUT/'recoveries.csv',index=False);pd.DataFrame(candidates).to_csv(OUT/'shake_candidates.csv',index=False)
    wo,wn,wd=matching(windows,['th_mean','speed','sp_max','voltage','th_std'],np.array([5,10,50,.7,5]),1)
    ro,rn,rd=matching(rec,['th_mean','speed','sp_max','voltage','pre_sp_max','pre_speed'],np.array([7,10,80,.8,300,12]),1.5)
    results={'headers_vs_13sep_log7':{k:[xs['LOG00007']['h'].get(k),xs['LOG00008']['h'].get(k)] for k in xs['LOG00007']['h'].keys()|xs['LOG00008']['h'].keys() if xs['LOG00007']['h'].get(k)!=xs['LOG00008']['h'].get(k)},'files':{n:{'duration_s':float(x['t'][-1]),'usable_s':float(x['usable'].sum()/x['fs']),'excluded_modes':x['excluded_modes']} for n,x in xs.items()},'idle_by_file':idle,'unmatched_windows':summary(windows),'unmatched_recoveries':summary(rec),'matched_windows':summary(pd.concat([wo,wn])),'matched_recoveries':summary(pd.concat([ro,rn])),'matched_recoveries_lower_shake_count':int(np.sum(rn.shake_combined.to_numpy()<ro.shake_combined.to_numpy())),'matched_recoveries_lower_peak_count':int(np.sum(rn.shake_peak.to_numpy()<ro.shake_peak.to_numpy()))}
    pairs=[{'distance':float(rd[i]),'off':ro.iloc[i].to_dict(),'on':rn.iloc[i].to_dict()} for i in range(len(ro))]
    (OUT/'matched_recoveries.json').write_text(json.dumps(pairs,indent=2))
    for i,pair in enumerate(sorted(pairs,key=lambda r:r['distance'])[:3],1):
        for label in ['off','on']:
            r=pair[label];x=xs[r['file']]
            core.plot_event(x,r['shake_peak_t'],OUT/f'matched_{i}_{label}.png',f'Matched recovery {i} | {r["file"]} | {x["group"]} | throttle crossing {r["trigger"]:.2f}s')
    for r in sorted([r for r in candidates if r['file']=='LOG00008'],key=lambda r:r['score'],reverse=True)[:3]:
        core.plot_event(xs['LOG00008'],r['t'],OUT/f'LOG00008_shake_{r["t"]:.2f}.png',f'LOG00008 | Dynamic Idle 35 | residual shake candidate at {r["t"]:.2f}s')
    # First-flight overview; shading denotes automatic rescue excluded from comparisons.
    x=xs['LOG00008'];t=x['t'];fig,axs=plt.subplots(5,1,figsize=(12,10),sharex=True,layout='constrained')
    axs[0].plot(t[::20],x['th'][::20]);axs[0].set_ylabel('Stick throttle %')
    axs[1].plot(t[::20],x['minrpm'][::20]);axs[1].axhline(3500,ls='--',color='black');axs[1].set_ylabel('Slowest motor RPM')
    axs[2].plot(t[::20],x['speed'][::20]);axs[2].set_ylabel('GPS km/h')
    axs[3].plot(t[::10],np.max(x['env'][::10,:2],axis=1));axs[3].set_ylim(0,40);axs[3].set_ylabel('8-80 Hz error\nRMS deg/s')
    axs[4].plot(t[::10],x['volt'][::10]);axs[4].set_ylabel('Battery V');axs[4].set_xlabel('Seconds since first recorded sample')
    for ax in axs:ax.grid(alpha=.2);ax.axvspan(188.902,208.582,alpha=.15,color='orange')
    fig.suptitle('15 September, first battery | LOG00008 | Damping 1.10 + Dynamic Idle 35\nOrange: GPS Rescue, excluded with transition margins');fig.savefig(OUT/'first_battery_overview.png',dpi=150);plt.close(fig)
    # Side-by-side distributions and the mechanism: minimum RPM during low-throttle periods.
    fig,axs=plt.subplots(1,3,figsize=(13,5),layout='constrained');groups=['Idle off','Idle 35'];colors=['#3577ad','#dc8730'];rng=np.random.default_rng(15)
    for ax,df,field,title in [(axs[0],pd.concat([ro,rn]),'shake_combined','Matched throttle recoveries'),(axs[1],pd.concat([ro,rn]),'pre_low_rpm_p05','Slowest motor before recovery'),(axs[2],pd.concat([wo,wn]),'high_D_pitch','Matched windows: pitch D activity')]:
        for i,g in enumerate(groups):
            v=df[df.group==g][field].to_numpy();ax.scatter(i+rng.uniform(-.12,.12,len(v)),v,s=14,alpha=.45,color=colors[i]);ax.plot([i-.2,i+.2],[np.median(v)]*2,color='black',lw=3)
        ax.set_xticks([0,1],groups);ax.set_title(title,fontsize=11);ax.grid(axis='y',alpha=.2)
    axs[0].set_ylabel('8-80 Hz roll/pitch error RMS (deg/s)');axs[1].set_ylabel('5th percentile minimum RPM');axs[1].axhline(3500,ls='--',color='gray');axs[2].set_ylabel('100-450 Hz D RMS (units)')
    fig.suptitle('Dynamic Idle off vs 35 | Damping 1.10 in both groups\nTwo earlier batteries vs one new battery; matched events are not independent controlled trials',fontsize=11);fig.savefig(OUT/'comparison.png',dpi=160);plt.close(fig)
    # Robustness to frequency band, subset choice, and matching tolerances.
    sensitivity=[]
    for x in xs.values():
        for band in [(5,40),(15,80)]:
            arr=sosfiltfilt(butter(3,band,btype='bandpass',fs=x['fs'],output='sos'),x['gyro'][:,:2]-x['sp'][:,:2],axis=0)
            for idx,r in rec[rec.file==x['name']].iterrows():
                m=(x['t']>=r.start)&(x['t']<r.end);rec.loc[idx,str(band)]=float(np.sqrt(np.mean(arr[m]**2)))
    for label,sub,tol in [('main',rec,1.5),('stricter_match',rec,1),('low_commands',rec[rec.sp_max<150],1.5),('zero_throttle',rec[rec.pre_th_min<1],1.5)]:
        a,b,dist=matching(sub,['th_mean','speed','sp_max','voltage','pre_sp_max','pre_speed'],np.array([7,10,80,.8,300,12]),tol)
        sensitivity.append({'selection':label,'pairs':len(a),'bands':{field:{'off_median':float(a[field].median()),'on_median':float(b[field].median()),'lower_pairs':int(np.sum(b[field].to_numpy()<a[field].to_numpy()))} for field in ['shake_combined','(5, 40)','(15, 80)']}})
    results['sensitivity']=sensitivity
    (OUT/'comparison.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({'headers':results['headers_vs_13sep_log7'],'idle':idle,'recovery_counts':rec.groupby('group').size().to_dict(),'matched_recoveries':results['matched_recoveries'],'sensitivity':sensitivity},indent=2))

if __name__=='__main__':main()
