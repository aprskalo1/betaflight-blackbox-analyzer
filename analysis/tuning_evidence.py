exec(open(__file__.replace('tuning_evidence.py','shake_scan.py'),encoding='utf8').read().split('all_events=[]')[0])
name='LOG00026';d=pd.read_csv(BASE/f'decoded/{name}.I.csv');t=(d.time.to_numpy()-d.time.iloc[0])/1e6;fs=1/np.median(np.diff(t))
gyro=d[[f'gyroADC[{i}]' for i in range(3)]].to_numpy(float);raw=d[[f'gyroUnfilt[{i}]' for i in range(3)]].to_numpy(float);sp=d[[f'setpoint[{i}]' for i in range(3)]].to_numpy(float);D=d[[f'axisD[{i}]' for i in range(2)]].to_numpy(float)
th=(d['rcCommand[3]'].to_numpy()-1000)/10;rpm=d[[f'eRPM[{i}]' for i in range(4)]].to_numpy(float)*200/14;motor=d[[f'motor[{i}]' for i in range(4)]].to_numpy(float)
bands={}
for label,band in [('shake',[8,80]),('high',[100,450])]:
 sos=butter(3,band,btype='bandpass',fs=fs,output='sos')
 bands[label]={k:sosfiltfilt(sos,v,axis=0) for k,v in [('gyro',gyro),('raw',raw),('D',D),('error',gyro-sp)]}
# Pick a relatively smooth, similar-throttle comparison with small rate commands.
poss=[]
for start in np.arange(10,t[-1]-10,1):
 m=(t>=start)&(t<start+.8)
 if 32<th[m].mean()<45 and th[m].std()<4 and abs(sp[m]).max()<100:
  poss.append((float(np.mean(bands['shake']['error'][m,:2]**2)),float(start)))
poss.sort();ref=poss[len(poss)//2][1]
windows=[('steady_comparison',ref,ref+.8),('confirmed_recovery',295,295.8),('turn_recovery',244.7,245.3),('zero_throttle_before_recovery',293.5,294.5)]
out={'file':name,'fs_hz':fs,'windows':[],'limitations':'100–450 Hz is only the sampled band. About 1 kHz logging cannot exclude aliased noise or resolve higher-frequency gyro/motor noise. No temperature or dynamic-D debug was logged.'}
for label,start,end in windows:
 m=(t>=start)&(t<end)
 r={'label':label,'start_s':start,'end_s':end,'throttle_mean_pct':float(th[m].mean()),'error_rms_dps':np.sqrt(np.mean((gyro[m]-sp[m])**2,axis=0)).tolist(),'gyro_range_dps':[gyro[m].min(axis=0).tolist(),gyro[m].max(axis=0).tolist()],'D_abs_p99':np.percentile(abs(D[m]),99,axis=0).tolist(),'rpm_min_per_motor':rpm[m].min(axis=0).tolist(),'rpm_max_per_motor':rpm[m].max(axis=0).tolist(),'motor_at_min_pct':(100*np.mean(motor[m]<=158,axis=0)).tolist(),'motor_at_max_pct':(100*np.mean(motor[m]>=2047,axis=0)).tolist()}
 for band,values in bands.items():
  for field,arr in values.items():r[band+'_'+field+'_rms']=np.sqrt(np.mean(arr[m]**2,axis=0)).tolist()
 out['windows'].append(r)
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for label,start,end in windows[:2]:
 m=(t>=start)&(t<end)
 for a in range(2):
  for row,arr in enumerate([gyro,D]):
   f,p=welch(arr[m,a],fs=fs,nperseg=min(512,m.sum()));axs[row,a].semilogy(f,p,label=f'{label} ({start:.1f}s)')
for a in range(2):
 axs[0,a].set_title(['Roll','Pitch'][a]);axs[0,a].set_ylabel('Gyro PSD ((deg/s)^2/Hz)');axs[1,a].set_ylabel('D contribution PSD (units^2/Hz)')
for ax in axs.flat:ax.set_xlim(5,450);ax.set_xlabel('Frequency (Hz)');ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('Confirmed recovery versus a steadier interval at similar throttle\nShort-window spectra: diagnostic comparison, not proof of thermal margin')
fig.savefig(OUT/'tuning_spectra.png',dpi=150);plt.close(fig)
(OUT/'tuning_evidence.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
