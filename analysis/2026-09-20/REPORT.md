# September 20: shaking, motor response and charge-calibration preparation

All eight files in `20_9_2026_bfl` decode with zero invalid callbacks, no main-frame gaps above 5 ms, and clean log-end events. Median sample interval is 987 microseconds (approximately 1,013 Hz); maximum intervals are 1,033-1,059 microseconds. Logging worked for these recordings. This does not establish what fixed the earlier empty files or guarantee future reliability.

The pilot reports new, unscratched props today. Today's prop-nut tightness, whether the prop model is unchanged, and exact perceived sound times have not been confirmed. Charger numbers will be provided later.

## Configuration and recording inventory

All today's logs have Dynamic Idle 35, simplified D gain 110, roll PID 45/80/44, pitch PID 47/84/50, D-min 33/37, motor poles 14, and ADC current offset 0 / scale 400. Compared with September 15 LOG00008, raw headers differ only in datetime, battery reference, and roll/pitch RC rate (218 -> 212). Today's main flights otherwise share the same recorded configuration.

Times below are local Europe/Zagreb (UTC+2), from log header datetimes. Durations are from first to last decoded main sample, not necessarily the OSD's exact timer.

| Log | Start | Recorded duration | Integrated recorded mAh |
|---|---|---|---:|
| LOG00001 | 15:48:22 | 0.70 s | 0.19 |
| LOG00002 | 15:48:48 | 5:43.65 | 464.66 |
| LOG00003 | 15:58:49 | 0.38 s | 0.12 |
| LOG00004 | 15:59:19 | 2:09.18 | 192.27 |
| LOG00005 | 16:01:47 | 1.56 s | 1.98 |
| LOG00006 | 16:04:02 | 2:50.88 | 291.83 |
| LOG00007 | 16:33:27 | 1.17 s | 0.31 |
| LOG00008 | 16:33:32 | 5:41.62 | 529.27 |

LOG00001/03/07 are brief near-stationary recordings. LOG00005 contains a short movement/contact event (peak gyro 1,398 deg/s and acceleration 7.31 g); do not describe all short files as stationary. Main flights show no recorded failsafe activation and end with switch-disarm reason 4. The endings of LOG00006/08 include contact-sized acceleration peaks (12.62/13.90 g); excluded from normal-flight metrics. These are not independent determinations of crash severity.

## Shaking candidates to review

Follow-up: [first-battery Split-S-like manoeuvre and sub-500 ms correction search](split_s/REPORT.md), including a four-event shortlist based on the pilot's description.

Further comparison: [today versus pre-Dynamic-Idle and first Dynamic Idle flights](recovery_comparison/REPORT.md). The RPM-regulation improvement remains; throttle-recovery disturbance scores are mixed, with stronger selected disturbances in today's first flight. Lower background vibration below should not be interpreted as universally less propwash.

There are brief, real differences between commanded and measured rotation, with simultaneous D and motor-correction activity. The strongest reviewed examples occur when throttle rises after a low/zero-throttle interval. This is consistent with throttle-recovery turbulence/propwash and controller response; the logs do not uniquely prove the aerodynamic or mechanical cause.

| Log and elapsed time | Observed context | Evidence |
|---|---|---|
| **LOG00002 5:28.6** | Zero/low-throttle coast, then a punch to roughly 74%; roll and pitch oscillate briefly and recover | [Plot](results/LOG00002_shake_328.61.png) |
| **LOG00004 0:48.7** | Zero throttle while turning, then power rises toward 57%; a distinct roll/pitch burst around 48.5-48.9 s | [Plot](results/LOG00004_shake_48.67.png) |
| **LOG00008 2:13.1** | Low/zero throttle followed by a punch toward 75%; brief roll/pitch correction burst | [Plot](results/LOG00008_correction_133.10.png) |
| **LOG00008 4:07.5** | Roll manoeuvre during a throttle cut, then power returns; short disturbance at recovery | [Plot](results/LOG00008_shake_247.53.png) |

Other algorithm-selected examples include LOG00002 1:27.6 and 4:00.0, LOG00004 1:40.2, LOG00006 0:30.6, and LOG00008 5:13.2. These are candidates, not confirmed acoustic timestamps. The script ranks both 8-80 Hz tracking-error bursts and 100-450 Hz differential motor-command bursts. They need not rank identically: high-frequency corrections can be strong even when the visible wobble is small. "Low command" in the JSON means limited angular-rate commands, not necessarily low throttle.

