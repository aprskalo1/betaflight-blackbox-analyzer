"""Compare pre/post-crash vibration at similar manual-flight operating points."""
import json
import dynamic_idle as di
from dynamic_idle import np,pd,plt,core,BASE
from scipy.signal import welch
from scipy.optimize import linear_sum_assignment
from scipy.ndimage import uniform_filter1d
OUT=BASE/'post_crash';OUT.mkdir(exist_ok=True)

def extract(x):
    rows=[];t=x['t'];fs=x['fs']
    for start in np.arange(5,t[-1]-5.5,.5):
        m=(t>=start)&(t<start+.5)
        if not x['usable'][m].all():continue
        if not(10<x['th'][m].mean()<65 and x['speed'][m].mean()>10 and abs(x['sp'][m]).max()<180):continue
        r=core.stats(x,float(start),float(start+.5))
        if max(r['shake_sp_roll'],r['shake_sp_pitch'])>5:continue
        r['raw_hf']=float(np.sqrt(np.mean(x['high_raw'][m]**2)))
        r['gyro_hf']=float(np.sqrt(np.mean(x['high_gyro'][m]**2)))
        r['D_hf']=float(np.sqrt(np.mean(x['high_D'][m]**2)))
        for a in range(4):r[f'motor{a+1}_rpm']=float(x['rpm'][m,a].mean())
        rows.append(r)
    return pd.DataFrame(rows)

def match(a,b,tol=1):
    cols=['th_mean','speed','sp_max','voltage','th_std','rpm_mean'];scales=np.array([5,10,50,.7,5,1500])
    delta=(a[cols].to_numpy()[:,None,:]-b[cols].to_numpy()[None,:,:])/scales
    dist=np.sqrt(np.mean(delta**2,axis=2));dist[np.max(abs(delta),axis=2)>tol]=1e6
    ai,bi=linear_sum_assignment(dist);ok=dist[ai,bi]<1e5
    return a.iloc[ai[ok]].reset_index(drop=True),b.iloc[bi[ok]].reset_index(drop=True)

def summary(d):
    cols=['raw_hf','gyro_hf','D_hf','shake_combined','th_mean','speed','voltage','rpm_mean']
    cols+=[f'{f}_{a}' for f in ['high_raw','high_gyro','high_D'] for a in (['roll','pitch'] if f=='high_D' else ['roll','pitch','yaw'])]
    return {'n':len(d),'median':d[cols].median().to_dict(),'p90':d[cols].quantile(.9).to_dict()}

def psd(x,df,field):
    vals=[]
    for r in df.itertuples():
        m=(x['t']>=r.start)&(x['t']<r.end)
        f,p=welch(x[field][m],fs=x['fs'],nperseg=256,noverlap=128,axis=0)
        vals.append(p)
    return f,np.median(vals,axis=0)

def event(x,start,end,label):
    t=x['t'];m=(t>=start)&(t<=end);fig,axs=plt.subplots(6,1,figsize=(12,11),sharex=True,layout='constrained')
    axs[0].plot(t[m],x['th'][m]);axs[0].set_ylabel('Stick throttle %')
    for a in range(3):
        axs[1].plot(t[m],x['raw'][m,a],label=['Roll','Pitch','Yaw'][a],lw=.6)
        axs[2].plot(t[m],x['gyro'][m,a]-x['sp'][m,a],label=['Roll','Pitch','Yaw'][a],lw=.7)
    axs[1].set_ylabel('Raw gyro deg/s');axs[2].set_ylabel('Tracking error deg/s')
    for a in range(2):axs[3].plot(t[m],x['D'][m,a],label=['Roll','Pitch'][a],lw=.6)
    axs[3].set_ylabel('D contribution')
    for a in range(4):
        axs[4].plot(t[m],x['motor'][m,a],label=f'M{a+1}',lw=.6)
        axs[5].plot(t[m],x['rpm'][m,a],label=f'M{a+1}',lw=.6)
    axs[4].set_ylabel('Motor command');axs[5].set_ylabel('Reported RPM')
    for ax in axs:
        ax.grid(alpha=.2)
        if ax!=axs[0]:ax.legend(ncol=4,fontsize=8)
    axs[-1].set_xlabel('Seconds since first recorded sample')
    fig.suptitle(f'{x["name"]} | {label} | Idle 35, Damping 1.10')
    fig.savefig(OUT/f'{x["name"]}_{label}.png',dpi=150);plt.close(fig)

