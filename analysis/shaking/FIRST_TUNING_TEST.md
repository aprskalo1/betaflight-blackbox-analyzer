The pilot confirmed that the remembered shake occurs when restoring throttle after a low-throttle coast. The hardware supplied is Ethix 3.3 props (interpreted as Ethix P3.3 Mango Lassi) and iFlight XING2 2207 1855KV motors. Motor temperature has not yet been established.

Update after receiving the current `diff all`: firmware matches the logs and all four PID profile sections contain no changes from defaults. The active PID profile is CLI index 2 (third profile; normally Profile 3 in Configurator), and the active rate profile is CLI index 0 (first profile). The default P/I/D/FF and D-min settings match the logged baseline below. The custom rates also match the Sunday log. The supplied configuration is stored in `../current_diff_all.txt` as backup text; it has not been executed. Apply the proposed test to the active third PID profile only. Motor temperature remains the outstanding physical check.

**Recommendation: one small D-damping experiment**

Provided the present setup still matches the Sunday logs and motors are not already running hot, test the Betaflight PID Tuning **Damping / D Gains** slider at **1.10**, up from the recorded 1.00. This is a roughly 10% increase to roll/pitch base and upper D values. It is a first comparison test, not a proven cure or an estimate of the optimal gain.

The recorded configuration exactly matches the Betaflight 4.5.1 PID defaults with simplified tuning multipliers at 100. Its 4.5.1 simplified-tuning calculation gives these expected integer values:

| Setting | Sunday baseline | First test |
| --- | --- | --- |
| Damping / D Gains multiplier | 1.00 | 1.10 |
| Roll D minimum (`d_min_roll`) | 30 | 33 |
| Pitch D minimum (`d_min_pitch`) | 34 | 37 |
| Roll upper D (`d_roll` in 4.5.1) | 40 | 44 |
| Pitch upper D (`d_pitch` in 4.5.1) | 46 | 50 |

Use the Damping / D Gains slider for this trial. It is different from the D Max / dynamic damping ratio slider and from a filter slider. P, I, feedforward, rates, filters, TPA, Anti Gravity, and Dynamic Idle should stay at the baseline for this comparison, so that the result can be attributed to the one D-gain adjustment. Inspect the resulting PID values before saving; if the existing settings differ, the table is not applicable verbatim.

**Why this is the first test**

During LOG00026 at 295.0–295.8 seconds, the motors report roughly 13,143–20,457 mechanical RPM and all output commands remain between their lower and upper limits. There is no apparent motor stop or output saturation within that interval. The preceding zero-throttle coast has motors as low as 2,800 RPM, but much smaller tracking errors than the subsequent shake. This makes a simple idle-floor problem a weaker direct explanation for the confirmed shake.

The disturbance is concentrated in low-frequency roll/pitch motion. In the 8–80 Hz band, roll/pitch tracking-error RMS is about 5.85/7.94 deg/s during the confirmed event, versus 1.44/1.41 in a steadier 0.8-second interval at a similar throttle. These windows are different manoeuvres at different battery states, not a controlled causal comparison. In the 100–450 Hz band, filtered roll/pitch gyro RMS during the shake is about 0.74/0.90 deg/s. The comparison supports a short recovery disturbance rather than dominant continuous high-frequency gyro noise in the sampled band.

Approximately 1 kHz logging cannot assess gyro noise above its Nyquist limit or rule out aliasing. The logs contain D contribution, but not the debug signal for instantaneous dynamic-D gain. Therefore the exact D-min activation, filter safety margin, and motor temperature are not known. More D may improve damping, or may prove unhelpful; it must be judged in a comparison flight.

**How to run the comparison**

1. Save `diff all` from the CLI as a text backup and note the active PID profile. Keep the same prop model, payload, and battery type. Check props, motor bells, and FC mounting for visible damage or looseness before interpreting this as a tuning issue.
2. If motor temperature has not been checked, make a short baseline flight first and inspect all four motors after disarming. If any are already hot/uncomfortable to touch, investigate that before increasing D. The logs do not replace this check.
3. Apply only the Damping / D Gains change from 1.00 to 1.10 and save. Verify the expected gains above. Do a short hover, land, disarm, and check motor temperature and sound before progressing.
4. In a clear area with recovery height, perform three to five modest, repeatable low-throttle-to-powered recoveries resembling the confirmed event. A 20–30 second test is enough initially; there is no need for full-throttle dives or aggressive manoeuvres. Stop if a new buzz, sustained oscillation, or unusual heating appears.
5. Save the new Blackbox log, mark it as Damping 1.10, and record whether the shake improved and whether motor temperatures changed. Compare similar recoveries, not simply each flight's single largest peak. Similar battery charge and manoeuvre speed make the comparison more useful.
6. If the result worsens or there is unusual heating, restore the Damping slider to 1.00 and verify the original values 30/34 (minimum) and 40/46 (upper). If it improves without a heat/noise penalty, retain that candidate while reviewing the new log before another increment. If there is no repeatable improvement, return to baseline and reconsider the mechanism rather than increasing D repeatedly.

No settings have been sent to a flight controller. The plan is conditional on a normal baseline temperature check. Dynamic Idle and Anti Gravity remain possible later investigations, not simultaneous changes in this first experiment.

**Verification sources**

- [iFlight XING2 2207 1855KV](https://iflight-rc.eu/en/products/xing2-2207-1855kv-fpv-motor): 6S variant, 12N14P configuration. The published 14 motor poles agree with the log's `motor_poles=14`, validating the RPM conversion on the stated hardware.
- [HQProp Ethix range](https://hqprop.com/search/?Keyword=P3+5.1x3x3&Sort=2d): identifies the P3.3 Mango Lassi product. P3.3 identification is an interpretation of the pilot's shorthand, not a prop marking read directly by the assistant.
- [Betaflight 4.5.1 simplified-tuning calculation](https://github.com/betaflight/betaflight/blob/4.5.1/src/main/config/simplified_tuning.c) and [PID defaults](https://github.com/betaflight/betaflight/blob/4.5.1/src/main/flight/pid.h): checked to distinguish base D from upper D and verify the effect of the D-gain multiplier for this firmware. Later Betaflight releases use different D naming.
- [Betaflight D-min guide](https://betaflight.com/docs/wiki/guides/current/DMIN): explains lower cruise damping with dynamically boosted D during manoeuvres/disturbances. This supports the mechanism being tested, not the specific 1.10 value; that value is the proposed small experimental step.

Supporting artifacts: `tuning_evidence.json`, `tuning_spectra.png`, `shortlist.png`, and the original decoded full-resolution data. Analysis script: `../tuning_evidence.py`.
