# Is the original Dynamic Idle improvement still present?

**The recorded tuning is unchanged from September 15's first Dynamic Idle flight and crash flight: Dynamic Idle 35, simplified D gain 110, roll/pitch D 44/50, D-min 33/37, and the same recorded filters. Today's low-throttle RPM regulation remains improved over the pre-Dynamic-Idle flights. A universal reduction in throttle-recovery shaking is not established.**

Raw headers from September 15 LOG00008 and LOG00009 versus September 20 LOG00002 differ only in datetime, battery reference and RC rates (roll/pitch 218 -> 212). The crash log is used only for configuration confirmation, not as a complete-flight performance reference.

September 13 LOG00006/07 have the same damping/PIDs but Dynamic Idle off. As previously measured, any motor falls below 3,000 RPM during about 11%/17% of selected near-zero-throttle flight. September 15 first flight is about 0.011%; today's four long logs are 0.003-0.017%, with median slowest-motor RPM 3,500-3,514. That is the clearest retained benefit. These percentages describe samples in the selected conditions, not motor-failure probabilities.

## Recovery comparison

Reused September 15's recovery extraction and matching definitions: crossing 20% throttle after a low-throttle period, with roll/pitch 8-80 Hz gyro-minus-setpoint RMS measured 0.05-1.05 s after the crossing. Excluded contacts, nonmanual modes and large ongoing stick activity. There are 56 eligible pre-idle recoveries, 25 in September 15's first flight, and 87 today (19 in today's first main flight).

Matched without replacement on mean throttle, speed, maximum angular command, voltage, preceding angular-command magnitude and preceding speed. Reference matching tolerance is 1.5, as in the original Dynamic Idle analysis. These match observable conditions, not actual wake inflow, orientation, wind or identical manoeuvre geometry.

| Reference | Today's selection | Pairs | Reference median error RMS | Today median error RMS | Pairs lower today |
|---|---|---:|---:|---:|---:|
| Sept 13, Idle off | First flight LOG00002 | 14 | 4.05 deg/s | 6.29 deg/s | 3/14 |
| Sept 13, Idle off | All four main flights | 47 | 3.81 deg/s | 3.74 deg/s | 27/47 |
| Sept 15, first Idle 35 flight | First flight LOG00002 | 13 | 5.23 deg/s | 6.15 deg/s | 6/13 |
| Sept 15, first Idle 35 flight | All four main flights | 21 | 4.76 deg/s | 4.42 deg/s | 10/21 |

Today's first flight has larger recovery disturbances in these matched samples. The all-today comparison is broadly similar to the pre-idle flights, not compelling evidence of a propwash reduction. Against the first Idle 35 flight, the all-today group medians are slightly lower at the reference tolerance, but change direction with stricter/looser matching. Do not present 7% lower as a reliable tuning gain.

Sensitivity to matching tolerance 1.0 / 1.5 / 2.0:

- Sept 13 vs first flight: 11/14/18 pairs, reference medians 3.94/4.05/3.87, today's 6.15/6.29/5.61 deg/s.
- Sept 13 vs all today: 27/47/54 pairs, reference 3.81/3.81/3.79, today 3.74/3.74/3.85.
- Sept 15 vs first flight: 7/13/15 pairs, reference 5.37/5.23/4.76, today 6.15/6.15/6.15.
- Sept 15 vs all today: 14/21/24 pairs, reference 4.93/4.76/4.31, today 5.79/4.42/4.98.

Each comparison selects a different matched reference subset. Do not compare table rows as if their reference medians represented fixed whole-flight scores. Events are repeated samples from a few flights, not independent controlled trials. Today's props are new and RC rates differ slightly. Higher measured error does not prove a tuning regression or negate the pilot's improved low-throttle feel.

The prior report's lower background vibration refers to steady, half-second general-flight windows. That finding and stronger transient recovery disturbances can both be true. Neither metric identifies the audible wheeze.

Recommendation: preserve the existing Idle 35/damping 1.10 baseline; no new setting change is supported by this comparison alone. The retained RPM regulation is clear; further propwash optimization needs more comparable manoeuvres and should not be inferred from the brief sound alone.

Reproduce: `python analysis/2026-09-20/recovery_comparison.py`. [Numerical output](comparison.json); matched-pair CSVs and today's extracted recoveries are in this directory.
