from __future__ import annotations

import uvicorn

from .config import load_settings


def run() -> None:
    config = load_settings()
    if config.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("SignalDesk refuses to bind to a non-loopback host")
    uvicorn.run(
        "signaldesk.api:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        access_log=True,
    )


if __name__ == "__main__":
    run()
