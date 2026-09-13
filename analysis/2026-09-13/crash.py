from compare import *
OUT=BASE/'crash';OUT.mkdir(exist_ok=True)

def main():
    summaries=[]
    for name in ['LOG00001','LOG00002','LOG00004','LOG00006','LOG00007']:
        x=load(name);t=x['t'];d=x['d'];fs=x['fs']
        err=x['gyro']-x['sp'];score=np.max(abs(err),axis=1)
        # Candidate scan for major loss of tracking; pilots can command rapid turns normally.
        peaks,_=find_peaks(score,height=300,distance=round(.7*fs),prominence=150)
        ev=[]
        for p in peaks:
            m=(t>=t[p]-.1)&(t<=t[p]+.1)
            ev.append({'t':float(t[p]),'error_peak':float(score[p]),'gyro':x['gyro'][p].tolist(),'setpoint':x['sp'][p].tolist(),'acc_peak_g':float(x['acc'][m].max()),'throttle':float(x['th'][p]),'min_rpm':float(x['rpm'][m].min()),'max_motor':float(x['motor'][m].max())})
        summaries.append({'file':name,'major_tracking_events':ev})
        if name!='LOG00001':continue
        cols=['time','rcCommand[3]']+[f'{field}[{a}]' for field in ['setpoint','gyroADC','gyroUnfilt','accSmooth','motor','eRPM'] for a in range(4 if field in ['motor','eRPM'] else 3)]+['vbatLatest','amperageLatest']
        table=d.loc[(t>=241.8),cols].copy();table.insert(0,'elapsed_s',t[t>=241.8]);table.to_csv(OUT/'LOG00001_crash_samples.csv',index=False)
        onset=[]
        search=(t>=242)&(t<242.6)
        checks={'raw_gyro_any_over_200':np.max(abs(x['raw']),axis=1)>200,'gyro_error_any_over_100':score>100,'gyro_error_any_over_300':score>300,'acc_over_3g':x['acc']>3,'acc_over_5g':x['acc']>5,'any_motor_max':np.any(x['motor']>=2047,axis=1),'throttle_under_1pct':x['th']<1}
        for key,mask in checks.items():
            pp=np.flatnonzero(mask&search)
            if len(pp):
                p=pp[0];onset.append({'condition':key,'t':float(t[p]),'gyro':x['gyro'][p].tolist(),'raw_gyro':x['raw'][p].tolist(),'setpoint':x['sp'][p].tolist(),'acc_g':float(x['acc'][p]),'throttle':float(x['th'][p]),'rpm':x['rpm'][p].tolist(),'motor':x['motor'][p].tolist()})
        (OUT/'onset_thresholds.json').write_text(json.dumps(onset,indent=2))
        print('ONSET',json.dumps(onset,indent=2))
        snapshots=[]
        for stamp in [241.8,242,242.1,242.2,242.24,242.26,242.27,242.28,242.29,242.30,242.31,242.32,242.34,242.36,242.4,242.5,242.7,243,243.23,243.315]:
            p=np.argmin(abs(t-stamp));snapshots.append({'t':round(float(t[p]),6),'th':float(x['th'][p]),'sp':x['sp'][p].tolist(),'gyro':x['gyro'][p].tolist(),'acc_g':round(float(x['acc'][p]),3),'motor':x['motor'][p].tolist(),'rpm':np.round(x['rpm'][p]).tolist(),'V':float(x['volt'][p]),'A':float(x['current'][p])})
        (OUT/'snapshots.json').write_text(json.dumps(snapshots,indent=2));print('SNAPSHOTS',json.dumps(snapshots))
        for label,start,end in [('overview',239.5,243.32),('onset',242.15,242.45),('impact',243.15,243.32)]:
            m=(t>=start)&(t<=end);fig,axs=plt.subplots(8,1,figsize=(13,15),sharex=True,layout='constrained')
            axs[0].plot(t[m],x['th'][m],label='Stick throttle');axs[0].plot(t[m],d['setpoint[3]'].to_numpy()[m]/10,label='Mixer throttle');axs[0].legend(loc='upper left');axs[0].set_ylabel('Throttle (%)')
            for a in range(3):
                axs[a+1].plot(t[m],x['sp'][m,a],label='Setpoint',color='black',lw=1)
                axs[a+1].plot(t[m],x['gyro'][m,a],label='Filtered gyro',lw=.8)
                axs[a+1].plot(t[m],x['raw'][m,a],label='Unfiltered gyro',lw=.6,alpha=.5)
                axs[a+1].set_ylabel(['Roll','Pitch','Yaw'][a]+' (deg/s)');axs[a+1].legend(loc='upper left',ncol=3,fontsize=8)
            axs[4].plot(t[m],x['acc'][m]);axs[4].set_ylabel('Accel magnitude g')
            for a in range(4):
                axs[5].plot(t[m],x['motor'][m,a],label=f'M{a+1}',lw=.8)
                axs[6].plot(t[m],x['rpm'][m,a],label=f'M{a+1}',lw=.8)
            axs[5].legend(ncol=4,loc='upper left');axs[5].set_ylabel('Motor command');axs[6].legend(ncol=4,loc='upper left');axs[6].set_ylabel('Mechanical RPM')
            axs[7].plot(t[m],x['volt'][m],label='Voltage',color='tab:blue');axs[7].set_ylabel('Battery V');ax2=axs[7].twinx();ax2.plot(t[m],x['current'][m],label='Current',color='tab:orange');ax2.set_ylabel('Battery A')
            for ax in axs:
                ax.grid(alpha=.2)
                for stamp in [242.293779,243.230036,243.314882]:
                    if start<=stamp<=end:ax.axvline(stamp,color='gray',ls='--',alpha=.5)
            axs[-1].set_xlabel('Seconds since first recorded sample')
            fig.suptitle(f'LOG00001 crash | {label} | default Damping 1.00\nRPM channel numbers are logical mixer motors; physical corners not established')
            fig.savefig(OUT/f'LOG00001_{label}.png',dpi=150);plt.close(fig)
        # Compact view of the key motor-speed disturbance, before the final impact.
        m=(t>=242.282)&(t<=242.312)
        fig,axs=plt.subplots(4,1,figsize=(11,8),sharex=True,layout='constrained')
        for a in range(4):axs[0].plot(t[m],x['rpm'][m,a],label=f'M{a+1}',lw=2 if a==3 else .8,alpha=1 if a==3 else .65)
        axs[0].legend(ncol=4);axs[0].set_ylabel('Reported RPM')
        axs[1].plot(t[m],x['motor'][m,3],label='M4 command',color='tab:red');axs[1].legend();axs[1].set_ylabel('Command\n158-2047')
        axs[2].plot(t[m],x['raw'][m,2],label='Unfiltered yaw');axs[2].plot(t[m],x['sp'][m,2],label='Commanded yaw',color='black');axs[2].legend();axs[2].set_ylabel('Yaw deg/s')
        axs[3].plot(t[m],x['th'][m]);axs[3].set_ylabel('Stick throttle %');axs[3].set_xlabel('Seconds since first recorded sample')
        for ax in axs:ax.grid(alpha=.2);ax.axvline(242.293779,color='gray',ls='--',alpha=.6)
        fig.suptitle('LOG00001: motor 4 RPM collapses during a high-power manoeuvre\nThe initial speed drop is visible while its command remains high; yaw then departs sharply')
        fig.savefig(OUT/'motor4_onset.png',dpi=160);plt.close(fig)
    (OUT/'major_events.json').write_text(json.dumps(summaries,indent=2));print('ALL MAJOR EVENTS',json.dumps(summaries,indent=2))

if __name__=='__main__':main()
