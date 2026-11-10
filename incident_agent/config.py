import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SENDER = "info@1myp.com"
DEFAULT_ORG = "Origin Support Services"


def load_env_file(path):
    values = {}
    if not path:
        return values
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"env file not found: {p}")
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass
class Config:
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    auth_mode: str = "device_code"
    mailbox: str = ""
    sender_address: str = DEFAULT_SENDER
    org_name: str = DEFAULT_ORG
    output_dir: Path = Path("output")
    downloads_dir: Path = Path("downloads")
    state_file: Path = Path("state.json")
    token_cache: Path = Path(".token_cache.json")
    lookback_days: int = 30
    poll_interval_seconds: int = 300
    max_attachment_bytes: int = 25 * 1024 * 1024

    @classmethod
    def from_env(cls, env_file=None, require_live=True):
        file_values = load_env_file(env_file)

        def get(key, default=""):
            return os.environ.get(key, file_values.get(key, default))

        auth_mode = get("NDIS_AUTH_MODE", "device_code").strip().lower()
        if auth_mode not in ("device_code", "client_credentials"):
            raise ValueError(f"NDIS_AUTH_MODE must be device_code or client_credentials, got {auth_mode!r}")
        cfg = cls(
            tenant_id=get("NDIS_TENANT_ID"),
            client_id=get("NDIS_CLIENT_ID"),
            client_secret=get("NDIS_CLIENT_SECRET"),
            auth_mode=auth_mode,
            mailbox=get("NDIS_MAILBOX"),
            sender_address=get("NDIS_SENDER", DEFAULT_SENDER).strip().lower(),
            org_name=get("NDIS_ORG_NAME", DEFAULT_ORG),
            output_dir=Path(get("NDIS_OUTPUT_DIR", "output")),
            downloads_dir=Path(get("NDIS_DOWNLOADS_DIR", "downloads")),
            state_file=Path(get("NDIS_STATE_FILE", "state.json")),
            token_cache=Path(get("NDIS_TOKEN_CACHE", ".token_cache.json")),
            lookback_days=int(get("NDIS_LOOKBACK_DAYS", "30")),
            poll_interval_seconds=int(get("NDIS_POLL_INTERVAL_SECONDS", "300")),
            max_attachment_bytes=int(get("NDIS_MAX_ATTACHMENT_BYTES", str(25 * 1024 * 1024))),
        )
        if require_live:
            cfg.validate_for_live()
        return cfg

    def validate_for_live(self):
        missing = [k for k in ("tenant_id", "client_id", "mailbox") if not getattr(self, k)]
        if missing:
            raise ValueError(
                "missing required config for live mode: "
                + ", ".join("NDIS_" + k.upper() for k in missing)
                + " (set them in the environment or an env file; see config.example.env)"
            )
        if self.auth_mode == "client_credentials" and not self.client_secret:
            raise ValueError("NDIS_CLIENT_SECRET is required when NDIS_AUTH_MODE=client_credentials")

    def ensure_dirs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
