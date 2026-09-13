from pathlib import Path
import sys, os, json
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'tools/pythonpkgs'))
os.environ['MPLCONFIGDIR']=str(BASE/'tools/mplconfig')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=BASE/'results'; OUT.mkdir(exist_ok=True)
summaries=[]; full=[]; all_fields=[]
def bounds(x): return [float(np.min(x)),float(np.max(x))]
def distance(lat,lon,lat0,lon0):
    a=np.sin(np.radians(lat-lat0)/2)**2+np.cos(np.radians(lat))*np.cos(np.radians(lat0))*np.sin(np.radians(lon-lon0)/2)**2
    return 6371000*2*np.arctan2(np.sqrt(a),np.sqrt(1-a))
for file in sorted((BASE/'decoded').glob('*.I.csv')):
    name=file.name.split('.')[0]; meta=json.loads((file.parent/f'{name}.metadata.json').read_text())
    d=pd.read_csv(file); g=pd.read_csv(file.parent/f'{name}.G.csv'); s=pd.read_csv(file.parent/f'{name}.S.csv'); home=pd.read_csv(file.parent/f'{name}.H.csv')
    h=dict(line[2:].split(':',1) for line in (file.parent/f'{name}.headers.txt').read_text().splitlines() if ':' in line)
    t=(d.time.to_numpy()-d.time.iloc[0])/1e6; gt=(g.time.to_numpy()-d.time.iloc[0])/1e6
    throttle=(d['rcCommand[3]'].to_numpy()-1000)/10
    lat=g['GPS_coord[0]'].to_numpy()/1e7; lon=g['GPS_coord[1]'].to_numpy()/1e7
    lat0=home['GPS_home[0]'].iloc[0]/1e7; lon0=home['GPS_home[1]'].iloc[0]/1e7
    dist=distance(lat,lon,lat0,lon0); speed=g.GPS_speed.to_numpy()*.036
    baro=d.baroAlt.to_numpy()/100; alt=g.GPS_altitude.to_numpy()/10
    v=d.vbatLatest.to_numpy()/100; current=d.amperageLatest.to_numpy()/100
    accel=np.linalg.norm(d[[f'accSmooth[{i}]' for i in range(3)]].to_numpy()/2048,axis=1)
    motors=d[[f'motor[{i}]' for i in range(4)]].to_numpy()
    rpm=d[[f'eRPM[{i}]' for i in range(4)]].to_numpy()*200/float(h['motor_poles'])
    dt=np.diff(d.time.to_numpy()); it=np.diff(d.loopIteration.to_numpy())
    armed_indices=np.flatnonzero(throttle>5)
    active=(t>3)&(t<t[-1]-3)&(np.interp(t,gt,speed)>5)
    events=[]
    enames={v:k for k,v in meta['eventNames'].items()}
    for e in meta['events']: events.append({'t':round((e['last_main_time']-d.time.iloc[0])/1e6,3),'event':enames.get(e['event'],e['event']),'data':e['data']})
    modes=[]
    prev=None
    for row in s.itertuples(index=False):
        vals=list(row); flags=int(vals[1]); key=tuple(vals[1:])
        if key!=prev: modes.append({'t':round((vals[0]-d.time.iloc[0])/1e6,3),'modes':[n for i,n in enumerate(meta['flightModeNames']) if flags&(1<<i)],'state':vals[2],'failsafe':vals[3],'rx':vals[4],'channels_valid':vals[5]}); prev=key
    axes={}
    for i,a in enumerate(['roll','pitch','yaw']):
        gyro=d[f'gyroADC[{i}]'].to_numpy(); sp=d[f'setpoint[{i}]'].to_numpy(); error=gyro-sp
        axes[a]={'gyro_range_dps':bounds(gyro),'setpoint_range_dps':bounds(sp),'active_error_rms_dps':float(np.sqrt(np.mean(error[active]**2))) if active.any() else None,'active_error_abs_p95_dps':float(np.percentile(abs(error[active]),95)) if active.any() else None,'max_error':float(np.max(abs(error))),'max_error_t':float(t[np.argmax(abs(error))])}
    summary={'file':name,'date_recorded':h['Log start datetime'],'rows':len(d),'duration_s':float(t[-1]),'sample_interval_us_median':float(np.median(dt)),'sample_interval_us_range':bounds(dt),'iteration_step_range':bounds(it),'gaps_gt_1_5ms':int((dt>1500).sum()),'invalid_frames':meta['invalidCallbacks'],'gps_rows':len(g),'gps_interval_s_median':float(np.median(np.diff(gt))),'gps_sats':bounds(g.GPS_numSat),'gps_speed_kmh':bounds(speed),'max_speed_t':float(gt[np.argmax(speed)]),'max_distance_home_m':float(dist.max()),'distance_end_m':float(dist[-1]),'gps_track_length_m':float(np.sum(distance(lat[1:],lon[1:],lat[:-1],lon[:-1]))),'baro_m_range':bounds(baro),'baro_start_end_m':[float(np.median(baro[t<1])),float(np.median(baro[t>t[-1]-1]))],'gps_altitude_asl_m':bounds(alt),'throttle_pct':bounds(throttle),'throttle_mean_pct':float(throttle.mean()),'throttle_gt5_first_last_s':[float(t[armed_indices[0]]),float(t[armed_indices[-1]])] if len(armed_indices) else None,'voltage_start_min_end':[float(np.median(v[t<1])),float(v.min()),float(np.median(v[t>t[-1]-1]))],'max_current_a':float(current.max()),'mah_integrated':float(np.trapezoid(current,t)/3.6),'rssi_raw':bounds(d.rssi),'motor_raw':bounds(motors),'motor_max_per_motor':motors.max(axis=0).tolist(),'motor_pct_samples_at_2047':float(100*np.mean(np.any(motors>=2047,axis=1))),'rpm_max_per_motor':rpm.max(axis=0).tolist(),'acc_magnitude_g_max':float(accel.max()),'max_acc_t':float(t[np.argmax(accel)]),'axes':axes,'modes':modes,'events':events,'PIDs':{k:h[k] for k in ['rollPID','pitchPID','yawPID','d_min','ff_weight']}}
    summaries.append(summary)
    for kind,df in [('I',d),('G',g),('H',home),('S',s)]:
        for col in df:
            all_fields.append({'file':name,'frame':kind,'field':col,'min_raw':float(df[col].min()),'max_raw':float(df[col].max()),'mean_raw':float(df[col].mean())})
    if t[-1]>10:
        full.append((name,d,g,t,gt,throttle,baro,dist,speed,lat,lon,lat0,lon0))
        blocks=[]
        for start in np.arange(0,t[-1],30):
            m=(t>=start)&(t<start+30); gm=(gt>=start)&(gt<start+30)
            blocks.append({'start_s':start,'throttle_mean':float(throttle[m].mean()),'throttle_max':float(throttle[m].max()),'speed_mean_kmh':float(speed[gm].mean()),'speed_max_kmh':float(speed[gm].max()),'baro_range':bounds(baro[m]),'distance_range':bounds(dist[gm]),'gyro_absmax':d.loc[m,[f'gyroADC[{i}]' for i in range(3)]].abs().max().tolist()})
        (OUT/f'{name}.timeline.json').write_text(json.dumps(blocks,indent=2))
        # Full flight overview: min/max envelopes preserve brief peaks.
        fig,ax=plt.subplots(6,1,figsize=(13,13),sharex=True,layout='constrained')
        ax[0].plot(t[::50],throttle[::50],lw=.8);ax[0].set_ylabel('Stick throttle (%)')
        ax[1].plot(gt,speed,lw=.8); ax[1].set_ylabel('GPS speed (km/h)')
        ax[2].plot(t[::100],baro[::100],label='Barometer',lw=.8); ax[2].plot(gt,alt-alt[0],label='GPS change from start',lw=.8);ax[2].set_ylabel('Relative altitude (m)');ax[2].legend()
        ax[3].plot(gt,dist,lw=.8);ax[3].set_ylabel('Distance to home (m)')
        ax[4].plot(t[::50],v[::50],lw=.8);ax[4].set_ylabel('Battery (V)')
        for i,a in enumerate(['Roll','Pitch','Yaw']):
            gg=d[f'gyroADC[{i}]'].to_numpy(); block=100; n=len(t)//block
            ax[5].fill_between(t[:n*block].reshape(-1,block).mean(axis=1),gg[:n*block].reshape(-1,block).min(axis=1),gg[:n*block].reshape(-1,block).max(axis=1),alpha=.4,label=a)
        ax[5].set_ylabel('Gyro envelope (deg/s)');ax[5].legend();ax[5].set_xlabel('Seconds from first recorded sample')
        for aa in ax:aa.grid(alpha=.2)
        if name=='LOG00021':
            for aa in ax:aa.axvspan(209.483589,242.521152,color='orange',alpha=.2)
        fig.suptitle(f'{name} | 6 September 2026 | {t[-1]:.1f} seconds'+(' | Orange: GPS Rescue active' if name=='LOG00021' else ''))
        fig.savefig(OUT/f'{name}.overview.png',dpi=150);plt.close(fig)

