# AI Usage

I used Claude throughout the assignment as a pair programmer: discussing the
design, generating code that I reviewed and ran step by step, suggesting
test scenarios and drafting documentation. I tested each part before moving
on and made the final decisions myself.

## 1. Project design

**Problem:** How to structure the solution so both sources go through the
same business rules, and a new source can be added without touching them.

**AI recommendation:** Map each source into one internal `Order` model using
a small adapter function per source, keep all business rules in a separate
transform step that only sees `Order`, and write output through a simple
sink interface (`send(payload)`) so the file output can later be replaced by
a queue or API. It suggested plain functions in a dict registry rather than
an abstract base class per source.

**Decision:** Accepted.

**Why:** It keeps the source-specific code and the business rules apart:
adding a source is one function plus one registry line, and a rule change
happens in one place. For two sources, a class hierarchy would add
structure without adding safety. I also liked that the sink abstraction
let the tests run fully in memory.

## 2. Tests

**Problem:** Which scenarios to cover, and how to structure the tests.

**AI recommendation:** Use pytest with shared fixtures and parametrized
tests, and cover four areas: field mapping per source, the business rules
(country, currency, total), invalid input (missing fields, wrong types,
unknown country), and pipeline behaviour (bad records don't stop the run,
duplicates, end-to-end CLI run). To fix a `ModuleNotFoundError` when
running pytest, it suggested adding a `pyproject.toml` with
`pythonpath = ["."]`.

**Decision:** Accepted the test structure and scenarios; rejected the
`pyproject.toml` fix and used `python -m pytest` instead.

**Why:** The scenarios cover what actually breaks in production: bad data
and duplicates, not only the happy path. For the import issue, running
pytest as a module solves the same problem without adding a config file,
which is simpler for a project this size.

## 3. Representing money

**Problem:** How to store prices and calculate the total order value.

**AI recommendation:** Use `Decimal` instead of float, create it from
`str(value)`, round the total to cents with ROUND_HALF_UP, and convert to a
JSON number only when writing the output.

**Decision:** Accepted, after checking it myself.

**Why:** In the shell, `0.1 * 3` gives `0.30000000000000004`, and
`Decimal(0.1)` without `str()` still carries the float error. For an order
value that isn't acceptable. I added sample data and tests for this case
(3 x 0.10 = 0.30).
