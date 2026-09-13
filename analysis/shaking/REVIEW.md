The four full flights were scanned for brief roll/pitch oscillations that were substantially larger than the corresponding commanded oscillations. Five intervals were then inspected on unfiltered-in-time plots of the recorded filtered gyro, setpoint, throttle, PID terms, and RPM. These are measured disturbances; whether each was the particular shaking felt by the pilot still needs matching to recollection or synchronised video.

**Start with these intervals**

Times are elapsed from the first main sample of the individual file, not from the beginning of the day's flying or a video.

| File | Review interval | Context | Observation |
| --- | --- | --- | --- |
| LOG00026 | 4:04.70–4:05.30 | Throttle fell from about 70% to the mid-20s after a turn, then returned to the mid-30s | Clear roll/pitch flutter; error ranges −36 to +24 deg/s roll and −47 to +37 deg/s pitch |
| LOG00026 | 4:55.00–4:55.80 | Zero-throttle coast, followed by power restoration to about 38–48% | Roll oscillates around a nearly steady command; pitch also shakes. Strong match for a catch/recovery symptom |
| LOG00025 | 1:21.75–1:22.30 | About 72% throttle cut to roughly 5%, then restored to the mid-30s during a turn | Repeated roll/pitch oscillations after the cut, mainly during recovery |
| LOG00023 | 2:16.35–2:16.85 | Rapid pitch move, subsequent roll movements, then power restoration toward 50% | One of the strongest inspected roll shakes; roll error ranges −69 to +45 deg/s |
| LOG00023 | 2:51.55–2:52.20 | Full throttle cut to around 8–10%, entering a turn | Immediate roll/pitch bobble and slower tracking error; differs from the repeated recovery flutter above |

[Combined close-ups](shortlist.png) show throttle context on the left and the actual recorded gyro against its command on the right. The shaded throttle region is the interval expanded in the gyro plots. Blue is the command and orange the gyro. These are rotation rates, not degrees of tilt.

**Interpretation**

The first four show brief repeated departures from the setpoint, with stronger bursts roughly in the 15–30 Hz region in the inspected candidates. The timing is consistent with disturbed airflow/propwash during manoeuvre recovery, potentially aggravated by damping or control-authority limits. Propwash is a working explanation, not a directly measured variable or a proven root cause. Some clear shakes also occur as throttle rises (for example LOG00026 near 1:57.8 and 4:10.8), so a throttle-release-only diagnosis would miss part of the pattern.

The fifth interval is a more immediate throttle-chop disturbance. I-term changes substantially, but this alone does not show that Anti Gravity is too high or too low: I is also responding to the disturbance. At least one motor reaches the minimum command of 158 in this interval, and the minimum reported mechanical RPM is about 3,043. This makes low-throttle authority worth inspecting. It does not demonstrate a stopped motor or desync.

During the two selected LOG00026 flutter intervals, reported mechanical RPM stays above about 10,500 and 13,100 respectively, and motor commands remain away from both limits. Enabling Dynamic Idle would therefore not directly establish a cure for those particular higher-RPM shakes.

The earlier highlighted brief yaw under-response near 2:07 in LOG00026 is a separate rapid-command event. It should not automatically be treated as the pilot's reported shaking.

**Tuning direction, after matching the symptom**

For repeated recovery flutter, evaluate roll/pitch damping (including D minimum/maximum behaviour) and gyro/D noise before a small, isolated D-related test. The recorded D minimum values are 30/34 and upper D settings 40/46 for roll/pitch. Raising D increases motor load and can amplify noise; a later change should use a short repeatable test and motor-temperature feedback. A numerical change is not established by the frequency of the shake alone.

For the immediate throttle-cut bobble, inspect low-throttle motor authority and Anti Gravity separately. Dynamic Idle is currently disabled (`dyn_idle_min_rpm=0`), with fixed DShot idle 5.5%, despite bidirectional DShot/RPM data being present. Choosing an appropriate RPM target requires the actual motor/prop setup and healthy RPM telemetry. Do not apply historical 4.2 idle instructions or current-version CLI names indiscriminately to this 4.5.1 build.

The next useful input is identifying which listed sequence matches the pilot's sensation; motor model/KV, prop model, and whether motors get hot are needed for a justified tuning prescription. No PID/filter configuration has been changed and no claim of a verified fix is made.

**Method and limits**

The automated screen uses an 8–80 Hz bandpass of gyro-minus-setpoint, a 150 ms RMS window, and excludes nearby commands above 180 deg/s or substantial oscillatory setpoint content. Peaks are separated by at least 1.1 seconds. This is a heuristic candidate search, not an exhaustive detector: very slow bobbles, high-frequency vibration, and disturbances during large commands may be missed. Filtering can ring around transients, so selected conclusions use the original recorded time traces, not just the detector score. Millisecond candidate peak timestamps are algorithm outputs; review-window boundaries are approximate visual selections.

`candidates.csv`/`candidates.json` contain the automated list, which includes unreviewed false-positive candidates. `shortlist.json` contains the reviewed windows, raw rate-error ranges, and flight-controller clock equivalents if a viewer displays time since boot. GPS/video alignment has not been performed.

Relevant official references: [D minimum and dynamic damping](https://betaflight.com/docs/wiki/guides/current/DMIN), [Dynamic Idle](https://betaflight.com/docs/wiki/guides/current/Dynamic-Idle), and [PID tuning controls](https://betaflight.com/docs/wiki/app/pid-tuning-tab). These explain possible mechanisms; the event measurements above come from the local logs.
