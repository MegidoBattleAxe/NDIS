import os
import stat
from urllib.parse import unquote

from incident_agent.config import Config
from incident_agent.graph_client import GraphClient


class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


class _FakeSession:
    def __init__(self):
        self.urls = []

    def get(self, url, headers=None, timeout=None, stream=False):
        self.urls.append(url)
        return _FakeResp({"value": []})

    def post(self, url, data=None, timeout=None):
        raise AssertionError("no network calls expected in these tests")


def _make_client(tmp_path, sender="info@1myp.com"):
    cfg = Config(
        tenant_id="tenant",
        client_id="client",
        mailbox="incidents@example.com",
        sender_address=sender,
        token_cache=tmp_path / ".token_cache.json",
    )
    session = _FakeSession()
    return GraphClient(cfg, session=session), session


def test_filter_url_is_encoded(tmp_path):
    client, session = _make_client(tmp_path)
    client.get_access_token = lambda: "fake-token"
    client.list_messages_from_sender(client.cfg.sender_address, since="2026-01-01T00:00:00Z")
    url = session.urls[0]
    assert " " not in url
    assert "'" not in url
    assert "from/emailAddress/address eq " in unquote(url)


def test_filter_escapes_odata_quote(tmp_path):
    client, session = _make_client(tmp_path, sender="o'brien@1myp.com")
    client.get_access_token = lambda: "fake-token"
    client.list_messages_from_sender("o'brien@1myp.com")
    url = session.urls[0]
    assert "o''brien" in unquote(url)


def test_token_cache_created_0600(tmp_path):
    client, _ = _make_client(tmp_path)
    client._save_cache({"access_token": "x"})
    mode = stat.S_IMODE((tmp_path / ".token_cache.json").stat().st_mode)
    assert mode == 0o600


def test_token_cache_tightens_existing_file(tmp_path):
    client, _ = _make_client(tmp_path)
    path = tmp_path / ".token_cache.json"
    path.write_text("{}", encoding="utf-8")
    os.chmod(path, 0o644)
    client._save_cache({"access_token": "x"})
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600
