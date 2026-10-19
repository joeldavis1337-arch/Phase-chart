# Phase App regression tests

These run the real `index.html` in a headless browser, load each case into the app,
run the diagnosis engine, and check the findings against what's expected.
Nothing here is used by the live app.

## Run

```
pip install playwright
python -m playwright install chromium
python3 tests/run.py            # tests ../index.html
python3 tests/run.py path/to/other/index.html
```

Output lists every case as PASS/FAIL with its findings, then a total.
Screenshots of each case's chart go to `tests/out/` (not committed).

## Add a case

Add one block to `cases.json`:

```json
{
  "id": "P-101-2026-10",
  "source": "Field job, what it is",
  "unit": "in/s",
  "layout": "H",
  "nodes": [
    {"name": "Driver", "shape": "Motor", "coupSide": "R", "meas": [
      ["HORIZ_NDE", "H1", 0.047, 1, {"ref": true}],
      ["AX_IB", "A2", 0.014, -179, {"axDir": "out"}]
    ]},
    {"name": "Driven", "shape": "Pump", "coupSide": "L", "meas": [
      ["AX_IB", "A4", 0.005, 9, {"axDir": "out"}]
    ]}
  ],
  "expect": {
    "present": ["Axial Phase Normal"],
    "absent": ["Angular Misalignment"]
  }
}
```

Each measurement is `[position code, label, amplitude, phase, {options}]`.
Options: `ref`, `axDir` (`in`/`out`). Node options: `bearingType`, `phaseUnstable`.
Case options: `detect` (`pk`/`rms`), `iso` (`{"group":"1|2|auto","found":"rigid|flex"}`).

Expectation keys (all optional):

| Key | Meaning |
|---|---|
| `present` | finding labels that must appear (substring match) |
| `absent` | finding labels that must not appear |
| `maxSeverityOf` / `minSeverityOf` | `{label: "info|warn|fault"}` severity limits |
| `descContains` | `{label: text}` text that must be in that finding's description |
| `bannedText` | text that must not appear in any description |
| `bubbles` | `{sensor label: "ok|warn|fault"}` expected bubble colours |
