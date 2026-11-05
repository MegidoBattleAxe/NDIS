import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests

LOGIN = "https://login.microsoftonline.com"
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPE = "https://graph.microsoft.com/.default"
DELEGATED_SCOPE = "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/User.Read offline_access"


class GraphAuthError(RuntimeError):
    pass


class GraphClient:
    def __init__(self, cfg, session=None):
        self.cfg = cfg
        self.session = session or requests.Session()
        self._token = None
        self._token_expiry = 0

    def _token_url(self):
        return f"{LOGIN}/{self.cfg.tenant_id}/oauth2/v2.0/token"

    def _load_cache(self):
        path = Path(self.cfg.token_cache)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_cache(self, data):
        path = Path(self.cfg.token_cache)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _store_token(self, resp):
        expires_in = int(resp.get("expires_in", 3600))
        self._token = resp["access_token"]
        self._token_expiry = time.time() + expires_in - 60
        cache = {"access_token": self._token, "expires_at": self._token_expiry}
        if resp.get("refresh_token"):
            cache["refresh_token"] = resp["refresh_token"]
        self._save_cache(cache)

    def _client_credentials_token(self):
        resp = self.session.post(
            self._token_url(),
            data={
                "client_id": self.cfg.client_id,
                "client_secret": self.cfg.client_secret,
                "scope": SCOPE,
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise GraphAuthError(f"client credentials token failed: {resp.status_code} {resp.text[:300]}")
        self._store_token(resp.json())

    def _refresh_token(self, refresh_token):
        resp = self.session.post(
            self._token_url(),
            data={
                "client_id": self.cfg.client_id,
                "refresh_token": refresh_token,
                "scope": DELEGATED_SCOPE if self.cfg.auth_mode == "device_code" else SCOPE,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return False
        self._store_token(resp.json())
        return True

    def _device_code_token(self):
        cache = self._load_cache()
        if cache.get("refresh_token") and self._refresh_token(cache["refresh_token"]):
            return
        dc = self.session.post(
            f"{LOGIN}/{self.cfg.tenant_id}/oauth2/v2.0/devicecode",
            data={"client_id": self.cfg.client_id, "scope": DELEGATED_SCOPE},
            timeout=30,
        )
        if dc.status_code != 200:
            raise GraphAuthError(f"device code request failed: {dc.status_code} {dc.text[:300]}")
        payload = dc.json()
        print("First-run sign-in required.")
        print(f"  1. Open {payload['verification_uri']} in a browser")
        print(f"  2. Enter code: {payload['user_code']}")
        print("  3. Sign in with the mailbox account: " + self.cfg.mailbox)
        interval = int(payload.get("interval", 5))
        deadline = time.time() + int(payload.get("expires_in", 900))
        while time.time() < deadline:
            time.sleep(interval)
            resp = self.session.post(
                self._token_url(),
                data={
                    "client_id": self.cfg.client_id,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": payload["device_code"],
                },
                timeout=30,
            )
            body = resp.json()
            if resp.status_code == 200:
                self._store_token(body)
                return
            if body.get("error") not in ("authorization_pending", "slow_down"):
                raise GraphAuthError(f"device code flow failed: {body.get('error')} {body.get('error_description', '')[:300]}")
            if body.get("error") == "slow_down":
                interval += 5
        raise GraphAuthError("device code flow timed out waiting for sign-in")

    def get_access_token(self):
        if self._token and time.time() < self._token_expiry:
            return self._token
        cache = self._load_cache()
        if cache.get("access_token") and float(cache.get("expires_at", 0)) > time.time() + 60:
            self._token = cache["access_token"]
            self._token_expiry = float(cache["expires_at"])
            return self._token
        if self.cfg.auth_mode == "client_credentials":
            self._client_credentials_token()
        else:
            self._device_code_token()
        return self._token

    def _get(self, url, stream=False):
        headers = {"Authorization": f"Bearer {self.get_access_token()}"}
        resp = self.session.get(url, headers=headers, timeout=60, stream=stream)
        if resp.status_code == 401:
            self._token = None
            self._token_expiry = 0
            headers = {"Authorization": f"Bearer {self.get_access_token()}"}
            resp = self.session.get(url, headers=headers, timeout=60, stream=stream)
        resp.raise_for_status()
        return resp

    def _paged(self, url):
        while url:
            resp = self._get(url)
            data = resp.json()
            yield from data.get("value", [])
            url = data.get("@odata.nextLink")

    def list_messages_from_sender(self, sender, since=None, top=100):
        mailbox = quote(self.cfg.mailbox, safe="@.")
        filters = [f"from/emailAddress/address eq '{sender.lower()}'", "hasAttachments eq true"]
        if since:
            filters.append(f"receivedDateTime ge {since}")
        query = (
            f"$filter={' and '.join(filters)}"
            "&$select=id,subject,receivedDateTime,from,hasAttachments"
            f"&$orderby=receivedDateTime desc&$top={top}"
        )
        url = f"{GRAPH}/users/{mailbox}/messages?{query}"
        return list(self._paged(url))

    def list_attachments(self, message_id):
        mailbox = quote(self.cfg.mailbox, safe="@.")
        url = (
            f"{GRAPH}/users/{mailbox}/messages/{message_id}/attachments"
            "?$select=id,name,contentType,size,isInline"
        )
        return list(self._paged(url))

    def download_attachment(self, message_id, attachment_id):
        mailbox = quote(self.cfg.mailbox, safe="@.")
        url = f"{GRAPH}/users/{mailbox}/messages/{message_id}/attachments/{attachment_id}/$value"
        resp = self._get(url)
        return resp.content


def since_iso(days):
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
