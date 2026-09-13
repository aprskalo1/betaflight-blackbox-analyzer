exec(open(__file__.replace('shake_shortlist.py','shake_scan.py'),encoding='utf8').read().split('all_events=[]')[0])
selected=[('LOG00026',244.7,245.3,'After throttle reduction and turn'),('LOG00026',295.0,295.8,'Power restored after zero-throttle coast'),('LOG00025',81.75,82.3,'Power restored after throttle cut'),('LOG00023',136.35,136.85,'After rapid pitch/roll manoeuvres'),('LOG00023',171.55,172.2,'Immediate throttle-cut bobble')]
fig,axs=plt.subplots(5,3,figsize=(16,14),layout='constrained')
rows=[]
for axes,(name,start,end,label) in zip(axs,selected):
 d=pd.read_csv(BASE/f'decoded/{name}.I.csv');t=(d.time.to_numpy()-d.time.iloc[0])/1e6
 m=(t>=start)&(t<=end);context=(t>=start-1.7)&(t<=end+.3)
 th=(d['rcCommand[3]'].to_numpy()-1000)/10
 axes[0].plot(t[context],th[context]);axes[0].axvspan(start,end,alpha=.15,color='red');axes[0].set_ylabel('Throttle (%)');axes[0].set_title(name+' | '+label,fontsize=9)
 row={'file':name,'interval_s':[start,end],'flight_controller_time_s':[(d.time.iloc[0]/1e6)+start,(d.time.iloc[0]/1e6)+end],'interpretation':label}
 for i,axis in enumerate(['roll','pitch']):
  gyro=d[f'gyroADC[{i}]'].to_numpy();sp=d[f'setpoint[{i}]'].to_numpy();err=gyro-sp
  axes[i+1].plot(t[m],sp[m],label='Command',lw=1.4);axes[i+1].plot(t[m],gyro[m],label='Gyro',lw=.9);axes[i+1].set_ylabel(axis+' (deg/s)');axes[i+1].legend(fontsize=8)
  row[axis+'_error_range_dps']=[float(err[m].min()),float(err[m].max())]
 rpm=d.loc[m,[f'eRPM[{i}]' for i in range(4)]].to_numpy()*200/14
 row['rpm_range']=[float(rpm.min()),float(rpm.max())]
 row['motor_command_range']=[int(d.loc[m,[f'motor[{i}]' for i in range(4)]].min().min()),int(d.loc[m,[f'motor[{i}]' for i in range(4)]].max().max())]
 for ax in axes:ax.grid(alpha=.2);ax.set_xlabel('Elapsed seconds')
 rows.append(row)
fig.suptitle('Five shake/bobble intervals to review | shaded throttle interval matches gyro close-ups\nBlue = command; orange = actual rotation. Axis values are rates, not tilt angles.',fontsize=13)
fig.savefig(OUT/'shortlist.png',dpi=150);plt.close(fig)
(OUT/'shortlist.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
