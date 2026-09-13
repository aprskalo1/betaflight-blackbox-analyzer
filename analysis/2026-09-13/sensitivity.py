from compare import *
from review import matching

def main():
    rec=pd.read_csv(OUT/'recoveries.csv');rec=rec[rec.eligible].copy()
    data={}
    for name in rec.file.unique():
        d=pd.read_csv(BASE/'decoded'/f'{name}.I.csv');t=(d.time.to_numpy()-d.time.iloc[0])/1e6
        err=d[[f'gyroADC[{a}]' for a in range(2)]].to_numpy(float)-d[[f'setpoint[{a}]' for a in range(2)]].to_numpy(float)
        fs=1/np.median(np.diff(t));bands={}
        for band in [(5,40),(8,80),(15,80)]:bands[str(band)]=sosfiltfilt(butter(3,band,btype='bandpass',fs=fs,output='sos'),err,axis=0)
        for idx,r in rec[rec.file==name].iterrows():
            m=(t>=r.start)&(t<r.end)
            for key,value in bands.items():rec.loc[idx,key]=np.sqrt(np.mean(value[m]**2))
    out=[]
    for label,sub in [('main',rec),('lower_commands',rec[rec.sp_max<150]),('zero_throttle',rec[rec.pre_th_min<1])]:
        a,b,dist=matching(sub,['th_mean','speed','sp_max','voltage','pre_sp_max','pre_speed'],np.array([7,10,80,.8,300,12]),1.5)
        out.append({'selection':label,'pairs':len(a),'bands':{key:{'old_median':float(a[key].median()),'new_median':float(b[key].median()),'new_lower_pairs':int((b[key].to_numpy()<a[key].to_numpy()).sum())} for key in ['(5, 40)','(8, 80)','(15, 80)']}})
    (OUT/'sensitivity.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
