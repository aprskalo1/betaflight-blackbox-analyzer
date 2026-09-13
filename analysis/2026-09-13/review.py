from compare import *
from scipy.optimize import linear_sum_assignment

def matching(df,cols,scales,maxdist=2):
    old=df[df.group=='Default'].reset_index(drop=True);new=df[df.group=='D 1.10'].reset_index(drop=True)
    aa=old[cols].to_numpy()/scales;bb=new[cols].to_numpy()/scales
    delta=aa[:,None,:]-bb[None,:,:]
    dist=np.sqrt(np.mean(delta**2,axis=2));dist[np.max(abs(delta),axis=2)>maxdist]=1e6
    a,b=linear_sum_assignment(dist);ok=dist[a,b]<1e5;a=a[ok];b=b[ok]
    return old.iloc[a].reset_index(drop=True),new.iloc[b].reset_index(drop=True),dist[a,b]

def group_summary(df):
    fields=['shake_combined','shake_peak','shake_time_gt8','high_gyro_roll','high_gyro_pitch','high_D_roll','high_D_pitch','th_mean','speed','sp_max','voltage']
    return {name:{'n':len(d),'median':d[fields].median().to_dict(),'p90':d[fields].quantile(.9).to_dict(),'mean':d[fields].mean().to_dict()} for name,d in df.groupby('group')}

