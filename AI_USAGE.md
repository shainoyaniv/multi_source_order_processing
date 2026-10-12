# AI Usage

I used Claude throughout the assignment as a pair programmer: discussing
the design, generating code that I then reviewed and ran step by step,
writing tests and drafting documentation. I tested each part in a notebook
before moving on, and made the final decisions myself. Some examples:

## 1. Language choice
**Problem:** The assignment mentions Java, but I work mainly in Python.
**AI recommendation:** Stay with Java as specified, or confirm with the
company before switching.
**Decision:** Modified - I confirmed with the company that Python is
acceptable and used it.
**Why:** I'd rather submit a solution I can fully reason about and defend.

## 2. Representing money
**Problem:** How to store prices and calculate the total.
**AI recommendation:** Use `Decimal`, created via `str(value)`, and round
the total half-up to cents.
**Decision:** Accepted, after checking it myself - `0.1 * 3` in float gives
`0.30000000000000004`, and `Decimal(0.1)` without `str()` keeps the float
error. Added tests for both cases.
**Why:** An order value can't have floating-point errors.

## 3. Running the tests
**Problem:** pytest failed with `ModuleNotFoundError: No module named 'orders'`.
**AI recommendation:** Add a `pyproject.toml` with `pythonpath = ["."]`.
**Decision:** Rejected - used `python -m pytest` instead.
**Why:** It solves the same problem without an extra config file, which is
simpler for a project this size.

## 4. Unknown country codes
**Problem:** What to do with a country not in the reference table.
**AI recommendation:** Reject the record to a separate output with the
reason and original payload, and continue processing.
**Decision:** <accepted / modified - your reasoning>
**Why:** <...>

## How I validated
- Ran each module in a notebook against the sample files before moving on.
- Debugged issues myself along the way (invalid JSON in the sample file,
  records in the wrong source file, relative imports when running the CLI).
- Broke the rounding rule on purpose to confirm the tests catch it.