def main():
    before=di.load('LOG00008',BASE);after=di.load('LOG00011',BASE)
    a=extract(before);b=extract(after);a.to_csv(OUT/'before_windows.csv',index=False);b.to_csv(OUT/'after_windows.csv',index=False)
    ma,mb=match(a,b)
    ma.to_csv(OUT/'matched_before.csv',index=False);mb.to_csv(OUT/'matched_after.csv',index=False)
    results={'header_changes':{k:[before['h'].get(k),after['h'].get(k)] for k in before['h'].keys()|after['h'].keys() if before['h'].get(k)!=after['h'].get(k)},'unmatched':{'before':summary(a),'after':summary(b)},'matched':{'before':summary(ma),'after':summary(mb)},'higher_after_pairs':{k:int(np.sum(mb[k].to_numpy()>ma[k].to_numpy())) for k in ['raw_hf','gyro_hf','D_hf','shake_combined']},'sensitivity':[]}
    for tol in [.75,1.5]:
        aa,bb=match(a,b,tol)
        results['sensitivity'].append({'tolerance':tol,'before':summary(aa),'after':summary(bb)})
    results['top_after_windows']=b.nlargest(6,'raw_hf')[['start','end','raw_hf','gyro_hf','D_hf','shake_combined','th_mean','sp_max','speed','rpm_mean']].to_dict('records')
    # Choose separated examples based on observed noise; these are descriptive, not comparison selection.
    centers=[]
    for r in b.sort_values('raw_hf',ascending=False).itertuples():
        c=(r.start+r.end)/2
        if all(abs(c-v)>4 for v in centers):
            centers.append(c);event(after,c-.75,c+.75,f'noise_{c:.2f}s')
        if len(centers)==3:break
    results['example_centers']=centers
    fig,axs=plt.subplots(3,1,figsize=(12,9),layout='constrained')
    spectral={}
    for x,df,label,color in [(before,ma,'First battery','#3577ad'),(after,mb,'After crash','#dc8730')]:
        for ax,field in zip(axs,['raw','gyro','D']):
            f,p=psd(x,df,field);power=np.mean(p,axis=1);ax.semilogy(f,power,label=label,color=color)
            mask=(f>=100)&(f<=450);peak=int(np.flatnonzero(mask)[np.argmax(power[mask])]);spectral[label+'_'+field]={'dominant_100_450_hz':float(f[peak]),'power_at_peak':float(power[peak])}
    for ax,label in zip(axs,['Raw gyro','Filtered gyro','D contribution']):ax.set_xlim(20,450);ax.set_ylabel(label+' PSD');ax.grid(alpha=.2);ax.legend()
    axs[-1].set_xlabel('Frequency Hz');fig.suptitle(f'Median window spectra, {len(ma)} matched pairs\nOnly the recorded band is shown; no acoustic recording or motor-specific vibration sensor')
    fig.savefig(OUT/'matched_spectra.png',dpi=150);plt.close(fig);results['spectra']=spectral
    fig,axs=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
    for x,label in [(before,'First battery'),(after,'After crash')]:
        for ax,field in zip(axs,['high_raw','high_gyro','high_D']):
            env=np.sqrt(np.maximum(0,uniform_filter1d(np.mean(x[field]**2,axis=1),size=round(.1*x['fs']))));valid=x['usable'].copy();env[~valid]=np.nan
            ax.plot(x['t'][::30],env[::30],label=label,lw=.8)
    for ax,label in zip(axs,['Raw gyro RMS deg/s','Filtered gyro RMS deg/s','D RMS units']):ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend()
    axs[-1].set_xlabel('Seconds since first recorded sample (separate flights, not synchronized)');fig.suptitle('100–450 Hz vibration/activity; manual flight, takeoff and landing excluded')
    fig.savefig(OUT/'vibration_timeline.png',dpi=150);plt.close(fig)
    for x in [before,after]:
        m=x['usable']
        results[x['name']+'_rpm_checks']={'min_in_usable_flight':float(x['rpm'][m].min()),'zero_rpm_samples':int(np.sum(x['rpm'][m]==0))}
    (OUT/'comparison.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

if __name__=='__main__':main()
