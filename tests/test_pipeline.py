import json

from orders.__main__ import main
from orders.pipeline import ListSink, OrderProcessor, read_records


def make_processor():
    target, rejected = ListSink(), ListSink()
    return OrderProcessor(target, rejected), target, rejected


def test_both_sources_produce_the_same_shape(rec_a, rec_b):
    processor, target, _ = make_processor()
    processor.process("A", rec_a)
    processor.process("B", rec_b)
    a, b = target.items
    assert a.keys() == b.keys()
    assert a["customer"].keys() == b["customer"].keys()
    assert a["product"].keys() == b["product"].keys()


def test_bad_record_does_not_stop_processing(rec_a):
    processor, target, rejected = make_processor()
    processor.process("A", {**rec_a, "country": "XX"})
    processor.process("A", rec_a)

    assert len(target.items) == 1
    assert len(rejected.items) == 1
    rej = rejected.items[0]
    assert rej["source"] == "A"
    assert "XX" in rej["reason"]
    assert rej["record"]["country"] == "XX"  # original payload kept for replay


def test_non_object_records_are_rejected():
    processor, _, rejected = make_processor()
    processor.process("B", "not json")
    processor.process("B", [1, 2])
    assert len(rejected.items) == 2


def test_duplicate_is_delivered_once(rec_a):
    processor, target, _ = make_processor()
    processor.process("A", rec_a)
    processor.process("A", rec_a)
    assert len(target.items) == 1
    assert processor.stats.duplicates == 1


def test_same_id_in_different_sources_is_not_a_duplicate(rec_a, rec_b):
    processor, target, _ = make_processor()
    rec_b["order_number"] = rec_a["orderId"]
    processor.process("A", rec_a)
    processor.process("B", rec_b)
    assert len(target.items) == 2


def test_rejected_order_can_be_resent_after_fix(rec_a):
    # a rejected record must not be marked as seen, otherwise
    # the corrected resend would be dropped as a duplicate
    processor, target, _ = make_processor()
    processor.process("A", {**rec_a, "quantity": 0})
    processor.process("A", rec_a)
    assert len(target.items) == 1


def test_read_records_skips_blank_lines_and_keeps_bad_ones(tmp_path):
    path = tmp_path / "in.jsonl"
    path.write_text('{"a": 1}\n\n   \n{broken\n{"a": 2}\n')
    assert list(read_records(str(path))) == [{"a": 1}, "{broken", {"a": 2}]


def test_cli_end_to_end(tmp_path, rec_a, rec_b):
    a_file = tmp_path / "a.jsonl"
    a_file.write_text(json.dumps(rec_a) + "\n" + "garbage line\n")
    b_file = tmp_path / "b.json"
    b_file.write_text(json.dumps([rec_b]))
    out_dir = tmp_path / "out"

    main(["--input", f"A={a_file}", "--input", f"B={b_file}", "--out-dir", str(out_dir)])

    delivered = [json.loads(l) for l in (out_dir / "target_orders.jsonl").read_text().splitlines()]
    rejected = [json.loads(l) for l in (out_dir / "rejected_orders.jsonl").read_text().splitlines()]

    assert [o["orderReference"] for o in delivered] == ["ORD-10001", "ORD-20001"]
    assert delivered[0]["totalOrderValue"] == 251.0
    assert delivered[1]["customer"]["fullName"] == "Jane Miller"
    assert delivered[1]["currency"] == "EUR"
    assert len(rejected) == 1