def main():
    windows=pd.read_csv(OUT/'windows.csv');rec=pd.read_csv(OUT/'recoveries.csv');rec=rec[rec.eligible].copy()
    wo,wn,wd=matching(windows,['th_mean','speed','sp_max','voltage','th_std'],np.array([5,10,50,.7,5]),1)
    ro,rn,rd=matching(rec,['th_mean','speed','sp_max','voltage','pre_sp_max','pre_speed'],np.array([7,10,80,.8,300,12]),1.5)
    results={'windows_unmatched':group_summary(windows),'recoveries_unmatched':group_summary(rec),'windows_matched':group_summary(pd.concat([wo,wn])),'recoveries_matched':group_summary(pd.concat([ro,rn])),'per_file_windows':windows.groupby('file')[['shake_combined','high_D_roll','high_D_pitch']].median().to_dict(),'per_file_recoveries':rec.groupby('file')[['shake_combined','shake_peak']].median().to_dict()}
    pairs=[]
    for i in range(len(ro)):
        pairs.append({'distance':float(rd[i]),'old':ro.iloc[i].to_dict(),'new':rn.iloc[i].to_dict()})
    (OUT/'matched_recoveries.json').write_text(json.dumps(pairs,indent=2))
    durations=[];ends=[]
    for name in ['LOG00001','LOG00002','LOG00004','LOG00006','LOG00007']:
        x=load(name);t=x['t'];fs=x['fs'];d=x['d'];env=np.max(x['env'][:,:2],axis=1)
        # Duration measure is only descriptive: shake >5 deg/s, decay to <3 for >=0.15 s.
        for _,r in rec[rec.file==name].iterrows():
            p=np.argmin(abs(t-r.shake_peak_t));a=env[p]
            if a<5:continue
            stop=min(len(t)-1,p+round(1.5*fs));low=env[p:stop]<3
            runs=np.convolve(low.astype(int),np.ones(round(.15*fs),int),'valid')
            found=np.flatnonzero(runs>=round(.15*fs))
            duration=float(t[p+found[0]]-t[p]) if len(found) else None
            horizon=p+found[0]+round(.15*fs) if len(found) else stop
            uncontaminated=bool(np.max(abs(x['sp'][p:horizon]))<250 and np.max(x['sp_env'][p:horizon,:2])<8)
            durations.append({'file':name,'group':x['group'],'peak_t':float(t[p]),'peak':float(a),'decay_s':duration,'uncontaminated':uncontaminated})
        last=stats(x,float(t[-1]-2),float(t[-1]+.001))
        last['last_baro_relative_m']=float(d.baroAlt.iloc[-1]/100-np.median(d.baroAlt.iloc[:1000]/100))
        last['last_gps_speed']=float(x['speed'][-1]);last['last_acc_g']=float(x['acc'][-1]);last['last_throttle']=float(x['th'][-1]);last['last_gyro']=x['gyro'][-1].tolist()
        ends.append(last)
        # Endings plotted at full rate so impacts are not lost in downsampling.
        m=t>t[-1]-3
        fig,axs=plt.subplots(5,1,figsize=(11,10),sharex=True,layout='constrained')
        axs[0].plot(t[m],x['th'][m]);axs[0].set_ylabel('Throttle %')
        for a in range(3):axs[1].plot(t[m],x['gyro'][m,a],label=['Roll','Pitch','Yaw'][a],lw=.8)
        axs[1].legend(ncol=3);axs[1].set_ylabel('Gyro deg/s')
        axs[2].plot(t[m],x['acc'][m]);axs[2].set_ylabel('Acceleration g')
        for a in range(4):axs[3].plot(t[m],x['motor'][m,a],label=f'M{a+1}',lw=.8)
        axs[3].legend(ncol=4);axs[3].set_ylabel('Motor command')
        axs[4].plot(t[m],d.baroAlt.to_numpy()[m]/100-np.median(d.baroAlt.iloc[:1000]/100));axs[4].set_ylabel('Relative baro m');axs[4].set_xlabel('Seconds since first recorded sample')
        for ax in axs:ax.grid(alpha=.2)
        fig.suptitle(name+' | last 3 seconds | switch disarm at end');fig.savefig(OUT/f'{name}_ending.png',dpi=130);plt.close(fig)
        # Closest matched examples by covariate distance, not by outcome.
        chosen=sorted(pairs,key=lambda r:r['distance'])[:3]
        for i,pair in enumerate(chosen):
            for group in ['old','new']:
                r=pair[group]
                if r['file']==name:plot_event(x,r['shake_peak_t'],OUT/f'matched_{i+1}_{group}.png',f'Matched example {i+1}: {name} | {x["group"]} | recovery at {r["trigger"]:.2f}s')
    dd=pd.DataFrame(durations);dd.to_csv(OUT/'recovery_decay.csv',index=False)
    results['decay_descriptive']={name:{'n':len(df),'resolved_n':int(df.decay_s.notna().sum()),'median_s':float(df.decay_s.median())} for name,df in dd[dd.uncontaminated].groupby('group')}
    results['endings']=ends
    (OUT/'comparison.json').write_text(json.dumps(results,indent=2))
    # Concise comparison figure; whole-flight and matched results kept distinct.
    fig,axs=plt.subplots(1,3,figsize=(13,4.8),layout='constrained')
    groups=['Default','D 1.10'];colors=['#3577ad','#dc8730']
    for ax,title,df,field in [(axs[0],'Matched flight windows',pd.concat([wo,wn]),'shake_combined'),(axs[1],'Matched throttle recoveries',pd.concat([ro,rn]),'shake_combined'),(axs[2],'Matched windows: pitch D noise',pd.concat([wo,wn]),'high_D_pitch')]:
        rng=np.random.default_rng(13)
        for i,group in enumerate(groups):
            values=df[df.group==group][field].to_numpy()
            ax.scatter(i+rng.uniform(-.12,.12,len(values)),values,s=8,alpha=.3,color=colors[i])
            ax.plot([i-.2,i+.2],[np.median(values)]*2,lw=3,color='black')
        ax.set_xticks([0,1],groups);ax.set_title(title);ax.grid(axis='y',alpha=.2)
    axs[0].set_ylabel('8-80 Hz roll/pitch error RMS (deg/s)');axs[1].set_ylabel('8-80 Hz roll/pitch error RMS (deg/s)');axs[2].set_ylabel('100-450 Hz D contribution RMS (units)')
    fig.suptitle('13 September: distributions overlap; a consistent shake reduction is not established\nDots are windows/events, not independent batteries. Black bars are medians.',fontsize=11)
    fig.savefig(OUT/'comparison.png',dpi=170);plt.close(fig)
    print(json.dumps({k:v for k,v in results.items() if k not in ['endings']},indent=2))
    print('ENDINGS',json.dumps([{k:r[k] for k in ['file','last_baro_relative_m','last_gps_speed','last_acc_g','last_throttle','last_gyro','acc_max']} for r in ends]))
if __name__=='__main__':main()
