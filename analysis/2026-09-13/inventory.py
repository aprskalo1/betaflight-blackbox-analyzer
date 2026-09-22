from pathlib import Path
import sys, json, os
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'tools/pythonpkgs'))
import numpy as np
import pandas as pd

def header(name,base=None):
    folder=Path(base) if base is not None else BASE
    return dict(line[2:].split(':',1) for line in (folder/'decoded'/f'{name}.headers.txt').read_text().splitlines() if ':' in line)

def main():
    out=[]; headers={}
    for f in sorted((BASE/'decoded').glob('*.I.csv')):
        name=f.name.split('.')[0]; h=header(name); headers[name]=h
        d=pd.read_csv(f); meta=json.loads(f.with_name(name+'.metadata.json').read_text())
        s=pd.read_csv(f.with_name(name+'.S.csv')); g=pd.read_csv(f.with_name(name+'.G.csv'))
        if not len(d): continue
        t=(d.time.to_numpy()-d.time.iloc[0])/1e6
        gyro=d[[f'gyroADC[{a}]' for a in range(3)]].to_numpy(float)
        acc=np.linalg.norm(d[[f'accSmooth[{a}]' for a in range(3)]].to_numpy(float),axis=1)/int(h['acc_1G'])
        rpm=d[[f'eRPM[{a}]' for a in range(4)]].to_numpy(float)*200/int(h['motor_poles'])
        modes=[]; prev=None
        for row in s.itertuples(index=False,name=None):
            if row[1:]!=prev:
                modes.append({'t':round((row[0]-d.time.iloc[0])/1e6,3),'flags':row[1], 'names':[n for i,n in enumerate(meta['flightModeNames']) if int(row[1])&(1<<i)], 'failsafe':row[3], 'rx':row[4], 'valid':row[5]});prev=row[1:]
        events=[{'t':round((e['last_main_time']-d.time.iloc[0])/1e6,3),'event':e['event'],'data':e['data']} for e in meta['events']]
        item={'file':name,'date':h['Log start datetime'],'first_uptime_s':float(d.time.iloc[0]/1e6),'last_uptime_s':float(d.time.iloc[-1]/1e6),'duration_s':float(t[-1]),'rows':len(d),'invalid':meta['invalidCallbacks'],'frame_stats':meta['stats']['frame'],'dt_median_us':float(np.median(np.diff(d.time))),'dt_max_us':float(np.max(np.diff(d.time))) if len(d)>1 else None,'PIDs':{k:h[k] for k in ['rollPID','pitchPID','yawPID','d_min','simplified_d_gain','ff_weight','dyn_idle_min_rpm'] if k in h},'volts_start_end':[float(d.vbatLatest.iloc[:200].median()/100),float(d.vbatLatest.iloc[-200:].median()/100)],'max_acc_g':float(acc.max()),'max_acc_t':float(t[acc.argmax()]),'high_acc_times_s':np.unique(np.round(t[acc>8],1)).tolist(),'max_gyro_dps':float(abs(gyro).max()),'rpm_min':float(rpm.min()),'gps_speed_max_kmh':float(g.GPS_speed.max()*.036) if len(g) else None,'modes':modes,'events':events}
        out.append(item)
        print(json.dumps({k:v for k,v in item.items() if k not in ['frame_stats','high_acc_times_s']}))
    baseline=next(iter(headers.values())); changes={}
    for name,h in headers.items():
        changes[name]={k:[baseline.get(k),h.get(k)] for k in baseline.keys()|h.keys() if baseline.get(k)!=h.get(k)}
    (BASE/'inventory.json').write_text(json.dumps(out,indent=2))
    (BASE/'header_changes.json').write_text(json.dumps(changes,indent=2))
    print('HEADER_CHANGES',json.dumps(changes))
if __name__=='__main__':
    if len(sys.argv)>1:BASE=Path(sys.argv[1]).resolve()
    main()