pd.DataFrame(all_fields).to_csv(OUT/'all_recorded_field_ranges.csv',index=False)
(OUT/'summary.json').write_text(json.dumps(summaries,indent=2))
fig,axs=plt.subplots(2,2,figsize=(12,10),layout='constrained')
for ax,values in zip(axs.flat,full):
    name,d,g,t,gt,th,baro,dist,speed,lat,lon,lat0,lon0=values
    x=(lon-lon0)*111195*np.cos(np.radians(lat0)); y=(lat-lat0)*111195
    ax.plot(x,y,lw=.6,color='lightgray'); sc=ax.scatter(x,y,c=gt,s=2,cmap='viridis');ax.scatter([0],[0],marker='*',s=100,c='red',label='Recorded home')
    ax.set_title(name);ax.set_xlabel('East of home (m)');ax.set_ylabel('North of home (m)');ax.set_aspect('equal');ax.grid(alpha=.2);fig.colorbar(sc,ax=ax,label='Seconds');ax.legend(fontsize=8)
fig.suptitle('Sunday flight paths | GPS, approximate local coordinates')
fig.savefig(OUT/'flight_paths.png',dpi=160);plt.close(fig)
for s in summaries:
    print(json.dumps({k:s[k] for k in ['file','duration_s','rows','sample_interval_us_median','gaps_gt_1_5ms','gps_sats','gps_speed_kmh','max_distance_home_m','distance_end_m','baro_m_range','throttle_pct','voltage_start_min_end','max_current_a','mah_integrated','motor_pct_samples_at_2047','acc_magnitude_g_max','modes','axes']}))
