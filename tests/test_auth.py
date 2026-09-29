"""Tests for Pi-hole authentication, session re-authentication, and logout."""

import logging
import unittest
from unittest import mock

from support import collector, exporter, non_json_response, response


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


SEATS_EXCEEDED = {"error": {"key": "api_seats_exceeded", "message": "full"}}


@mock.patch.object(exporter.time, "sleep")
@mock.patch.object(exporter.requests, "post")
class GetSidTest(unittest.TestCase):
    def test_success_returns_sid_and_csrf(self, post, _sleep):
        post.return_value = response(200, {"session": {"valid": True, "sid": "s", "csrf": "c"}})
        self.assertEqual(collector().get_sid("secret"), {"sid": "s", "csrf": "c"})

    def test_posts_password_with_timeout(self, post, _sleep):
        post.return_value = response(200, {"session": {"valid": True, "sid": "s", "csrf": "c"}})
        c = collector()
        c.timeout = 3
        c.get_sid("secret")
        self.assertEqual(post.call_args.args[0], "http://pihole.test:80/api/auth")
        self.assertEqual(post.call_args.kwargs["json"], {"password": "secret"})
        self.assertEqual(post.call_args.kwargs["timeout"], 3)

    def test_wrong_password_without_error_key_raises(self, post, _sleep):
        post.return_value = response(401, {"session": {"valid": False, "sid": None, "message": "password incorrect"}})
        with self.assertRaisesRegex(Exception, "Authentication failed: password incorrect"):
            collector().get_sid("wrong")

    def test_no_password_set_returns_none(self, post, _sleep):
        post.return_value = response(
            200, {"session": {"valid": True, "sid": None, "validity": -1, "message": "no password set"}}
        )
        self.assertIsNone(collector().get_sid("secret"))

    def test_valid_session_without_csrf_raises(self, post, _sleep):
        post.return_value = response(200, {"session": {"valid": True, "sid": "s"}})
        with self.assertRaisesRegex(Exception, "Authentication failed"):
            collector().get_sid("secret")

    def test_non_200_status_raises(self, post, _sleep):
        post.return_value = response(500, {"session": {"valid": True, "sid": "s", "csrf": "c"}})
        with self.assertRaisesRegex(Exception, "Authentication failed: unexpected response"):
            collector().get_sid("secret")

    def test_missing_session_raises_with_response_in_message(self, post, _sleep):
        post.return_value = response(200, {"unexpected": 1})
        with self.assertRaisesRegex(Exception, "unexpected response"):
            collector().get_sid("secret")

    def test_error_key_raises_error_message(self, post, _sleep):
        post.return_value = response(400, {"error": {"key": "bad_request", "message": "nope"}})
        with self.assertRaisesRegex(Exception, "Authentication failed: nope"):
            collector().get_sid("secret")

    def test_error_without_message_raises_error_key(self, post, _sleep):
        post.return_value = response(400, {"error": {"key": "bad_request"}})
        with self.assertRaisesRegex(Exception, "Authentication failed: bad_request"):
            collector().get_sid("secret")

    def test_error_that_is_a_string_raises_it(self, post, _sleep):
        post.return_value = response(400, {"error": "boom"})
        with self.assertRaisesRegex(Exception, "Authentication failed: boom"):
            collector().get_sid("secret")

    def test_non_json_response_raises_readable_error(self, post, _sleep):
        post.return_value = non_json_response(502, "<html>Bad Gateway</html>")
        with self.assertRaisesRegex(Exception, r"non-JSON response \(status 502\): <html>Bad Gateway"):
            collector().get_sid("secret")

    def test_api_seats_exceeded_retries_then_succeeds(self, post, sleep):
        ok = response(200, {"session": {"valid": True, "sid": "s", "csrf": "c"}})
        post.side_effect = [response(429, SEATS_EXCEEDED), response(429, SEATS_EXCEEDED), ok]
        self.assertEqual(collector().get_sid("secret", initial_backoff=10), {"sid": "s", "csrf": "c"})
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [10, 20])

    def test_api_seats_exceeded_gives_up_after_max_retries(self, post, _sleep):
        post.return_value = response(429, SEATS_EXCEEDED)
        with self.assertRaisesRegex(Exception, "max retries exceeded"):
            collector().get_sid("secret", max_retries=3)
        self.assertEqual(post.call_count, 3)

    def test_backoff_is_capped_at_300_seconds(self, post, sleep):
        post.return_value = response(429, SEATS_EXCEEDED)
        with self.assertRaisesRegex(Exception, "max retries exceeded"):
            collector().get_sid("secret", max_retries=6, initial_backoff=100)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [100, 200, 300, 300, 300, 300])


