"""Offline camera width inspection using exact decimal fixture inputs."""
import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
from pathlib import Path
import sys


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):
        raise ValueError("expected a decimal number")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal number") from exc
    if not d.is_finite() or abs(d) > 1000000 or d.as_tuple().exponent < -6:
        raise ValueError("use finite numbers up to 1000000 with at most six decimals")
    return Fraction(d)


def positive(value):
    x = number(value)
    if x <= 0:
        raise ValueError("reference widths and pixel spans must be positive")
    return x


@dataclass(frozen=True)
class Calibration:
    lo_px: Fraction
    hi_px: Fraction
    scale: Fraction
    offset: Fraction

    @classmethod
    def fit(cls, rows):
        if not isinstance(rows, list) or len(rows) != 2:
            raise ValueError("exactly two calibration rows required")
        (p0, w0), (p1, w1) = sorted(
            (positive(r["span_px"]), positive(r["width_mm"])) for r in rows
        )
        if p0 >= p1 or w0 >= w1:
            raise ValueError("calibration needs distinct spans and increasing widths")
        scale = (w1 - w0) / (p1 - p0)
        return cls(p0, p1, scale, w0 - scale * p0)

    def width(self, span):
        return self.scale * span + self.offset

    def covers(self, span):
        return self.lo_px <= span <= self.hi_px


def classify(width, allowance, lower, upper):
    left, right = width - allowance, width + allowance
    if right < lower or left > upper:
        return "reject"
    if lower <= left and right <= upper:
        return "accept"
    return "review"


def fixed(x):
    # The display rounds after all decisions; Python's float is display only.
    return f"{float(x):.6f}"


def inspect(config):
    c = Calibration.fit(config["calibration"])
    lower, upper = [positive(x) for x in config["tolerance_mm"]]
    allowance = number(config["allowance_mm"])
    residual_limit = number(config["check_residual_limit_mm"])
    if lower >= upper or min(allowance, residual_limit) < 0:
        raise ValueError("tolerance must increase; allowance and check limit must be nonnegative")
    check = config["check"]
    span = positive(check["span_px"])
    reference = positive(check["width_mm"])
    if not c.lo_px < span < c.hi_px or not c.width(c.lo_px) < reference < c.width(c.hi_px):
        raise ValueError("check standard must be interior to the calibration range")
    residual = c.width(span) - reference
    check_ok = abs(residual) <= residual_limit
    parts = config["parts"]
    if not isinstance(parts, list) or not parts:
        raise ValueError("provide a nonempty parts list")
    results, ids = [], set()
    for row in parts:
        name = row["id"]
        if not isinstance(name, str) or not name.strip() or name in ids:
            raise ValueError("part IDs must be nonempty, unique strings")
        ids.add(name)
        span = positive(row["span_px"])
        width = c.width(span)
        if not check_ok:
            decision, reason = "hold", "check_failed"
        elif not c.covers(span):
            decision, reason = "hold", "outside_calibration"
        else:
            decision, reason = classify(width, allowance, lower, upper), "interval_rule"
        results.append({"id": name, "status": decision, "reason": reason,
                        "width_mm": None if decision == "hold" else fixed(width)})
    return {"scale_mm_per_px": fixed(c.scale), "offset_mm": fixed(c.offset),
            "check_residual_mm": fixed(residual), "check": "pass" if check_ok else "fail",
            "parts": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect(json.loads(args.fixture.read_text(encoding="utf-8"), parse_float=Decimal))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
