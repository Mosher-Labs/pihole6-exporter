"""Tests for argument parsing, startup, and shutdown."""

import logging
import os
import unittest
from unittest import mock

from support import exporter


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


class ParseArgsTest(unittest.TestCase):
    @mock.patch.dict(os.environ, {}, clear=True)
    def test_defaults(self):
        args = exporter.parse_args([])
        self.assertEqual(
            (args.host, args.port, args.pihole_port, args.protocol, args.key, args.timeout),
            ("localhost", 9617, 80, "http", None, exporter.DEFAULT_TIMEOUT),
        )

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_flags(self):
        args = exporter.parse_args(
            [
                "-H",
                "pihole",
                "-p",
                "9000",
                "--pihole-port",
                "8080",
                "--protocol",
                "https",
                "-k",
                "cli-key",
                "--timeout",
                "2.5",
            ]
        )
        self.assertEqual(
            (args.host, args.port, args.pihole_port, args.protocol, args.key, args.timeout),
            ("pihole", 9000, 8080, "https", "cli-key", 2.5),
        )

    @mock.patch.dict(os.environ, {"PIHOLE_API_TOKEN": "env-key"}, clear=True)
    def test_key_falls_back_to_environment(self):
        self.assertEqual(exporter.parse_args([]).key, "env-key")

    @mock.patch.dict(os.environ, {"PIHOLE_API_TOKEN": "env-key"}, clear=True)
    def test_cli_key_wins_over_environment(self):
        self.assertEqual(exporter.parse_args(["-k", "cli-key"]).key, "cli-key")


class StopLoop(Exception):
    pass


@mock.patch.dict(os.environ, {}, clear=True)
@mock.patch.object(exporter.signal, "signal")
@mock.patch.object(exporter.time, "sleep", side_effect=StopLoop)
@mock.patch.object(exporter.REGISTRY, "register")
@mock.patch.object(exporter, "PiholeCollector")
@mock.patch.object(exporter, "start_http_server")
class MainTest(unittest.TestCase):
    def test_starts_server_and_registers_collector(self, start_http_server, collector_cls, register, _sleep, signal_fn):
        with self.assertRaises(StopLoop):
            exporter.main(["-H", "pihole", "-p", "9000", "-k", "secret", "--timeout", "3"])
        start_http_server.assert_called_once_with(9000)
        collector_cls.assert_called_once_with("pihole", 80, "http", "secret", 3.0)
        register.assert_called_once_with(collector_cls.return_value)
        self.assertIs(exporter._collector, collector_cls.return_value)
        handled = {c.args[0] for c in signal_fn.call_args_list}
        self.assertEqual(handled, {exporter.signal.SIGTERM, exporter.signal.SIGINT})


class ShutdownHandlerTest(unittest.TestCase):
    def test_deletes_session_and_exits(self):
        c = mock.Mock()
        with mock.patch.object(exporter, "_collector", c), self.assertRaises(SystemExit) as exit_:
            exporter.shutdown_handler(15, None)
        c.delete_session.assert_called_once()
        self.assertEqual(exit_.exception.code, 0)

    def test_exits_when_no_collector_yet(self):
        with mock.patch.object(exporter, "_collector", None), self.assertRaises(SystemExit):
            exporter.shutdown_handler(15, None)


if __name__ == "__main__":
    unittest.main()
