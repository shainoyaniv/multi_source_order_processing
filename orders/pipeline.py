"""Glue: read records -> adapt -> transform -> deliver.

Each record is processed independently. A bad record goes to the rejected
sink with the reason and the original payload, and processing continues.
"""
import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal

from .adapters import get_adapter
from .models import InvalidOrder
from .transform import to_target

log = logging.getLogger(__name__)


def _json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"not JSON serializable: {type(obj).__name__}")


def to_json(payload):
    return json.dumps(payload, default=_json_default, ensure_ascii=False)


class JsonLinesSink:
    """Writes one JSON object per line. Stands in for the real target system."""

    def __init__(self, path):
        self.path = path
        self._fh = open(path, "w", encoding="utf-8")

    def send(self, payload):
        self._fh.write(to_json(payload) + "\n")

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class ListSink:
    """In-memory sink, used by tests."""

    def __init__(self):
        self.items = []

    def send(self, payload):
        self.items.append(payload)


@dataclass
class Stats:
    delivered: int = 0
    rejected: int = 0
    duplicates: int = 0
    by_source: dict = field(default_factory=dict)


class OrderProcessor:
    def __init__(self, target, rejected):
        self.target = target
        self.rejected = rejected
        self.stats = Stats()
        # (source, order_id) pairs already delivered in this run.
        # In production this would be a persistent store - see DESIGN.md.
        self._seen = set()

    def process(self, source, record):
        adapter = get_adapter(source)
        try:
            if not isinstance(record, dict):
                raise InvalidOrder("record is not a JSON object")
            order = adapter(record)
            key = (order.source, order.order_id)
            if key in self._seen:
                self.stats.duplicates += 1
                log.info("skipping duplicate order %s from source %s", order.order_id, source)
                return
            payload = to_target(order)
        except InvalidOrder as e:
            self.stats.rejected += 1
            self.rejected.send({"source": source, "reason": str(e), "record": record})
            log.warning("rejected record from source %s: %s", source, e)
            return

        self.target.send(payload)
        self._seen.add(key)
        self.stats.delivered += 1
        self.stats.by_source[source] = self.stats.by_source.get(source, 0) + 1


def read_records(path):
    """Yield records from a .jsonl file (one per line) or a .json array.

    JSONL is streamed line by line. A line that isn't valid JSON is yielded
    as a raw string and gets rejected downstream instead of crashing the run.
    """
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        yield from (data if isinstance(data, list) else [data])
        return

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                yield line