@mock.patch.object(exporter.requests, "get")
class GetApiCallTest(unittest.TestCase):
    def test_sends_session_headers_and_timeout(self, get):
        get.return_value = response(200, {"ok": True})
        self.assertEqual(collector().get_api_call("stats/summary"), {"ok": True})
        self.assertEqual(get.call_args.args[0], "http://pihole.test:80/api/stats/summary")
        headers = get.call_args.kwargs["headers"]
        self.assertEqual(headers["X-FTL-SID"], "old-sid")
        self.assertEqual(headers["X-FTL-CSRF"], "old-csrf")
        self.assertEqual(get.call_args.kwargs["timeout"], exporter.DEFAULT_TIMEOUT)

    def test_no_session_headers_without_auth(self, get):
        get.return_value = response(200, {"ok": True})
        collector(using_auth=False).get_api_call("stats/summary")
        self.assertNotIn("X-FTL-SID", get.call_args.kwargs["headers"])

    def test_unauthorized_reauthenticates_and_retries_once(self, get):
        unauthorized = response(401, {"error": {"key": "unauthorized", "message": "expired"}})
        get.side_effect = [unauthorized, response(200, {"ok": True})]
        c = collector()
        with mock.patch.object(c, "get_sid", return_value={"sid": "new-sid", "csrf": "new-csrf"}) as get_sid:
            self.assertEqual(c.get_api_call("stats/summary"), {"ok": True})
        get_sid.assert_called_once_with("secret")
        self.assertEqual((c.sid, c.csrf), ("new-sid", "new-csrf"))
        self.assertEqual(get.call_args.kwargs["headers"]["X-FTL-SID"], "new-sid")

    def test_unauthorized_twice_returns_error_without_looping(self, get):
        get.return_value = response(401, {"error": {"key": "unauthorized", "message": "expired"}})
        c = collector()
        with mock.patch.object(c, "get_sid", return_value={"sid": "s", "csrf": "c"}):
            reply = c.get_api_call("stats/summary")
        self.assertEqual(reply["error"]["key"], "unauthorized")
        self.assertEqual(get.call_count, 2)

    def test_reauth_to_passwordless_pihole_drops_session_headers(self, get):
        unauthorized = response(401, {"error": {"key": "unauthorized", "message": "expired"}})
        get.side_effect = [unauthorized, response(200, {"ok": True})]
        c = collector()
        with mock.patch.object(c, "get_sid", return_value=None):
            self.assertEqual(c.get_api_call("stats/summary"), {"ok": True})
        self.assertFalse(c.using_auth)
        self.assertNotIn("X-FTL-SID", get.call_args.kwargs["headers"])

    def test_error_without_key_is_returned_not_raised(self, get):
        get.return_value = response(400, {"error": {"message": "bad"}})
        self.assertEqual(collector().get_api_call("stats/summary"), {"error": {"message": "bad"}})

    def test_non_json_response_raises_readable_error(self, get):
        get.return_value = non_json_response(502, "Bad Gateway")
        with self.assertRaisesRegex(Exception, "non-JSON response"):
            collector().get_api_call("stats/summary")


@mock.patch.object(exporter.requests, "delete")
class DeleteSessionTest(unittest.TestCase):
    def test_deletes_session_with_headers(self, delete):
        delete.return_value = response(204, None)
        collector().delete_session()
        self.assertEqual(delete.call_args.args[0], "http://pihole.test:80/api/auth")
        self.assertEqual(delete.call_args.kwargs["headers"]["X-FTL-SID"], "old-sid")
        self.assertEqual(delete.call_args.kwargs["timeout"], exporter.DEFAULT_TIMEOUT)

    def test_unexpected_status_does_not_raise(self, delete):
        delete.return_value = response(500, None)
        collector().delete_session()
        delete.assert_called_once()

    def test_request_error_does_not_raise(self, delete):
        delete.side_effect = exporter.requests.exceptions.ConnectionError("down")
        collector().delete_session()

    def test_skipped_without_auth(self, delete):
        collector(using_auth=False).delete_session()
        delete.assert_not_called()


@mock.patch.object(exporter.PiholeCollector, "get_sid")
class ConstructorTest(unittest.TestCase):
    def test_without_key_does_not_authenticate(self, get_sid):
        c = exporter.PiholeCollector("h", 80, "http", None)
        get_sid.assert_not_called()
        self.assertFalse(c.using_auth)

    def test_with_key_stores_session(self, get_sid):
        get_sid.return_value = {"sid": "s", "csrf": "c"}
        c = exporter.PiholeCollector("h", 8080, "https", "secret", timeout=5)
        self.assertTrue(c.using_auth)
        self.assertEqual((c.sid, c.csrf, c.password, c.timeout), ("s", "c", "secret", 5))

    def test_with_key_but_no_pihole_password_disables_auth(self, get_sid):
        get_sid.return_value = None
        c = exporter.PiholeCollector("h", 80, "http", "secret")
        self.assertFalse(c.using_auth)


if __name__ == "__main__":
    unittest.main()
