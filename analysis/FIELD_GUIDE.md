The exports preserve the decoded raw integer values. Main I and P frames are combined chronologically into each `.I.csv`. GPS `.G.csv`, home `.H.csv`, slow status `.S.csv`, and events in `.metadata.json` remain separate to preserve their recording cadence. The added `last_main_time` column on H/S records is the time of the preceding main sample, not an independently recorded H/S timestamp.

Axis indices 0, 1, 2 mean roll, pitch, yaw. Motor indices 0–3 are firmware motor numbers 1–4; physical corners depend on the mixer and motor mapping.

| Frame | Recorded fields | Meaning and conversion for these logs |
| --- | --- | --- |
| I/P | loopIteration | Recorded PID-loop iteration counter; increments by 4 between saved samples |
| I/P | time | Flight-controller time in microseconds; subtract first sample and divide by 1,000,000 for elapsed seconds |
| I/P | axisP[0..2] | Actual proportional controller contribution, internal PID units |
| I/P | axisI[0..2] | Actual integral contribution, internal PID units |
| I/P | axisD[0..1] | Actual derivative contribution for roll/pitch; no yaw D channel is recorded and yaw D is configured to zero |
| I/P | axisF[0..2] | Actual feedforward contribution, internal PID units |
| I/P | rcCommand[0..2] | Processed roll/pitch/yaw stick commands; not attitude angles or raw receiver pulse measurements |
| I/P | rcCommand[3] | Processed stick throttle in 1000–2000 range; approximate percentage = (value−1000)/10 |
| I/P | setpoint[0..2] | Rotation-rate targets supplied to the PID controller, degrees/second |
| I/P | setpoint[3] | Final mixer throttle ×1000; divide by 10 for percent; may differ from stick throttle |
| I/P | vbatLatest | Battery measurement in hundredths of a volt; divide by 100 |
| I/P | amperageLatest | Current measurement in hundredths of an amp; divide by 100; depends on calibration |
| I/P | baroAlt | Barometric altitude in centimetres; divide by 100 for metres; not terrain clearance |
| I/P | rssi | Generic RSSI scale; value/1024×100 is the Explorer percentage; not automatically dBm or an independent link-quality channel |
| I/P | gyroADC[0..2] | Filtered angular rates, degrees/second for this firmware and scale |
| I/P | gyroUnfilt[0..2] | Gyro before software filtering, degrees/second; sensor hardware filtering can still apply |
| I/P | accSmooth[0..2] | Accelerometer counts, 2048 per g; specific force including gravity response, not direct world-space acceleration |
| I/P | motor[0..3] | Motor output command, not measured RPM; header motorOutput range is 158–2047. Fraction of this configured range = (value−158)/(2047−158); this differs from physical DShot scale starting at 48 |
| I/P | eRPM[0..3] | Electrical RPM in hundreds; mechanical RPM = value×200/14 using recorded 14 motor poles; pole-count accuracy is assumed |
| G | time | Timestamp in microseconds, same flight-controller timebase |
| G | GPS_numSat | Reported satellite count |
| G | GPS_coord[0..1] | Latitude/longitude in degrees×10^7; divide by 10,000,000 |
| G | GPS_altitude | GPS altitude in decimetres; divide by 10 for metres above mean sea level as presented by Explorer; not height above terrain |
| G | GPS_speed | Recorded GPS ground speed, cm/s; divide by 100 for m/s or multiply by 0.036 for km/h |
| G | GPS_ground_course | Course over ground in tenths of a degree; divide by 10; not nose heading |
| H | GPS_home[0..1] | Recorded home latitude/longitude, degrees×10^7 |
| S | flightModeFlags | RC mode-activation bitmask. In these recordings 0=no selected modes, 1=ARM selected, 129=ARM plus GPSRESCUE selected. This is not the firmware's separate internal flight-mode bitmask |
| S | stateFlags | GPS status bits; 7 indicates home fix, current fix, and a fix acquired at some point |
| S | failsafePhase | Failsafe state; 0=IDLE throughout these logs |
| S | rxSignalReceived | Receiver-signal-valid Boolean; 1 throughout |
| S | rxFlightChannelsValid | Flight-channel-valid Boolean; 1 throughout |
| E | event + event data | Synchronisation beep, mode changes, disarm reason, and log end; see each metadata JSON |

There are 42 main fields, seven GPS fields, two home fields, and five slow status fields. The main fields are recorded around 1 kHz, GPS around 10 Hz, and slow status on change/periodically. Repeated GPS values must not be treated as independent 1 kHz position measurements.

The static configuration headers additionally record PID and rate settings, filter configuration, motor/receiver setup, GPS Rescue parameters, firmware identity, and logging configuration. These are preserved in full in `decoded/*.headers.txt`. They are settings, rather than additional time-varying measurements. Sensor temperatures, video, individual cell voltages, explicit attitude angles/quaternions, magnetometer measurements, and debug channels are not present in these files.
