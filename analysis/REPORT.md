All seven Blackbox files from Sunday, 6 September 2026 have been decoded and inspected. They contain four full flights and three very short stationary recordings. The latest flight is LOG00026.BFL. There are 1,427,801 decoded main-loop samples in total, with zero corrupt or desynchronised frames reported by the official Betaflight parser, and no missing scheduled main-loop samples detected (iteration advances by four throughout).

**Flight inventory**

Times below reproduce the log header clock. The headers label these times +00:00; the flight-controller clock/timezone has not been independently verified. Durations run from the first to last recorded main sample and include time on the ground.

| File | Header start time | Recorded duration | Peak recorded GPS ground speed | Maximum horizontal distance from recorded home |
| --- | --- | --- | --- | --- |
| LOG00020.BFL | 15:15:12 | 1.00 s | 0.4 km/h | <1 m |
| LOG00021.BFL | 15:15:34 | 6 min 13.77 s | 134.9 km/h | 239.5 m |
| LOG00022.BFL | 15:26:30 | 0.80 s | 0.2 km/h | <1 m |
| LOG00023.BFL | 15:26:50 | 5 min 2.40 s | 149.4 km/h | 105.0 m |
| LOG00024.BFL | 15:36:28 | 0.67 s | 0.2 km/h | <1 m |
| LOG00025.BFL | 15:36:42 | 5 min 58.25 s | 155.8 km/h | 87.8 m |
| LOG00026.BFL | 15:47:25 | 6 min 11.90 s | 127.9 km/h | 90.0 m |

The short files have zero throttle throughout, gyro readings within roughly 1–2 degrees/second, and essentially no GPS movement. They are consistent with brief arming/disarming on the ground, rather than airborne flights. Some contain rapid ARM mode-switch changes. Their cause is not established by these logs.

**What happened in the latest flight, LOG00026**

- At about 2.3 seconds the throttle rises above 5%; GPS motion follows. The first minute consists mainly of repeated local circuits, with moderate stick throttle and smaller rotational commands.
- From about 1:16 onward there are repeated rapid pitch and roll manoeuvres, interspersed with circuits and throttle bursts. They are consistent with freestyle flying. Rotation rates reach 1,173 degrees/second in roll and 1,179 degrees/second in pitch. Rates alone do not establish the exact name or full attitude sequence of each trick.
- Around 2:01–2:07 there are two clear sequences of a throttle burst, reduced throttle, a rapid pitch command, then a combined roll/yaw command. The tracking chart shows that these large rotations were commanded. Yaw falls substantially short of the brief high-rate requests: at about 127.000 seconds, yaw setpoint is 857 degrees/second while measured yaw is 218 degrees/second; roll is simultaneously commanded at 1,169 degrees/second and measured at 928 degrees/second. This warrants a closer motor/PID examination before attributing it to a particular gain or hardware limitation.
- The largest recorded distance from home is about 90 m. Peak GPS ground speed is 127.9 km/h at 4:23.73. These are GPS measurements, not independently verified speed or distance.
- The flight slows near its end. The final GPS speed is about 2.1 km/h, barometer is near its starting level, and throttle falls to zero. A switch-disarm event occurs at 6:11.90. This is consistent with the end of a landing. The log ends roughly 46 m from its recorded home point, so it does not show a landing exactly at home.
- No receiver-loss or failsafe transition was recorded. Receiver signal and flight-channel-valid flags remain true; failsafe phase remains IDLE. No GPS Rescue mode activation is recorded in this flight.

**GPS Rescue in LOG00021**

At 3:29.484, the GPS Rescue mode-switch flag activates with the aircraft about 239.5 m from home. It climbs: the barometer rises from about 19.6 m to around 49 m, while the GPS altitude change from the start reaches about 39.8 m. It then returns toward home at around 27 km/h. By 4:02.521, it is about 45.2 m from home and the Rescue flag switches off. The interval lasts 33.038 seconds. Flying continues afterward.

The receiver remains valid and the failsafe phase stays IDLE throughout. This strongly suggests a manually selected Rescue test rather than a radio-loss failsafe; pilot intent itself is not recorded. During most of the return the stick-throttle channel is zero, which must not be interpreted as the motors stopping: Rescue supplies the final mixer throttle separately.

**Other full flights**

LOG00023 and LOG00025 both show repeated local circuits, rapid rotations, and short high-throttle runs. Their peak GPS speeds occur at 2:51.46 and 4:03.89 respectively. Neither records GPS Rescue selection, receiver loss, or a failsafe transition. Both end with a switch-disarm event. All seven files have a valid log-end event and disarm reason 4, which is SWITCH in Betaflight 4.5.1.

**Recorded setup**

