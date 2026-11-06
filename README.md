# Dimensional inspection with a camera

Turn synthetic edge spans into millimetres. Fit two reference widths, check a third, and classify parts using a stated tolerance and allowance. This lab starts **after** edge detection. It does not use a camera or drive inspection equipment.

Full lesson: [Dimensional Inspection with a Camera](https://wifarobotics.com/learn/dimensional-inspection-camera/).

## Get started

1. Install Python 3.12 or newer from [python.org](https://www.python.org/downloads/). On Windows use the official installer or Python install manager and verify the launcher with `py -3 --version`.
2. Use GitHub's **Code → Download ZIP**, extract it, and open a terminal in the folder containing `inspect_width.py`.
3. Check `python3 --version`. On Windows replace `python3` with `py -3` in the commands below. Nothing needs to be installed with pip.

```sh
python3 inspect_width.py examples/nominal.json
python3 inspect_width.py examples/shifted-check.json
python3 inspect_width.py examples/boundaries.json
python3 -m unittest discover -s tests -v
```

## What you should see

| Example | Check residual | Results in order |
| --- | --- | --- |
| nominal | +0.010 mm, pass | accept 15.040 mm; review 15.080 mm; reject 15.200 mm; hold outside calibration |
| shifted-check | +0.050 mm, fail | hold even for the centered part |
| boundaries | −0.020 mm, pass | accept at both inner boundaries; review at exact overlap; reject just past overlap |

The nominal calibration is `width_mm = 0.1 × span_px − 0.2`. The check residual is predicted minus reference. If it exceeds the absolute limit, no part decision is made. The decision rule accepts a closed measurement interval fully inside the closed tolerance, rejects if they are disjoint, and asks for review otherwise. Exact rational comparisons precede display rounding, so two displayed widths can appear equal while their decisions differ.

Try changing the nominal check span from `152.1` to `152.4`: the residual becomes +0.040 mm and all parts go to hold. Revert the fixture before running the unit tests.

## Files

* `inspect_width.py`: Python CLI and pure functions.
* `examples/`: editable JSON fixtures. Units are pixels for edge spans and mm for all widths, tolerances, allowances and check limits.
* `tests/`: independent integer interval oracle, numerical fixtures, input and CLI checks.
* `diagrams/`: editable SVGs and matching optimized WebPs.

## Troubleshooting

If Python cannot open the file, navigate to the directory containing `inspect_width.py`. Input errors exit with code 2 and a message; a valid fixture with a failed check returns a JSON hold decision and exits 0. If the check fails, inspect the span, units and measurement setup before evaluating parts. Never widen the residual limit just to make the result pass.

This is a synthetic single-plane affine fit with one independent check. The allowance is supplied by the fixture. It does not estimate uncertainty, model lens distortion, measure repeatability, validate a real gauge, or establish conformity for production.

## References

* [JCGM 106:2012, BIPM](https://www.bipm.org/en/doi/10.59161/jcgm106-2012), conformity decisions and uncertainty.
* [NIST, check standards](https://www.itl.nist.gov/div898/handbook/mpc/section1/mpc12.htm), detecting measurement changes.
* [Edmund Optics, advantages of telecentricity](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/advantages-of-telecentricity), how working distance affects optical magnification.
