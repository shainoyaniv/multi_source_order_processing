# Design

## Architecture

The core idea is one internal `Order` model between the sources and the target:

```
Source A JSON --> parse_source_a --\
                                    >-- Order --> to_target --> target sink
Source B JSON --> parse_source_b --/                 |
                                                     \--> (on error) rejected sink
```

- **Adapters** (`adapters.py`) - one function per source. Each knows only its
  own JSON structure and maps it to `Order`. Field validation helpers are
  shared, so both sources are validated by the same rules.
- **Order** (`models.py`) - a source-independent, immutable dataclass.
- **Transform** (`transform.py`) - all business rules: country lookup,
  currency, total value. It only reads `Order`, so it doesn't know or care
  which source the order came from.
- **Pipeline** (`pipeline.py`) - runs each record through
  adapter -> transform -> sink, handles errors and duplicates, collects stats.
- **Sinks** - anything with a `send(payload)` method. The CLI writes JSON
  Lines files as a stand-in for the target system; tests use an in-memory list.

Why this split: adding a source means writing one adapter function and
registering it. Changing a business rule means changing one place, and it
applies to all sources.

## How an order is processed

1. The CLI reads a source file record by record (JSONL is streamed).
2. `OrderProcessor.process(source, record)` picks the adapter for that source.
3. The adapter validates required fields and builds an `Order`
   (names normalized, country code upper-cased, price as `Decimal`,
   timestamp parsed to `datetime`).
4. If `(source, order_id)` was already delivered in this run, it's skipped.
5. `to_target` looks up the country name and currency, computes the total,
   and builds the target JSON.
6. The payload is sent to the target sink. Any `InvalidOrder` along the way
   sends `{source, reason, record}` to the rejected sink instead, and
   processing continues with the next record.

## Key technical decisions

**Python.** The assignment mentions Java; I confirmed with the company that
Python is acceptable and used it since it's the language I work with daily.

**Decimal for money, not float.** In float, `3 * 0.1 = 0.30000000000000004`.
Prices are parsed with `Decimal(str(value))` and the total is rounded to
cents with ROUND_HALF_UP. Conversion to a JSON number happens only when
writing the output.

**Reject per record, never fail the batch.** At ~50k orders/day, one bad
record must not block the rest. Rejected records keep the original payload
and a readable reason, so they can be fixed and replayed.

**Unknown country -> reject.** The country determines the currency. Sending
an order with a guessed or missing currency is worse than holding it back.

**Duplicates keyed on `(source, order_id)`.** The two systems number orders
independently, so the same id in A and B is two different orders. An order
is marked as seen only after it was delivered, so a corrected resend of a
rejected order still goes through.

**Strict types, no silent conversion.** A quantity of `"2"` (string) or
`true` is rejected rather than converted. If a source starts sending the
wrong types, I'd rather find out than guess.

**Plain functions + a dict registry for adapters**, instead of an abstract
base class per source. For two sources a class hierarchy adds ceremony
without adding safety. Easy to switch if adapters need state later.

**Standard library only** for the application; pytest for tests. For this
size, a framework or pydantic would add more setup than value.

**File-based CLI as the entry point.** The assignment doesn't specify how
orders arrive, so files were the simplest way to demonstrate it. The
processor handles one record at a time and knows nothing about files, so it
can sit behind a queue consumer or an HTTP endpoint without changes.

## Alternatives considered

- **Config-driven mapping** (YAML of field paths per source). Useful with
  many similar sources, but name joining and type checks end up as special
  cases in the config. For two sources, code is clearer and easier to test.
- **Mapping each source directly to the target** without an internal model.
  Less code now, but every new source would re-implement the business rules.
- **pandas.** Good for bulk processing, but per-record error handling and
  nested JSON are awkward, and 50k/day doesn't need it.
- **Validation in `Order.__post_init__`** instead of the adapters. I kept it
  in the adapters so error messages use the source's field names
  (e.g. `item.units` rather than `quantity`).

## Assumptions

- Each input is labelled with its source (here: by file). Records are not
  auto-detected by structure.
- All fields in the examples are required, except `last_name` in source B.
  Without it, the full name is just the first name.
- Customer names: surrounding and repeated whitespace is removed; casing is
  kept as-is.
- Country codes are case-insensitive (`de` = `DE`).
- `quantity` must be a positive integer. `unitPrice` must be >= 0
  (0 allowed, e.g. a free item).
- Timestamps are ISO-8601 without timezone, passed through as-is. I assumed
  both sources use the same timezone.
- `totalOrderValue` is rounded to 2 decimals, half up. The assignment shows
  `251.00`; JSON numbers don't keep trailing zeros, so the output is `251.0`,
  the same value.
- Prices are already in the currency of the customer's country.
- Each order has exactly one item, as in both examples.

## Production concerns not implemented

- **Ingestion:** a queue/topic per source (e.g. Kafka, SQS) with a consumer
  running the same processor. This absorbs uneven load between the sources
  and peaks during the day.
- **Delivery:** a real target client with retries and exponential backoff.
  Acknowledge the source message only after the target confirmed. Orders
  that keep failing go to a dead-letter queue.
- **Idempotency:** duplicate detection is in-memory for one run. In
  production: a persistent store (DB unique constraint or Redis) on
  `(source, order_id)`, plus an idempotency key towards the target, since
  at-least-once delivery means duplicates will happen.
- **Reference data:** countries from a DB or config service, cached, so
  adding a country doesn't need a deploy.
- **Observability:** metrics per source (received / delivered / rejected /
  latency), alerts on rejection-rate spikes or on a source going silent,
  structured logs with the order id.
- **Replay tooling** for rejected records after they're fixed.
- **PII:** customer names are personal data - limit what's logged and how
  long rejected payloads are kept.

## Questions before a production version

1. What currency are source prices in? If a source always sends USD, the
   total needs a conversion, not just a currency label.
2. What should happen to an order with an unknown country - reject, manual
   review, or deliver without currency?
3. Can orders be updated or cancelled after delivery? Then a "duplicate"
   may really be a new version.
4. How do the sources deliver - push/pull, files, API, queue? Any ordering
   guarantees?
5. What does the target accept - single orders or batches, which protocol,
   rate limits? Is it idempotent?
6. Which timezone are the timestamps in? Does the target expect UTC?
7. Can an order have more than one item?
8. Which rounding rule does the target expect, and should amounts be sent
   as strings to keep exactly 2 decimals?
9. Latency requirements - near real-time or periodic batches?
10. Who handles rejected orders, and how do they get fixed?

## Evolving the solution

- **More sources:** one adapter function + one registry line each. With
  dozens of mostly-flat sources, a config-driven mapping starts to pay off,
  keeping code adapters only for the unusual ones.
- **More volume:** 50k/day is under one order per second on average, so one
  process is enough. For much more: partition the queue by order id and run
  more consumers. The processor is stateless apart from duplicate
  detection, which moves to the shared store anyway.
- **More rules:** keep them as small functions in `transform.py`. If they
  start varying by country or customer, move to a list of rule objects
  applied in order, each tested separately.
- **Multi-item orders:** `Order` gets a list of lines and the total becomes a
  sum. The target format would need to change too.