The 0.4-second window centered on LOG00004 48.668 s contains neither minimum nor maximum motor-command saturation. LOG00002 328.614 s briefly reaches a maximum command (about 2% of samples), but no minimum command. This does not support one universal explanation based on motor saturation for every burst.

No audio is recorded. With approximately 1,013 samples/s, the analysis cannot resolve the full audible spectrum: its 100-450 Hz band is recorded control/vibration content, not the pitch of the sound. DShot RPM reports motor rotation, not an independent measurement of prop rotation or thrust; it cannot exclude prop slip. See [Betaflight RPM telemetry documentation](https://betaflight.com/docs/wiki/guides/current/DSHOT-RPM-Filtering).

## Motor-speed screening and Dynamic Idle

Across usable flight in LOG00002/04/06/08:

- No reported zero-RPM samples; minimum RPM is respectively 2,914 / 2,971 / 2,986 / 2,900.
- No candidates for a >40% RPM drop in 20 ms from above 8,000 RPM while a substantial motor command remains stable over the preceding 80 ms. The corresponding stable-command rise screen also returns no candidates.
- Less restrictive RPM-drop flags occur during large command changes/braking and are not classified as failures solely from the speed change.
- During zero-throttle forward flight, the median slowest-motor RPM is 3,500-3,514. Only 0.003-0.017% of those samples are below 3,000 RPM.

These findings support continued idle regulation and do not show an obvious motor stop or stable-command speed collapse in the screened portions. They do not certify healthy motors, bearings, ESCs, props or fasteners. The screen excludes the first/last five seconds, contacts and nonmanual modes; it is deliberately not a universal desync detector.

## Comparison with September 15 first battery

Matched nonoverlapping 0.5-second manual-flight windows against September 15 LOG00008 using throttle, speed, angular-command magnitude, voltage, throttle variation and mean RPM. Eligibility and matching use flight conditions, not the measured noise outcome. Each comparison independently reuses the reference pool; counts must not be treated as independent experimental replicates.

| Today's log | Matched pairs | Raw gyro 100-450 Hz RMS, before -> today (deg/s) | Roll/pitch 8-80 Hz error RMS, before -> today (deg/s) |
|---|---:|---:|---:|
| LOG00002 | 288 | 6.74 -> 4.63 | 1.57 -> 1.15 |
| LOG00004 | 126 | 6.74 -> 4.64 | 1.59 -> 1.27 |
| LOG00006 | 170 | 6.45 -> 4.45 | 1.67 -> 1.36 |
| LOG00008 | 289 | 6.71 -> 4.47 | 1.59 -> 1.16 |

These median values show lower background vibration/error in comparable selected conditions, while short recovery bursts remain. They do not establish that today's props caused the difference or that every manoeuvre improved. The flights are not controlled repetitions, and RC rates changed slightly. No new PID or filtering change is justified solely by these aggregate numbers. Retain Idle 35 and the recorded tune while correlating the selected events with the pilot's observations/audio.

## Battery calibration: pending charger measurements

Likely groups, inferred from timestamps, uninterrupted controller uptime and voltage progression, **not yet confirmed by the pilot**:

| Tentative battery session | Files | Sum of recorded mAh |
|---|---|---:|
| First | LOG00001 + LOG00002 | **464.85** |
| Second | LOG00003 + LOG00004 + LOG00005 + LOG00006 | **486.20** |
| Third | LOG00007 + LOG00008 | **529.58** |

These values integrate already-calibrated current at scale 400; they are not independent true consumption. They omit unlogged ground draw, startup/header time and disarmed gaps. The middle session includes substantial disarmed time, making its log-only total a poorer direct comparison with a recharge total. An OSD total captured before unplugging is preferable if available.

Leave scale **400**, offset **0** until charger-added mAh and battery mapping are supplied. For ADC scaling with unchanged offset: `new scale = old scale * indicated mAh / reference mAh`. A matched full-to-full recharge gives an approximate reference; verify over further packs. Do not substitute label capacity or infer true consumed charge from voltage. [Betaflight battery/current calibration](https://betaflight.com/docs/wiki/guides/current/Battery).

## Reproduction

```text
node analysis/decode.mjs 20_9_2026_bfl analysis/2026-09-20/decoded
python analysis/2026-09-13/inventory.py analysis/2026-09-20
python analysis/2026-09-20/review.py
```

Outputs: [inventory](inventory.json), [recorded current integration](current_usage.json), [vibration/RPM results](results/summary.json), event plots and matched-window CSVs in `results/`. Decoder warnings about unsupported configuration headers do not indicate corrupted flight frames; original headers are retained and the analysis reads their raw values where needed.
