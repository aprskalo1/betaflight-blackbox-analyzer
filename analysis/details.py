exec(open(__file__.replace('details.py','analyse.py'),encoding='utf8').read().split('for file in sorted')[0])
details={}
for name in ['LOG00021','LOG00023','LOG00025','LOG00026']:
 d=pd.read_csv(BASE/f'decoded/{name}.I.csv');g=pd.read_csv(BASE/f'decoded/{name}.G.csv');hh=pd.read_csv(BASE/f'decoded/{name}.H.csv');t=(d.time-d.time.iloc[0])/1e6;gt=(g.time-d.time.iloc[0])/1e6
 dist=distance(g['GPS_coord[0]']/1e7,g['GPS_coord[1]']/1e7,hh['GPS_home[0]'].iloc[0]/1e7,hh['GPS_home[1]'].iloc[0]/1e7)
 voltage=d.vbatLatest/100;v100=voltage.rolling(101,center=True,min_periods=101).mean()
 fast={}
 for i,a in enumerate(['roll','pitch','yaw']):
  gyro=d[f'gyroADC[{i}]'].to_numpy();mask=abs(gyro)>500
  starts=np.flatnonzero(mask&~np.r_[False,mask[:-1]]);ends=np.flatnonzero(mask&~np.r_[mask[1:],False]);episodes=[]
  for start,end in zip(starts,ends):
   if t.iloc[end]-t.iloc[start]>.025:episodes.append({'start_s':round(float(t.iloc[start]),3),'end_s':round(float(t.iloc[end]),3),'peak_dps':int(max(abs(gyro[start:end+1]))),'rotation_during_fast_part_deg':round(float(np.trapezoid(gyro[start:end+1],t.iloc[start:end+1])),1)})
  fast[a]=episodes
 sample_times=[0,3,30,60,70,120,127,150,200,250,263.7,300,340,360,float(t.iloc[-1])]
 if name=='LOG00021':sample_times=[0,200,209.484,215,220,230,240,242.521,250,373.7]
 samples=[]
 for tt in sample_times:
  if tt>t.iloc[-1]:continue
  ii=int(np.argmin(abs(t-tt)));gi=int(np.argmin(abs(gt-tt)))
  samples.append({'t':round(float(t.iloc[ii]),3),'distance_home_m':round(float(dist.iloc[gi]),1),'gps_alt_relative_m':round(float((g.GPS_altitude.iloc[gi]-g.GPS_altitude.iloc[0])/10),1),'baro_m':round(float(d.baroAlt.iloc[ii]/100),1),'speed_kmh':round(float(g.GPS_speed.iloc[gi]*.036),1),'throttle_pct':round(float((d['rcCommand[3]'].iloc[ii]-1000)/10),1),'gyro':[int(d[f'gyroADC[{i}]'].iloc[ii]) for i in range(3)],'setpoint':[int(d[f'setpoint[{i}]'].iloc[ii]) for i in range(3)]})
 details[name]={'min_voltage_100ms':float(v100.min()),'min_voltage_100ms_t':float(t.iloc[v100.idxmin()]),'gps_max_alt_relative_m':float((g.GPS_altitude.max()-g.GPS_altitude.iloc[0])/10),'fast_rotation_episodes':fast,'samples':samples}
 if name=='LOG00026':
  fig,ax=plt.subplots(4,1,figsize=(13,10),sharex=True,layout='constrained');mask=(t>=119.5)&(t<=129)
  for i,a in enumerate(['Roll','Pitch','Yaw']):
   ax[i].plot(t[mask],d.loc[mask,f'setpoint[{i}]'],label='Commanded',lw=1);ax[i].plot(t[mask],d.loc[mask,f'gyroADC[{i}]'],label='Measured gyro',lw=.8);ax[i].set_ylabel(a+' (deg/s)');ax[i].legend();ax[i].grid(alpha=.2)
  ax[3].plot(t[mask],(d.loc[mask,'rcCommand[3]']-1000)/10);ax[3].set_ylabel('Stick throttle (%)');ax[3].set_xlabel('Seconds from first sample');ax[3].grid(alpha=.2);fig.suptitle('LOG00026 | Commands and response during rapid manoeuvres')
  fig.savefig(OUT/'LOG00026.tracking.png',dpi=150);plt.close(fig)
(OUT/'event_details.json').write_text(json.dumps(details,indent=2))
print(json.dumps(details,indent=2))
