"""September 20 integrity, recorded charge, vibration and RPM screening.

Uses the existing September 13/15 definitions for comparable descriptive metrics.
No audio is recorded; candidates are not diagnoses of acoustic noise or prop slip.
"""
from pathlib import Path
import sys, json
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent/'2026-09-15'))
import dynamic_idle as di
import post_crash as pc
import motor_response as mr
import motor_bursts as mb
import current_usage as cu
from dynamic_idle import np, pd, plt, find_peaks, maximum_filter1d
OUT = BASE/'results'
OUT.mkdir(exist_ok=True)

def run():
    cu.BASE = BASE
    cu.main()
    mr.BASE = mb.BASE = BASE
    mr.OUT = mb.OUT = pc.OUT = OUT
    baseline = di.load('LOG00008', BASE.parent/'2026-09-15')
    baseline_windows = pc.extract(baseline)
    summaries=[]
    for name in ['LOG00002','LOG00004','LOG00006','LOG00008']:
        x=di.load(name,BASE);t=x['t'];fs=x['fs']
        # Filter definitions assume regularly sampled data. Reject a gapped log
        # rather than silently filtering across missing samples.
        if np.max(np.diff(t))>.005:
            raise ValueError(f'{name}: split into continuous segments before filtering')
        motor=mr.investigate(name)
        bursts=mb.inspect(name)
        windows=pc.extract(x)
        a,b=pc.match(baseline_windows,windows)
        comparison={'pairs':len(a)}
        if len(a):
            comparison.update(before=pc.summary(a),today=pc.summary(b))
            pd.concat([a.add_prefix('before_'),b.add_prefix('today_')],axis=1).to_csv(OUT/f'{name}_matched_windows.csv',index=False)
        quiet=x['usable']&(maximum_filter1d(abs(x['sp']).max(axis=1),size=round(.4*fs))<180)&(x['sp_env'][:,:2].max(axis=1)<8)&(x['speed']>10)&(x['th']>10)
        score=np.where(quiet,x['env'][:,:2].max(axis=1),0)
        peaks,_=find_peaks(score,height=5,prominence=2,distance=round(1.5*fs))
        candidates=[]
        for p in sorted(peaks,key=lambda p:score[p],reverse=True)[:6]:
            row=di.stats(x,float(t[p]-.2),float(t[p]+.2))
            row.update(t=float(t[p]),score=float(score[p]))
            candidates.append(row)
        selected=[('shake',r['t']) for r in candidates[:2]]+[('correction',r['t']) for r in bursts['low_command_bursts'][:2]]
        for kind,center in selected:
            di.core.plot_event(x,center,OUT/f'{name}_{kind}_{center:.2f}.png',f'{name} | {kind} candidate at {center:.3f}s | elapsed from first sample')
        low=x['usable']&(x['th']<1)&(x['speed']>10)
        idle={'seconds':float(low.sum()/fs)}
        if low.any():
            idle.update(min_motor_rpm_percentiles=np.percentile(x['minrpm'][low],[0,5,50,95]).tolist(),below3000_pct=float(100*np.mean(x['minrpm'][low]<3000)))
        result={'file':name,'usable_s':float(x['usable'].sum()/fs),'idle':idle,'shake_candidates':candidates,'bursts':bursts,'motor_response':motor,'comparison_to_sept15_first_battery':comparison}
        summaries.append(result)
        # Continuous timeline; decimate only the plotted lines, not the analysis.
        fig,axs=plt.subplots(5,1,figsize=(13,10),sharex=True,layout='constrained')
        axs[0].plot(t[::20],x['th'][::20]);axs[0].set_ylabel('Throttle %')
        axs[1].plot(t[::20],x['volt'][::20]);axs[1].set_ylabel('Battery V')
        axs[2].plot(t[::10],x['env'][::10,:2]);axs[2].set_ylabel('8-80 Hz error\nRMS deg/s')
        axs[3].plot(t[::10],x['rpm'][::10]);axs[3].set_ylabel('Motor RPM')
        axs[4].plot(t[::5],x['acc'][::5]);axs[4].set_ylabel('Acceleration g')
        for ax in axs:ax.grid(alpha=.2)
        axs[-1].set_xlabel('Seconds from first recorded sample');fig.suptitle(name)
        fig.savefig(OUT/f'{name}_overview.png',dpi=140);plt.close(fig)
        print(json.dumps({'file':name,'shake':[(r['t'],r['score']) for r in candidates[:3]],'bursts':[(r['t'],r['motor_correction_rms_units']) for r in bursts['low_command_bursts'][:3]],'stable_drops':motor['stable_command_drop_candidates'],'stable_rises':motor['rapid_rise_candidates'],'pairs':len(a)}),flush=True)
    (OUT/'summary.json').write_text(json.dumps(summaries,indent=2))

if __name__=='__main__':run()
