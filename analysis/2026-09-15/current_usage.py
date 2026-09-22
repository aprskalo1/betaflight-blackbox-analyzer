"""Integrate recorded calibrated current; this is not independent sensor calibration."""
from pathlib import Path
import csv,json
BASE=Path(__file__).resolve().parent

def main():
    rows=[]
    for path in sorted((BASE/'decoded').glob('*.I.csv')):
        name=path.name.split('.')[0]
        headers=dict(line[2:].split(':',1) for line in (BASE/'decoded'/f'{name}.headers.txt').read_text().splitlines() if ':' in line)
        meta=json.loads((BASE/'decoded'/f'{name}.metadata.json').read_text())
        mah=0.;gap_s=0.;first=None;last=None;previous=None
        with path.open(newline='') as fh:
            for row in csv.DictReader(fh):
                now=int(row['time']);current=float(row['amperageLatest'])
                if first is None:first=now
                if previous:
                    dt=now-previous[0]
                    if 0<dt<=5000:mah+=(current+previous[1])/2*dt/360000000
                    elif dt>5000:gap_s+=dt/1e6
                previous=(now,current);last=now
        offset,scale=map(int,headers['currentSensor'].split(','))
        rows.append({'file':name,'current_meter_source_inferred_from_conditional_header':'ADC','ibata_scale':scale,'ibata_offset':offset,'recorded_duration_s':(last-first)/1e6,'integrated_recorded_mah':mah,'excluded_gap_s':gap_s,'invalid_decoder_callbacks':meta['invalidCallbacks'],'clean_log_end':any(e['event']==255 for e in meta['events'])})
    result={'method':'Trapezoidal integration of amperageLatest (centiamps) over recorded timestamps. Intervals >5ms excluded. No estimate for missing flight time or unlogged ground consumption. Values depend on existing sensor calibration; not independent actual consumption.','logs':rows}
    (BASE/'current_usage.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
