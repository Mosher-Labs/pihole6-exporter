"""Unit tests for Pi-hole authentication handling in pihole6_exporter."""

import importlib.machinery
import importlib.util
import logging
import pathlib
import unittest
from unittest import mock

# The exporter is a script without a .py extension, so load it by path.
_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "pihole6_exporter"
_loader = importlib.machinery.SourceFileLoader("pihole6_exporter", str(_SCRIPT))
_spec = importlib.util.spec_from_loader("pihole6_exporter", _loader)
exporter = importlib.util.module_from_spec(_spec)
_loader.exec_module(exporter)


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


def _response(status_code, body):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = body
    return resp


def _collector():
    # Skip __init__ so no network call happens on construction.
    c = object.__new__(exporter.PiholeCollector)
    c.protocol = "http"
    c.host = "pihole.test"
    c.pihole_port = 80
    c.using_auth = True
    c.password = "secret"
    c.sid = "old-sid"
    c.csrf = "old-csrf"
    return c


@mock.patch.object(exporter.time, "sleep")
@mock.patch.object(exporter.requests, "post")
class GetSidTest(unittest.TestCase):

    def test_success_returns_sid_and_csrf(self, post, _sleep):
        post.return_value = _response(200, {"session": {"valid": True, "sid": "s", "csrf": "c"}})
        self.assertEqual(_collector().get_sid("secret"), {"sid": "s", "csrf": "c"})

    def test_wrong_password_without_error_key_raises(self, post, _sleep):
        post.return_value = _response(
            401, {"session": {"valid": False, "sid": None, "message": "password incorrect"}})
        with self.assertRaisesRegex(Exception, "Authentication failed: password incorrect"):
            _collector().get_sid("wrong")

    def test_valid_session_without_csrf_raises(self, post, _sleep):
        # Pi-hole with no password configured returns a valid session with no csrf.
        post.return_value = _response(
            200, {"session": {"valid": True, "sid": None, "message": "no password set"}})
        with self.assertRaisesRegex(Exception, "Authentication failed: no password set"):
            _collector().get_sid("secret")

    def test_non_200_status_raises(self, post, _sleep):
        post.return_value = _response(500, {"session": {"valid": True, "sid": "s", "csrf": "c"}})
        with self.assertRaises(Exception):
            _collector().get_sid("secret")

    def test_missing_session_raises_with_response_in_message(self, post, _sleep):
        post.return_value = _response(200, {"unexpected": 1})
        with self.assertRaisesRegex(Exception, "unexpected response"):
            _collector().get_sid("secret")

    def test_error_key_raises_error_message(self, post, _sleep):
        post.return_value = _response(400, {"error": {"key": "bad_request", "message": "nope"}})
        with self.assertRaisesRegex(Exception, "Authentication failed: nope"):
            _collector().get_sid("secret")

    def test_api_seats_exceeded_retries_then_succeeds(self, post, sleep):
        seats = _response(429, {"error": {"key": "api_seats_exceeded", "message": "full"}})
        ok = _response(200, {"session": {"valid": True, "sid": "s", "csrf": "c"}})
        post.side_effect = [seats, seats, ok]
        self.assertEqual(_collector().get_sid("secret", initial_backoff=10), {"sid": "s", "csrf": "c"})
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [10, 20])

    def test_api_seats_exceeded_gives_up_after_max_retries(self, post, sleep):
        post.return_value = _response(429, {"error": {"key": "api_seats_exceeded", "message": "full"}})
        with self.assertRaisesRegex(Exception, "max retries exceeded"):
            _collector().get_sid("secret", max_retries=3)
        self.assertEqual(post.call_count, 3)

    def test_backoff_is_capped_at_300_seconds(self, post, sleep):
        post.return_value = _response(429, {"error": {"key": "api_seats_exceeded", "message": "full"}})
        with self.assertRaises(Exception):
            _collector().get_sid("secret", max_retries=6, initial_backoff=100)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [100, 200, 300, 300, 300, 300])


@mock.patch.object(exporter.requests, "get")
class GetApiCallTest(unittest.TestCase):

    def test_sends_session_headers(self, get):
        get.return_value = _response(200, {"ok": True})
        self.assertEqual(_collector().get_api_call("stats/summary"), {"ok": True})
        headers = get.call_args.kwargs["headers"]
        self.assertEqual(headers["X-FTL-SID"], "old-sid")
        self.assertEqual(headers["X-FTL-CSRF"], "old-csrf")

    def test_unauthorized_reauthenticates_and_retries_once(self, get):
        unauthorized = _response(401, {"error": {"key": "unauthorized", "message": "expired"}})
        get.side_effect = [unauthorized, _response(200, {"ok": True})]
        c = _collector()
        with mock.patch.object(c, "get_sid", return_value={"sid": "new-sid", "csrf": "new-csrf"}) as get_sid:
            self.assertEqual(c.get_api_call("stats/summary"), {"ok": True})
        get_sid.assert_called_once_with("secret")
        self.assertEqual((c.sid, c.csrf), ("new-sid", "new-csrf"))
        self.assertEqual(get.call_args.kwargs["headers"]["X-FTL-SID"], "new-sid")

    def test_unauthorized_twice_returns_error_without_looping(self, get):
        get.return_value = _response(401, {"error": {"key": "unauthorized", "message": "expired"}})
        c = _collector()
        with mock.patch.object(c, "get_sid", return_value={"sid": "s", "csrf": "c"}):
            reply = c.get_api_call("stats/summary")
        self.assertEqual(reply["error"]["key"], "unauthorized")
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
