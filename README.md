# Betaflight Blackbox Analyzer

Scripts and analysis reports for decoding Betaflight Blackbox flight logs, comparing PID settings and propwash recovery, and investigating crashes and disarms.

Repository name: `betaflight-blackbox-analyzer`.

## Capabilities

- Decode `.BFL` files using the official Betaflight Blackbox Explorer parser.
- Read recorded configuration, gyro measurements, setpoints, PID contributions, throttle, motor RPM, GPS, and flight events.
- Compare flight segments and throttle recoveries across tuning changes.
- Generate charts and evidence-based reports with crash and disarm timelines.

The current project consists of local Node.js and Python analysis scripts. Its decoder uses the Blackbox Explorer source under `analysis/tools/blackbox-log-viewer`; the Python scripts use the locally installed packages under `analysis/tools/pythonpkgs`. Dependency setup is currently specific to this workspace.

## Analysis files

- [Decoder](analysis/decode.mjs)
- [Recorded-field reference](analysis/FIELD_GUIDE.md)
- [6 September flight analysis](analysis/REPORT.md)
- [13 September tuning comparison](analysis/2026-09-13/REPORT.md)
- [13 September crash analysis](analysis/2026-09-13/crash/REPORT.md)

Run the decoder from the project root with an input directory and a separate output directory:

```text
node analysis/decode.mjs 13_9_2026_bfl analysis/2026-09-13/decoded
```

Each dated report documents the commands used to reproduce its analysis.
