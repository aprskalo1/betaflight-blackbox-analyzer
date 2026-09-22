"""Compare throttle recoveries using the September 15 matching definitions."""
from pathlib import Path
import sys,json
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'2026-09-15'))
import dynamic_idle as di
from dynamic_idle import np,pd
OUT=BASE/'recovery_comparison';OUT.mkdir(exist_ok=True)

def main():
    rows=[]
    for name in ['LOG00002','LOG00004','LOG00006','LOG00008']:
        x=di.load(name,BASE)
        if np.max(np.diff(x['t']))>.005:raise ValueError('Discontinuous flight')
        w,r=di.extract(x);rows.extend(r)
        print(name,len(r),flush=True)
    today=pd.DataFrame(rows);today.to_csv(OUT/'today_recoveries.csv',index=False)
    previous=pd.read_csv(BASE.parent/'2026-09-15/results/recoveries.csv')
    previous=previous[previous.eligible].copy();today=today[today.eligible].copy()
    results=[]
    for source in ['Idle off','Idle 35']:
        earlier=previous[previous.group==source].copy();earlier['group']='Idle off'
        for selection in ['first_battery','all_today']:
            later=today[today.file=='LOG00002'].copy() if selection=='first_battery' else today.copy()
            later['group']='Idle 35'
            for tolerance in [1.,1.5,2.]:
                a,b,cost=di.matching(pd.concat([earlier,later],ignore_index=True),['th_mean','speed','sp_max','voltage','pre_sp_max','pre_speed'],np.array([7,10,80,.8,300,12]),tolerance)
                r={'reference':'Sept13_idle_off' if source=='Idle off' else 'Sept15_first_idle35','today_selection':selection,'tolerance':tolerance,'pairs':len(a),'reference_eligible':len(earlier),'today_eligible':len(later)}
                if len(a):
                    keys=['shake_combined','shake_peak','pre_low_rpm_p05']
                    r.update(before_median=a[keys].median().to_dict(),today_median=b[keys].median().to_dict(),pairs_lower_today=int((b.shake_combined.to_numpy()<a.shake_combined.to_numpy()).sum()))
                    pd.concat([a.add_prefix('before_'),b.add_prefix('today_')],axis=1).to_csv(OUT/f'{r["reference"]}_{selection}_{tolerance}_pairs.csv',index=False)
                results.append(r)
    (OUT/'comparison.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
