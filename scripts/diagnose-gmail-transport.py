from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httplib2
import requests

from signaldesk.connectors.gmail import GmailConnector
from signaldesk.database import Database

PROBE_URL = "https://www.googleapis.com/discovery/v1/apis/gmail/v1/rest"


def _error_code(value: str) -> str:
    ssl_code = re.search(r"\[SSL:\s*([^\]]+)]", value)
    if ssl_code:
        return f"ssl:{ssl_code.group(1).lower()}"
    return value.partition(":")[0].strip().lower() or "unknown"


def _exception_code(error: Exception) -> str:
    status = getattr(error, "status_code", None) or getattr(
        getattr(error, "resp", None), "status", None
    )
    if status:
        return f"http:{status}"
    return _error_code(f"{type(error).__name__}: {error}")


def _proxy_metadata() -> list[dict[str, str]]:
    records = []
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        value = os.environ.get(name)
        if value:
            records.append({"name": name, "scheme": urlparse(value).scheme or "n/a"})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe Gmail transports without printing tokens, mail, or proxy addresses."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--account-id")
    parser.add_argument("--sync-probe", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {
        "requests": None,
        "requests_without_environment": None,
        "httplib2": None,
        "proxy_environment": _proxy_metadata(),
        "accounts": [],
        "private_data": False,
    }
    try:
        report["requests"] = requests.get(PROBE_URL, timeout=10).status_code
    except Exception as error:
        report["requests"] = _error_code(f"{type(error).__name__}: {error}")
    try:
        session = requests.Session()
        session.trust_env = False
        report["requests_without_environment"] = session.get(
            PROBE_URL, timeout=10
        ).status_code
    except Exception as error:
        report["requests_without_environment"] = _error_code(
            f"{type(error).__name__}: {error}"
        )
    try:
        response, _ = httplib2.Http(timeout=10).request(PROBE_URL)
        report["httplib2"] = int(response.status)
    except Exception as error:
        report["httplib2"] = _error_code(f"{type(error).__name__}: {error}")

    database = Database(args.database)
    stored_health = {
        item["connector_id"]: item for item in database.connectors() if item["source"] == "gmail"
    }
    accounts = database.connector_accounts("gmail")
    if args.account_id:
        accounts = [item for item in accounts if item["account_id"] == args.account_id]
    outcomes = []
    for account in accounts:
        config = account["config"]
        connector = GmailConnector(
            account["account_id"],
            Path(config["credentials_path"]),
            draft_scope=bool(config.get("draft_scope", False)),
        )
        connected = connector.authenticate(interactive=False)
        health = connector.health()
        stored = stored_health.get(connector.connector_id, {})
        sync_probe: int | str | None = None
        if connected and args.sync_probe:
            try:
                batch = connector.incremental_sync(
                    database.connector_cursor(connector.connector_id)
                )
                sync_probe = len(batch.events)
            except Exception as error:
                sync_probe = _exception_code(error)
        outcomes.append(
            {
                "account_id": account["account_id"],
                "configured_connected": bool(config.get("connected")),
                "cursor_present": bool(database.connector_cursor(connector.connector_id)),
                "connected": connected,
                "status": health.status,
                "error_code": None if connected else _error_code(health.detail),
                "sync_probe": sync_probe,
                "stored_status": stored.get("status"),
                "stored_error_code": (
                    None
                    if stored.get("status") == "healthy"
                    else _error_code(str(stored.get("detail", "")))
                ),
            }
        )
    report["accounts"] = outcomes
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
