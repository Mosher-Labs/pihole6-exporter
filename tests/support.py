"""Shared helpers for the pihole6_exporter tests."""

import importlib.machinery
import importlib.util
import pathlib
from unittest import mock

# The exporter is a script without a .py extension, so load it by path.
_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "pihole6_exporter"
_loader = importlib.machinery.SourceFileLoader("pihole6_exporter", str(_SCRIPT))
_spec = importlib.util.spec_from_loader("pihole6_exporter", _loader)
exporter = importlib.util.module_from_spec(_spec)
_loader.exec_module(exporter)


def response(status_code, body):
    """A fake requests.Response whose .json() returns body."""
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.text = str(body)
    return resp


def non_json_response(status_code, text):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.side_effect = ValueError("Expecting value")
    resp.text = text
    return resp


def collector(using_auth=True):
    """A PiholeCollector built without running __init__, so no network call happens."""
    c = object.__new__(exporter.PiholeCollector)
    c.protocol = "http"
    c.host = "pihole.test"
    c.pihole_port = 80
    c.timeout = exporter.DEFAULT_TIMEOUT
    c.using_auth = using_auth
    c.password = "secret"
    c.sid = "old-sid"
    c.csrf = "old-csrf"
    c.type_cnt = {}
    c.status_cnt = {}
    c.reply_cnt = {}
    c.client_cnt = {}
    c.upstream_cnt = {}
    return c
