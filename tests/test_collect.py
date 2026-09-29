"""Tests for metric collection."""

import logging
import unittest
from unittest import mock

from support import collector, exporter

SUMMARY = {
    "queries": {
        "types": {"A": 10, "AAAA": 5},
        "status": {"GRAVITY": 3, "FORWARDED": 12},
        "replies": {"IP": 13, "NXDOMAIN": 2},
        "total": 15,
        "blocked": 3,
        "unique_domains": 7,
        "forwarded": 12,
        "cached": 0,
    },
    "clients": {"active": 4, "total": 6},
    "gravity": {"domains_being_blocked": 12345},
}

UPSTREAMS = {"upstreams": [{"ip": "1.1.1.1", "name": "one.one.one.one", "port": 53, "count": 12}]}


def query(qtype="A", status="FORWARDED", reply="IP", name="laptop", ip="192.168.1.5", upstream="1.1.1.1#53"):
    return {
        "type": qtype,
        "status": status,
        "reply": {"type": reply},
        "client": {"name": name, "ip": ip},
        "upstream": upstream,
    }


QUERIES = {
    "queries": [
        query(),
        query(qtype="AAAA", name=None, ip="192.168.1.9"),
        query(status="GRAVITY", reply="BLOCKED", upstream=None),
        query(status="IN_PROGRESS", reply="UNKNOWN", upstream=None),
    ]
}


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


def fake_api(summary=SUMMARY, upstreams=UPSTREAMS, queries=QUERIES):
    responses = {"stats/summary": summary, "stats/upstreams": upstreams}

    def call(path):
        if path.startswith("queries?"):
            return queries
        return responses[path]

    return call


def scrape(c):
    return {m.name: {tuple(s.labels.values()): s.value for s in m.samples} for m in c.collect()}


# A fixed clock so the 1-minute window and sample timestamps are predictable.
NOW = 1_700_000_123


@mock.patch.object(exporter.time, "time", return_value=NOW)
class CollectTest(unittest.TestCase):
    def test_summary_metrics(self, _time):
        c = collector()
        c.get_api_call = fake_api()
        metrics = scrape(c)
        self.assertEqual(metrics["pihole_query_by_type"], {("A",): 10, ("AAAA",): 5})
        self.assertEqual(metrics["pihole_query_by_status"], {("GRAVITY",): 3, ("FORWARDED",): 12})
        self.assertEqual(metrics["pihole_query_replies"], {("IP",): 13, ("NXDOMAIN",): 2})
        self.assertEqual(
            metrics["pihole_query_count"],
            {("total",): 15, ("blocked",): 3, ("unique",): 7, ("forwarded",): 12, ("cached",): 0},
        )
        self.assertEqual(metrics["pihole_client_count"], {("active",): 4, ("total",): 6})
        self.assertEqual(metrics["pihole_domains_being_blocked"], {(): 12345})
        self.assertEqual(metrics["pihole_query_upstream_count"], {("1.1.1.1", "one.one.one.one", "53"): 12})

    def test_per_minute_query_metrics(self, _time):
        c = collector()
        c.get_api_call = fake_api()
        metrics = scrape(c)
        self.assertEqual(metrics["pihole_query_type_1m"], {("A",): 3, ("AAAA",): 1})
        self.assertEqual(metrics["pihole_query_status_1m"], {("FORWARDED",): 2, ("GRAVITY",): 1, ("IN_PROGRESS",): 1})
        self.assertEqual(metrics["pihole_query_reply_1m"], {("IP",): 2, ("BLOCKED",): 1, ("UNKNOWN",): 1})
        self.assertEqual(metrics["pihole_query_client_1m"], {("laptop (192.168.1.5)",): 3, ("192.168.1.9",): 1})
        self.assertEqual(
            metrics["pihole_query_upstream_1m"], {("1.1.1.1#53",): 2, ("None-GRAVITY",): 1, ("None-OTHER",): 1}
        )

    def test_queries_window_is_the_last_whole_minute(self, _time):
        c = collector()
        paths = []
        api = fake_api()

        def record(path):
            paths.append(path)
            return api(path)

        c.get_api_call = record
        list(c.collect())
        last_min = NOW // 60 * 60
        self.assertIn(f"queries?from={last_min - 60}&until={last_min}&length=1000000", paths)

    def test_per_minute_samples_are_timestamped(self, _time):
        c = collector()
        c.get_api_call = fake_api()
        q_type = next(m for m in c.collect() if m.name == "pihole_query_type_1m")
        self.assertEqual({s.timestamp for s in q_type.samples}, {NOW // 60 * 60})

    def test_counts_reset_between_scrapes(self, _time):
        c = collector()
        c.get_api_call = fake_api()
        scrape(c)
        c.get_api_call = fake_api(queries={"queries": [query(qtype="MX")]})
        metrics = scrape(c)
        # Types seen last minute report 0 once, so the series drops to zero instead of going stale.
        self.assertEqual(metrics["pihole_query_type_1m"], {("A",): 0, ("AAAA",): 0, ("MX",): 1})
        c.get_api_call = fake_api(queries={"queries": []})
        metrics = scrape(c)
        # A type that already reported 0 is dropped.
        self.assertEqual(metrics["pihole_query_type_1m"], {("MX",): 0})

    def test_api_error_on_summary_yields_nothing(self, _time):
        c = collector()
        c.get_api_call = fake_api(summary={"error": {"key": "unauthorized"}})
        self.assertEqual(list(c.collect()), [])

    def test_missing_queries_on_summary_yields_nothing(self, _time):
        c = collector()
        c.get_api_call = fake_api(summary={"clients": {}})
        self.assertEqual(list(c.collect()), [])

    def test_missing_upstreams_skips_that_metric(self, _time):
        c = collector()
        c.get_api_call = fake_api(upstreams={})
        self.assertNotIn("pihole_query_upstream_count", scrape(c))

    def test_query_details_error_stops_after_summary_metrics(self, _time):
        c = collector()
        c.get_api_call = fake_api(queries={"error": {"key": "bad_request"}})
        metrics = scrape(c)
        self.assertIn("pihole_query_by_type", metrics)
        self.assertNotIn("pihole_query_type_1m", metrics)

    def test_exception_during_scrape_is_logged_not_raised(self, _time):
        c = collector()
        c.get_api_call = mock.Mock(side_effect=Exception("connection refused"))
        with mock.patch.object(exporter.logging, "error") as log_error:
            self.assertEqual(list(c.collect()), [])
        log_error.assert_called_once_with("Error during scrape: connection refused")


class ClearCountsTest(unittest.TestCase):
    def test_nonzero_counts_reset_and_zero_counts_removed(self):
        c = collector()
        for counts in (c.type_cnt, c.status_cnt, c.reply_cnt, c.client_cnt, c.upstream_cnt):
            counts.update({"seen": 4, "idle": 0})
        c.clear_cnts()
        for counts in (c.type_cnt, c.status_cnt, c.reply_cnt, c.client_cnt, c.upstream_cnt):
            self.assertEqual(counts, {"seen": 0})


if __name__ == "__main__":
    unittest.main()
