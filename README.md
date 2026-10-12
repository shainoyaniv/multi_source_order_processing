# Multi-Source Order Processing

Reads orders from two source systems (A and B), each with its own JSON
structure, applies the business rules (full customer name, country name,
currency, total order value) and delivers them in the target system format.

Design decisions, assumptions and open questions are in [DESIGN.md](DESIGN.md).

## Requirements

- Python 3.10+
- `pytest` for running the tests (`pip install pytest`)

The application itself uses only the standard library.

## Build

There's nothing to compile or install. Clone the repo and run the commands
below from the project root.

## Run

```bash
python -m orders --input A=samples/source_a.jsonl --input B=samples/source_b.jsonl --out-dir output
```

| Option | Description |
|---|---|
| `--input SOURCE=PATH` | Input file for a source. Repeatable, in any order. Accepts JSON Lines (`.jsonl`, one order per line) or a JSON array (`.json`). |
| `--out-dir` | Output directory (default: `output/`) |
| `-v` | Log every rejected / duplicate record |

Note: run it as a module (`python -m orders`), not as a script
(`python orders/__main__.py`) - the package uses relative imports.

Example output:

```
delivered: 5 {'A': 2, 'B': 3}
rejected:  4
duplicates skipped: 1
output:   output/target_orders.jsonl
rejected: output/rejected_orders.jsonl
```

## Demo data

`samples/` contains orders from both sources, including the two examples
from the assignment, plus edge cases added on purpose:

| Record | Source | Expected result |
|---|---|---|
| ORD-10001 | A | delivered (matches the target example in the assignment) |
| ORD-10002 | A | delivered (GB -> United Kingdom, GBP) |
| ORD-10003 | A | rejected - unknown country FR |
| ORD-10001 (again) | A | skipped as duplicate |
| ORD-10004 | A | rejected - quantity 0 |
| ORD-20001 | B | delivered (matches the B example in the assignment) |
| ORD-20002 | B | delivered - 3 x 0.10 = 0.30 exactly, no float error |
| ORD-20003 | B | delivered - no last name, lowercase country code "de" |
| ORD-20004 | B | rejected - invalid timestamp |
| non-JSON line | B | rejected - not a JSON object |

## Verify the output

```bash
cat output/target_orders.jsonl      # orders delivered to the target system
cat output/rejected_orders.jsonl    # rejected records: source, reason, original payload

# pretty-print the first delivered order
head -1 output/target_orders.jsonl | python -m json.tool
```

The first delivered order should match the target example from the
assignment: ORD-10001, John Smith, United States, total 251.0, USD.

## Tests

```bash
python -m pytest -v
```

## Project structure

```
orders/
  models.py      Order dataclass (internal model) and InvalidOrder exception
  reference.py   country code -> name / currency
  adapters.py    source A / source B -> Order, with field validation
  transform.py   business rules: Order -> target JSON
  pipeline.py    processing loop, duplicate check, sinks, input reading
  __main__.py    command line interface
tests/
samples/
```