The controller identifies itself as Betaflight 4.5.1 (77d01ba3b), build date 31 January 2026, board SPBE SPEEDYBEEF405V4 / STM32F405. The recorded settings and field definitions are identical across all seven files except the start timestamp and reference battery voltage. That includes the PID/filter configuration; these files do not represent different recorded PID tunes.

| Axis | P | I | D setting | D minimum | Feedforward weight |
| --- | --- | --- | --- | --- | --- |
| Roll | 45 | 80 | 40 | 30 | 120 |
| Pitch | 47 | 84 | 46 | 34 | 125 |
| Yaw | 45 | 80 | 0 | 0 | 120 |

Bidirectional DShot is enabled, motor poles are configured as 14, and RPM filtering has three harmonics. Dynamic notch count is one. Gyro LPF1 is configured dynamically at 250–500 Hz, LPF2 at 500 Hz; D-term LPF1 dynamically at 75–150 Hz and LPF2 at 150 Hz. These are recorded configuration values, not a claim that this is an optimal tune.

The nominal PID loop is 4 kHz from the header, with logging every fourth PID iteration. Measured sample spacing is typically 987 microseconds, approximately 1,013 samples/second; GPS updates are approximately 10 Hz. No debug channels are present (debug_mode=0), but unfiltered gyro and RPM channels are present.

**Measurement limits and observations relevant to later tuning**

All full flights reach 100% stick throttle. At least one motor reaches its upper command limit for approximately 0.81%, 0.87%, 0.98%, and 1.00% of main samples in LOG00021/23/25/26 respectively. This identifies brief output saturation, not a motor fault by itself.

Battery start readings are about 25.1 V, consistent with a charged 6S pack. In LOG00026 the final one-second median is 21.60 V. Raw instantaneous minima are much lower (17.55–17.98 V across the four flights), but approximately 100 ms moving-average minima are 19.80–20.12 V. The voltage traces contain fast fluctuations; interpreting a single raw minimum as sustained battery voltage would be misleading. Current and integrated consumption depend on sensor calibration, which has not been verified.

Altitude needs care. There are sharp positive and negative barometer excursions during manoeuvres, and disagreement/drift between GPS and barometer. LOG00026 ranges from -21.98 to +47.43 m on the raw barometer, while its maximum GPS altitude change from the start is +23.5 m. Neither is a terrain-referenced height measurement; the barometer extrema do not establish the actual highest and lowest physical altitude.

The logs record angular rates, not direct absolute roll/pitch/yaw attitude or a fused attitude quaternion. Attitude could be estimated from gyro/accelerometer data, but that would be derived, subject to drift and acceleration errors, and is not included as a directly measured parameter. GPS ground course is direction of travel, not necessarily the direction the drone's nose points.

This is a flight reconstruction and initial signal review. No PID/filter settings have been changed. These observations do not yet establish a final PID tune, motor temperature, prop condition, a specific mechanical fault, or the presence/absence of every possible crash or vibration issue.

**Saved material**

- [Four flight paths](results/flight_paths.png)
- [Latest flight overview](results/LOG00026.overview.png)
- [Latest flight command/gyro comparison](results/LOG00026.tracking.png)
- [First flight overview, with Rescue interval](results/LOG00021.overview.png)
- [All recorded field names, meanings, and units](FIELD_GUIDE.md)
- [Ranges of every recorded numeric field in every file](results/all_recorded_field_ranges.csv)
- [Machine-readable summaries](results/summary.json)
- [Event measurements and rapid-rotation intervals](results/event_details.json)
- Full-resolution decoded CSVs, all original header settings, parser statistics, and events are under `decoded/`. The original BFL files remain the source of truth.

**Method and sources**

Decoding uses the [official Betaflight Blackbox Explorer parser](https://github.com/betaflight/blackbox-log-viewer). The local adapter changes module resolution and removes an unused UI-settings dependency; binary decoding algorithms are unchanged. Some configuration headers are not recognised by the parser's UI configuration model; every original header is separately preserved verbatim in `decoded/*.headers.txt`. No invalid frames were included in the CSVs; none were reported for these files.

Mode-switch semantics and the distinction between stick and mixer throttle were checked against [Betaflight 4.5.1 Blackbox source](https://github.com/betaflight/betaflight/blob/4.5.1/src/main/blackbox/blackbox.c) and [mode identifiers](https://github.com/betaflight/betaflight/blob/4.5.1/src/main/fc/rc_modes.h). Switch-disarm reason was checked against [4.5.1 core definitions](https://github.com/betaflight/betaflight/blob/4.5.1/src/main/fc/core.h). Analysis scripts are `decode.mjs`, `analyse.py`, and `details.py`; numerical summaries use full-resolution samples, while overview plots use display sampling/envelopes.
