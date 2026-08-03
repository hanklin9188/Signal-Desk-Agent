from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .actions import ActionError, CardActions
from .config import PROJECT_ROOT, Settings, load_settings
from .connectors.chat_archive import ChatArchiveError, load_chat_archives
from .connectors.gmail import GmailConnector
from .connectors.windows_bridge import WindowsBridgeConnector
from .database import Database
from .demo import seed_demo
from .events import EventBus
from .media_store import MediaError, MediaStore
from .model_gateway import build_gateway
from .models import (
    CardActionRequest,
    RuleCreate,
    UnifiedEvent,
    UserSettingsPatch,
    VisualAnalysis,
    WindowsNotificationPayload,
)
from .normalizer import is_browser_background_notice
from .pipeline import Pipeline
from .preference import PreferenceRanker
from .vision import build_vision_analyzer

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "system",
    "focus_mode": False,
    "shadow_mode": True,
    "onboarding_complete": False,
    "quiet_start": "23:00",
    "quiet_end": "08:00",
    "model_residency": "on_demand",
    "raw_retention_days": 7,
    "notification_allowlist": ["LINE", "Messenger", "Google Chrome", "Microsoft Edge"],
    "digest_time": "18:00",
    "focus_digest_minutes": 60,
    "now_window_hours": 6,
}


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[UnifiedEvent] = Field(min_length=1, max_length=100)


class GmailAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    credentials_path: str | None = None
    draft_scope: bool = False


class GmailAccountPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credentials_path: str | None = None
    draft_scope: bool | None = None


class GmailDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str


class GmailDataResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str


class ChatArchiveImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["line", "messenger"]
    paths: list[str] = Field(min_length=1, max_length=500)


class WindowsNotificationStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["allowed", "denied", "unspecified", "error"]
    detail: str | None = Field(default=None, max_length=500)


def _default_gmail_credentials(
    *, platform: str | None = None, local_app_data: str | None = None
) -> Path:
    provisioned = os.getenv("SIGNALDESK_GMAIL_CREDENTIALS")
    if provisioned:
        return Path(provisioned)
    platform = platform or os.name
    if platform == "nt":
        app_data = local_app_data or os.getenv("LOCALAPPDATA")
        if app_data:
            return Path(app_data) / "SignalDesk" / "oauth" / "credentials.json"
    return PROJECT_ROOT / "credentials.json"


def _session_token(config: Settings) -> str:
    provisioned = os.getenv("SIGNALDESK_AUTH_TOKEN")
    if provisioned:
        if len(provisioned) < 32:
            raise RuntimeError("SIGNALDESK_AUTH_TOKEN must contain at least 32 characters")
        return provisioned
    config.data_dir.mkdir(parents=True, exist_ok=True)
    path = config.data_dir / ".auth-token"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    path.write_text(token, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return token


def create_app(config: Settings | None = None, database: Database | None = None) -> FastAPI:
    config = config or load_settings()
    database = database or Database(config.database_path)
    database.ensure_defaults(
        {**DEFAULT_SETTINGS, "quiet_start": config.quiet_start, "quiet_end": config.quiet_end}
    )
    initial_settings = database.settings()
    if initial_settings.get("shadow_mode") and not initial_settings.get(
        "shadow_evaluation_started_at"
    ):
        database.update_settings(
            {"shadow_evaluation_started_at": datetime.now(UTC).isoformat()}
        )
    database.hide_browser_background_cards()
    repaired_messenger_cards = database.reclassify_messenger_browser_cards()
    database.collapse_duplicate_notification_replays()
    repaired_line_threads = database.normalize_line_notification_identities()
    merged_messenger_threads = database.merge_duplicate_messenger_threads()
    bus = EventBus()
    media_store = MediaStore(config.data_dir / "media")
    gateway = build_gateway(
        config.model_backend,
        config.model_endpoint,
        config.model_id,
        media_store=media_store,
        revision=config.model_revision,
        quantization=config.model_quantization,
    )
    vision = build_vision_analyzer(
        config.vision_backend,
        config.ocr_model_id,
        config.ocr_model_revision,
        media_store,
        max_new_tokens=config.ocr_max_new_tokens,
    )
    preferences = PreferenceRanker(database)
    pipeline = Pipeline(database, config, gateway, bus, preferences)
    if config.model_backend in {"endpoint", "transformers"}:
        database.queue_recent_cards_for_model()
    for thread_id in repaired_line_threads:
        pipeline.analyze_thread(thread_id)
    if repaired_messenger_cards:
        for thread_id in database.thread_ids_for_source("messenger_notification"):
            pipeline.analyze_thread(thread_id)
    database.sync_card_event_timestamps(
        database.thread_ids_for_source("line_notification")
    )
    for thread_id in merged_messenger_threads:
        pipeline.analyze_thread(thread_id)
    card_actions = CardActions(database, bus, preferences)
    windows = WindowsBridgeConnector()
    default_credentials = _default_gmail_credentials()
    default_draft_scope = os.getenv("SIGNALDESK_GMAIL_DRAFT_SCOPE", "0") == "1"
    account_records = database.connector_accounts("gmail")
    if not account_records:
        database.upsert_connector_account(
            "gmail:personal",
            "gmail",
            "personal",
            {
                "credentials_path": str(default_credentials),
                "draft_scope": default_draft_scope,
                "connected": False,
            },
        )
        account_records = database.connector_accounts("gmail")
    gmail_connectors = {
        record["account_id"]: GmailConnector(
            account_id=record["account_id"],
            client_secrets=Path(record["config"].get("credentials_path", default_credentials)),
            draft_scope=bool(record["config"].get("draft_scope", default_draft_scope)),
            media_store=media_store,
        )
        for record in account_records
    }
    token = _session_token(config)
    static_dir = PROJECT_ROOT / "signaldesk" / "static"

    for gmail in gmail_connectors.values():
        gmail_detail = (
            "Ready for OAuth"
            if gmail.client_secrets.exists()
            else "Add Google Desktop OAuth credentials.json to connect"
        )
        database.set_connector_health(
            gmail.connector_id,
            "gmail",
            "not_configured",
            gmail_detail,
            ["read", "read_images", *(["create_draft"] if gmail.draft_scope else [])],
        )
    windows_health = windows.health()
    database.set_connector_health(
        windows_health.connector_id,
        windows_health.source,
        windows_health.status,
        windows_health.detail,
        windows_health.capabilities,
    )
    line_webhook_secret = os.getenv("SIGNALDESK_LINE_CHANNEL_SECRET", "")
    meta_app_secret = os.getenv("SIGNALDESK_META_APP_SECRET", "")
    meta_verify_token = os.getenv("SIGNALDESK_META_VERIFY_TOKEN", "")
    database.set_connector_health(
        "line:official",
        "line_official_webhook",
        "healthy" if line_webhook_secret else "not_configured",
        "Signed webhook receiver ready" if line_webhook_secret else "Add LINE channel secret",
        ["receive_webhook"],
    )
    database.set_connector_health(
        "messenger:page",
        "messenger_page_webhook",
        "healthy" if meta_app_secret and meta_verify_token else "not_configured",
        (
            "Signed webhook receiver ready"
            if meta_app_secret and meta_verify_token
            else "Add Meta app secret and verify token"
        ),
        ["receive_webhook"],
    )

    isolate_local_models = (
        os.name == "nt"
        and config.model_backend == "transformers"
        and config.model_isolation
    )

    async def run_isolated_model_worker(kind: str, *identifiers: str) -> bool:
        """Run CUDA inference in a disposable process so Windows reclaims its context."""
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "signaldesk.local_model_worker",
            kind,
            *identifiers,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            return await asyncio.wait_for(process.wait(), timeout=900) == 0
        except TimeoutError:
            process.kill()
            await process.wait()
            return False

    async def background_worker() -> None:
        last_daily_digest: str | None = None
        last_focus_digest = time.monotonic()
        last_reminder_check = 0.0
        last_gmail_sync = 0.0
        last_digest_check = 0.0
        last_cleanup = 0.0
        first_cycle = True
        while True:
            if not first_cycle:
                await asyncio.sleep(2)
            first_cycle = False
            monotonic_now = time.monotonic()
            if monotonic_now - last_reminder_check >= 30:
                for reminder in database.fire_due_reminders():
                    bus.publish("reminder_due", reminder)
                last_reminder_check = monotonic_now
            # Keep GPU work in a small sequential batch. The original event/card is
            # already safely persisted, so OCR failure can never lose a notification.
            processed_vision = False
            if config.vision_backend != "disabled" and config.vision_auto_analyze:
                # Poll every two seconds so a newly persisted image starts automatically.
                # One image per cycle bounds foreground latency and KV-cache growth.
                media_batch = database.unanalyzed_media(limit=1)
                if media_batch and not isolate_local_models:
                    # Never let the general VLM and OCR model coexist on a 16 GB GPU.
                    await asyncio.to_thread(gateway.release)
                try:
                    for media in media_batch:
                        processed_vision = True
                        try:
                            if isolate_local_models:
                                completed = await run_isolated_model_worker(
                                    "vision", media.asset_id
                                )
                                analysis = database.visual_analysis(media.asset_id)
                                if not completed or analysis is None:
                                    raise RuntimeError("isolated vision worker failed")
                            else:
                                analysis = await asyncio.to_thread(vision.analyze, media)
                        except Exception as error:
                            # A failed model load must not kill the lifelong desktop worker.
                            # Persist only the exception class; never persist private image text.
                            analysis = VisualAnalysis(
                                asset_id=media.asset_id,
                                asset_sha256=media.sha256,
                                status="failed",
                                ocr_model_id=config.ocr_model_id,
                                ocr_model_revision=config.ocr_model_revision,
                                error_code=type(error).__name__.lower(),
                                started_at=datetime.now(UTC),
                                completed_at=datetime.now(UTC),
                            )
                        database.save_visual_analysis(analysis)
                        for thread_id in database.thread_ids_for_media(media.asset_id):
                            await asyncio.to_thread(pipeline.analyze_thread, thread_id)
                finally:
                    if processed_vision and not isolate_local_models:
                        await asyncio.to_thread(vision.release)
            # Qwen runs after the deterministic card is already visible. This keeps
            # notification ingestion and app startup responsive even when the model
            # is cold-loading, while still replacing the baseline after validation.
            # OCR and Qwen never occupy VRAM together. Process a small Qwen batch only
            # on a cycle without OCR work, then return its weights and KV cache.
            model_residency = str(
                database.settings().get("model_residency", "on_demand")
            )
            if (
                not processed_vision
                and model_residency != "paused"
                and config.model_backend in {"endpoint", "transformers"}
            ):
                model_batch = database.pending_model_thread_ids(limit=8)
                if isolate_local_models and model_batch:
                    completed = await run_isolated_model_worker("triage", *model_batch)
                    if not completed:
                        database.mark_model_worker_failed(model_batch)
                    if completed:
                        for thread_id in model_batch:
                            card_id = "card_" + hashlib.sha256(thread_id.encode()).hexdigest()[:20]
                            bus.publish(
                                "card_updated",
                                {"card_id": card_id, "thread_id": thread_id},
                            )
                else:
                    for thread_id in model_batch:
                        await asyncio.to_thread(
                            lambda value=thread_id: pipeline.analyze_thread(
                                value, use_model=True
                            )
                        )
                    if model_batch and model_residency != "always_on":
                        await asyncio.to_thread(gateway.release)
            # Restore connected OAuth sessions immediately after launch, then poll every minute.
            if monotonic_now - last_gmail_sync >= 60:
                records = {
                    item["account_id"]: item for item in database.connector_accounts("gmail")
                }
                for gmail in list(gmail_connectors.values()):
                    if not records.get(gmail.account_id, {}).get("config", {}).get("connected"):
                        continue
                    try:
                        if gmail.health().status != "healthy" and not await asyncio.to_thread(
                            gmail.authenticate, interactive=False
                        ):
                            persist_gmail_health(gmail)
                            continue
                        await sync_gmail_connector(gmail)
                    except Exception as error:
                        database.set_connector_health(
                            gmail.connector_id,
                            "gmail",
                            "degraded",
                            f"Sync failed: {type(error).__name__}",
                            gmail.health().capabilities,
                        )
                last_gmail_sync = time.monotonic()

            current = database.settings()
            local_now = datetime.now(ZoneInfo(config.timezone))
            if monotonic_now - last_digest_check >= 30:
                digest_at = str(current.get("digest_time", "18:00"))
                if (
                    local_now.strftime("%H:%M") >= digest_at
                    and last_daily_digest != local_now.date().isoformat()
                ):
                    digest_payload = database.digest()
                    if digest_payload["analysis"]["pending"] == 0:
                        bus.publish("digest_ready", {"kind": "daily", **digest_payload})
                        last_daily_digest = local_now.date().isoformat()
                last_digest_check = monotonic_now
            focus_minutes = int(current.get("focus_digest_minutes", 60))
            if bool(current.get("focus_mode")):
                if time.monotonic() - last_focus_digest >= focus_minutes * 60:
                    digest_payload = database.digest()
                    if digest_payload["analysis"]["pending"] == 0:
                        bus.publish("digest_ready", {"kind": "focus", **digest_payload})
                        last_focus_digest = time.monotonic()
            else:
                last_focus_digest = time.monotonic()
            if monotonic_now - last_cleanup >= 60 * 60:
                database.cleanup_retention(
                    int(current.get("raw_retention_days", config.raw_retention_days)),
                    config.normalized_retention_days,
                    config.summary_retention_days,
                )
                for media in database.delete_orphan_media():
                    media_store.delete(media)
                last_cleanup = monotonic_now

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if config.demo and database.counts()["open"] == 0:
            seed_demo(pipeline)
            database.update_settings({"onboarding_complete": True})
        worker = asyncio.create_task(background_worker())
        try:
            yield
        finally:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="SignalDesk Agent",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.config = config
    app.state.database = database
    app.state.pipeline = pipeline
    app.state.bus = bus
    app.state.auth_token = token
    app.state.windows_connector = windows
    app.state.gmail_connectors = gmail_connectors
    app.state.media_store = media_store

    request_times: dict[str, deque[float]] = defaultdict(deque)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Any) -> Response:
        content_length = int(request.headers.get("content-length", "0") or 0)
        if content_length > config.max_request_bytes:
            return JSONResponse({"detail": "request too large"}, status_code=413)
        if request.url.path.startswith(("/api/v1", "/webhooks")):
            client = request.client.host if request.client else "local"
            now = time.monotonic()
            window = request_times[client]
            while window and window[0] < now - 60:
                window.popleft()
            if len(window) >= 300:
                return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
            window.append(now)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path == "/":
            response.set_cookie(
                "signaldesk_session",
                token,
                httponly=True,
                samesite="strict",
                max_age=86400 * 30,
            )
        return response

    def require_auth(request: Request, authorization: str | None = Header(default=None)) -> None:
        supplied = request.cookies.get("signaldesk_session")
        if authorization and authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
        if not supplied or not secrets.compare_digest(supplied, token):
            raise HTTPException(status_code=401, detail="local session authentication required")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/healthz")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": __version__, "private_data": False}

    @app.get("/readyz")
    def ready() -> dict[str, Any]:
        try:
            database.counts()
            return {"status": "ready", "database": "ok"}
        except Exception:
            raise HTTPException(status_code=503, detail="database unavailable") from None

    @app.get("/metrics")
    def metrics() -> Response:
        counts = database.counts(
            now_window_hours=int(database.settings().get("now_window_hours", 6))
        )
        body = "\n".join(
            [
                "# HELP signaldesk_cards Local card counts without message content",
                "# TYPE signaldesk_cards gauge",
                *(f'signaldesk_cards{{state="{key}"}} {value}' for key, value in counts.items()),
            ]
        )
        return Response(body + "\n", media_type="text/plain")

    @app.post("/webhooks/line")
    async def line_webhook(
        request: Request, x_line_signature: str | None = Header(default=None)
    ) -> dict[str, Any]:
        if not line_webhook_secret:
            raise HTTPException(status_code=503, detail="LINE webhook is not configured")
        raw = await request.body()
        expected = base64.b64encode(
            hmac.new(line_webhook_secret.encode(), raw, hashlib.sha256).digest()
        ).decode()
        if not x_line_signature or not hmac.compare_digest(x_line_signature, expected):
            raise HTTPException(status_code=401, detail="invalid LINE webhook signature")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="invalid webhook JSON") from error
        results: list[dict[str, Any]] = []
        for item in payload.get("events", []):
            message = item.get("message", {})
            source = item.get("source", {})
            if item.get("type") != "message" or message.get("type") != "text":
                continue
            source_id = source.get("groupId") or source.get("roomId") or source.get("userId")
            event = UnifiedEvent(
                event_id=f"line_webhook_{message.get('id') or uuid.uuid4().hex}",
                source="line_official_webhook",
                source_app_id="line_official",
                account_id=os.getenv("SIGNALDESK_LINE_ACCOUNT_ID", "line_official"),
                sender=str(source.get("userId") or "LINE user"),
                conversation_id=str(source_id or "unknown"),
                content=str(message.get("text", "")),
                content_completeness="full",
                received_at=datetime.fromtimestamp(int(item.get("timestamp", 0)) / 1000, tz=UTC),
                metadata={"webhook_event_id": item.get("webhookEventId")},
            )
            results.append(pipeline.process(event).model_dump(mode="json"))
        return {"accepted": True, "processed": len(results), "results": results}

    @app.get("/webhooks/messenger")
    def messenger_verify(
        hub_mode: str = Query(alias="hub.mode"),
        hub_verify_token: str = Query(alias="hub.verify_token"),
        hub_challenge: str = Query(alias="hub.challenge"),
    ) -> Response:
        if (
            not meta_verify_token
            or hub_mode != "subscribe"
            or not hmac.compare_digest(hub_verify_token, meta_verify_token)
        ):
            raise HTTPException(status_code=403, detail="webhook verification failed")
        return Response(hub_challenge, media_type="text/plain")

    @app.post("/webhooks/messenger")
    async def messenger_webhook(
        request: Request, x_hub_signature_256: str | None = Header(default=None)
    ) -> dict[str, Any]:
        if not meta_app_secret:
            raise HTTPException(status_code=503, detail="Messenger webhook is not configured")
        raw = await request.body()
        expected = "sha256=" + hmac.new(meta_app_secret.encode(), raw, hashlib.sha256).hexdigest()
        if not x_hub_signature_256 or not hmac.compare_digest(x_hub_signature_256, expected):
            raise HTTPException(status_code=401, detail="invalid Meta webhook signature")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="invalid webhook JSON") from error
        results: list[dict[str, Any]] = []
        for entry in payload.get("entry", []):
            for item in entry.get("messaging", []):
                message = item.get("message", {})
                if not message.get("text") or message.get("is_echo"):
                    continue
                sender_id = str(item.get("sender", {}).get("id") or "Meta user")
                message_id = message.get("mid") or uuid.uuid4().hex
                event = UnifiedEvent(
                    event_id=f"messenger_webhook_{message_id}",
                    source="messenger_page_webhook",
                    source_app_id="messenger_page",
                    account_id=str(entry.get("id") or "messenger_page"),
                    sender=sender_id,
                    conversation_id=sender_id,
                    content=str(message["text"]),
                    content_completeness="full",
                    received_at=datetime.fromtimestamp(
                        int(item.get("timestamp", 0)) / 1000, tz=UTC
                    ),
                    metadata={"message_id": message_id},
                )
                results.append(pipeline.process(event).model_dump(mode="json"))
        return {"accepted": True, "processed": len(results), "results": results}

    router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])

    @router.get("/bootstrap")
    def bootstrap() -> dict[str, Any]:
        now_window_hours = int(database.settings().get("now_window_hours", 6))
        return {
            "version": __version__,
            "cards": database.list_cards(
                view="now", now_window_hours=now_window_hours, limit=100
            ),
            "counts": database.counts(now_window_hours=now_window_hours),
            "settings": database.settings(),
            "connectors": database.connectors(),
            "model": {
                "backend": config.model_backend,
                "id": config.model_id,
                "revision": config.model_revision,
                "quantization": config.model_quantization,
                "process_isolation": isolate_local_models,
                "ocr_max_new_tokens": config.ocr_max_new_tokens,
                "external_inference": False,
                "status": "available" if config.model_backend != "rule" else "rule_fallback",
            },
            "vision": {
                "backend": vision.backend_name,
                "ocr_model_id": config.ocr_model_id,
                "ocr_model_revision": config.ocr_model_revision,
                "auto_analyze": config.vision_auto_analyze,
                "status": "available" if config.vision_backend != "disabled" else "disabled",
            },
            "privacy": {"local_only": True, "auto_send": False},
        }

    @router.get("/cards")
    def cards(
        view: str = "all",
        search: str = "",
        source: str | None = None,
        priority: str | None = None,
        date: str | None = Query(default=None, pattern=r"^(today|7d|30d)?$"),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        now_window_hours = int(database.settings().get("now_window_hours", 6))
        return {
            "items": database.list_cards(
                view=view,
                search=search,
                source=source,
                priority=priority,
                date_filter=date,
                timezone=config.timezone,
                now_window_hours=now_window_hours,
                limit=limit,
            ),
            "counts": database.counts(now_window_hours=now_window_hours),
        }

    @router.get("/cards/{card_id}")
    def card(card_id: str) -> dict[str, Any]:
        detail = database.card_detail(card_id)
        if not detail:
            raise HTTPException(status_code=404, detail="card not found")
        return detail

    @router.get("/media/{asset_id}")
    def media_content(asset_id: str) -> FileResponse:
        media = database.media_asset(asset_id)
        if not media:
            raise HTTPException(status_code=404, detail="media not found")
        try:
            path = media_store.path_for(media)
        except MediaError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return FileResponse(
            path,
            media_type=media.mime_type,
            headers={"Cache-Control": "private, no-store"},
        )

    @router.get("/media/{asset_id}/thumbnail")
    def media_thumbnail(asset_id: str) -> FileResponse:
        media = database.media_asset(asset_id)
        if not media:
            raise HTTPException(status_code=404, detail="media not found")
        try:
            path = media_store.thumbnail_path_for(media)
        except MediaError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return FileResponse(
            path,
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=3600"},
        )

    @router.get("/media/{asset_id}/analysis")
    def media_analysis(asset_id: str) -> dict[str, Any]:
        if not database.media_asset(asset_id):
            raise HTTPException(status_code=404, detail="media not found")
        analysis = database.visual_analysis(asset_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="analysis not found")
        return analysis.model_dump(mode="json")

    @router.post("/media/{asset_id}/analysis")
    async def analyze_media(asset_id: str) -> dict[str, Any]:
        media = database.media_asset(asset_id)
        if not media:
            raise HTTPException(status_code=404, detail="media not found")
        if config.vision_backend == "disabled":
            raise HTTPException(status_code=503, detail="vision analysis is disabled")
        if isolate_local_models:
            completed = await run_isolated_model_worker("vision", asset_id)
            analysis = database.visual_analysis(asset_id)
            if not completed or analysis is None:
                raise HTTPException(status_code=503, detail="vision worker failed")
        else:
            try:
                analysis = await asyncio.to_thread(vision.analyze, media)
                database.save_visual_analysis(analysis)
            finally:
                await asyncio.to_thread(vision.release)
        # This is an explicit user request, so Qwen may inspect the real image even
        # when OCR found no text. OCR is released first to keep both models disjoint.
        semantic_status = "disabled"
        if config.model_backend in {"endpoint", "transformers"}:
            semantic_status = "rule_fallback"
            thread_ids = database.thread_ids_for_media(asset_id)
            if isolate_local_models:
                completed = await run_isolated_model_worker("triage", *thread_ids)
                if not completed:
                    database.mark_model_worker_failed(thread_ids)
                if completed:
                    for thread_id in thread_ids:
                        card_id = "card_" + hashlib.sha256(thread_id.encode()).hexdigest()[:20]
                        bus.publish(
                            "card_updated", {"card_id": card_id, "thread_id": thread_id}
                        )
            else:
                try:
                    for thread_id in thread_ids:
                        await asyncio.to_thread(
                            lambda value=thread_id: pipeline.analyze_thread(
                                value, use_model=True
                            )
                        )
                finally:
                    await asyncio.to_thread(gateway.release)
            for thread_id in thread_ids:
                card_id = "card_" + hashlib.sha256(thread_id.encode()).hexdigest()[:20]
                detail = database.card_detail(card_id)
                backend = str(detail.get("model_backend", "")) if detail else ""
                if backend.startswith("qwen") and "fallback" not in backend:
                    semantic_status = "completed"
        payload = analysis.model_dump(mode="json")
        payload["semantic_status"] = semantic_status
        return payload

    @router.post("/cards/{card_id}/actions")
    def card_action(card_id: str, request: CardActionRequest) -> dict[str, Any]:
        try:
            return card_actions.perform(card_id, request)
        except ActionError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @router.post("/events", status_code=201)
    def ingest(event: UnifiedEvent) -> dict[str, Any]:
        return pipeline.process(event).model_dump(mode="json")

    @router.post("/events/batch", status_code=201)
    def ingest_batch(batch: BatchRequest) -> dict[str, Any]:
        return {
            "results": [pipeline.process(event).model_dump(mode="json") for event in batch.events]
        }

    @router.post("/connectors/windows/notifications", status_code=201)
    def windows_notification(payload: WindowsNotificationPayload) -> dict[str, Any]:
        allowlist = database.settings().get("notification_allowlist", [])
        if allowlist and not any(
            allowed.casefold() in f"{payload.app_id} {payload.app_name}".casefold()
            for allowed in allowlist
        ):
            return {"accepted": False, "reason": "app_not_allowed"}
        windows.permission = "allowed"
        health_state = windows.health()
        database.set_connector_health(
            health_state.connector_id,
            health_state.source,
            health_state.status,
            health_state.detail,
            health_state.capabilities,
            synced=True,
        )
        native_app = f"{payload.app_id} {payload.app_name}".casefold()
        visible_text = "\n".join(part for part in (payload.title, payload.body) if part)
        if any(browser in native_app for browser in ("chrome", "edge", "firefox")) and (
            is_browser_background_notice(visible_text)
        ):
            bus.publish(
                "connector_health", {"connector_id": windows.connector_id, "status": "healthy"}
            )
            return {"accepted": False, "reason": "browser_background_status"}
        event = windows.normalize(payload)
        result = pipeline.process(event).model_dump(mode="json")
        bus.publish("connector_health", {"connector_id": windows.connector_id, "status": "healthy"})
        return {"accepted": True, **result}

    @router.post("/connectors/windows/status")
    def windows_notification_status(
        request: WindowsNotificationStatusRequest,
    ) -> dict[str, Any]:
        windows.set_permission(request.status, request.detail)
        health_state = windows.health()
        database.set_connector_health(
            health_state.connector_id,
            health_state.source,
            health_state.status,
            health_state.detail,
            health_state.capabilities,
            synced=request.status == "allowed",
        )
        bus.publish(
            "connector_health",
            {"connector_id": windows.connector_id, "status": health_state.status},
        )
        return {
            "connector_id": health_state.connector_id,
            "source": health_state.source,
            "status": health_state.status,
            "detail": health_state.detail,
            "capabilities": health_state.capabilities,
        }

    @router.get("/connectors")
    def connectors() -> dict[str, Any]:
        return {"items": database.connectors()}

    @router.post("/connectors/chat-archives/import")
    def import_chat_archives(request: ChatArchiveImportRequest) -> dict[str, Any]:
        try:
            parsed = load_chat_archives(
                request.source,
                request.paths,
                timezone=config.timezone,
                media_store=media_store,
            )
        except ChatArchiveError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        imported = 0
        existing_event_ids = database.existing_event_ids(
            [event.event_id for event in parsed.events]
        )
        duplicates = sum(
            1 for event in parsed.events if event.event_id in existing_event_ids
        )
        affected_threads: set[str] = set()
        for event in parsed.events:
            if event.event_id in existing_event_ids:
                continue
            result = pipeline.process(event, analyze=False, archive_import=True)
            if result.duplicate:
                duplicates += 1
            else:
                imported += 1
                if result.thread_id:
                    affected_threads.add(result.thread_id)

        cards: list[str] = []
        for thread_id in sorted(affected_threads):
            analyzed = pipeline.analyze_thread(thread_id, archive_import=True)
            if analyzed.card_id:
                cards.append(analyzed.card_id)
        bus.publish(
            "archive_imported",
            {
                "source": request.source,
                "imported": imported,
                "duplicates": duplicates,
                "conversations": len(parsed.conversations),
            },
        )
        return {
            "source": request.source,
            "files": parsed.files,
            "parsed": len(parsed.events),
            "imported": imported,
            "duplicates": duplicates,
            "skipped": parsed.skipped,
            "conversations": len(parsed.conversations),
            "cards_updated": len(cards),
            "warnings": parsed.warnings[:50],
        }

    def gmail_for(account_id: str) -> GmailConnector:
        connector = gmail_connectors.get(account_id)
        if connector is None:
            raise HTTPException(status_code=404, detail="Gmail account was not found")
        return connector

    def gmail_record(account_id: str) -> dict[str, Any]:
        return next(
            (
                record
                for record in database.connector_accounts("gmail")
                if record["account_id"] == account_id
            ),
            {},
        )

    def save_gmail_config(gmail: GmailConnector, *, connected: bool) -> None:
        database.upsert_connector_account(
            gmail.connector_id,
            "gmail",
            gmail.account_id,
            {
                "credentials_path": str(gmail.client_secrets),
                "draft_scope": gmail.draft_scope,
                "connected": connected,
            },
        )

    def persist_gmail_health(gmail: GmailConnector, synced: bool = False) -> None:
        health_state = gmail.health()
        database.set_connector_health(
            health_state.connector_id,
            health_state.source,
            health_state.status,
            health_state.detail,
            health_state.capabilities,
            synced=synced,
        )

    async def sync_gmail_connector(gmail: GmailConnector) -> list[dict[str, Any]]:
        cursor = database.connector_cursor(gmail.connector_id)
        batch = await asyncio.to_thread(gmail.incremental_sync, cursor)
        if batch.full_sync_required:
            batch = await asyncio.to_thread(gmail.initial_sync)
        results = [pipeline.process(event).model_dump(mode="json") for event in batch.events]
        database.set_connector_cursor(gmail.connector_id, batch.cursor)
        persist_gmail_health(gmail, synced=True)
        bus.publish("connector_health", {"connector_id": gmail.connector_id, "status": "healthy"})
        return results

    @router.post("/connectors/gmail/accounts", status_code=201)
    def add_gmail_account(request: GmailAccountRequest) -> dict[str, Any]:
        if request.account_id in gmail_connectors:
            raise HTTPException(status_code=409, detail="Gmail account alias already exists")
        credentials = (
            Path(request.credentials_path) if request.credentials_path else default_credentials
        )
        connector = GmailConnector(
            request.account_id,
            credentials,
            draft_scope=request.draft_scope,
            media_store=media_store,
        )
        gmail_connectors[request.account_id] = connector
        save_gmail_config(connector, connected=False)
        persist_gmail_health(connector)
        bus.publish(
            "connector_health", {"connector_id": connector.connector_id, "status": "not_configured"}
        )
        return {
            "account_id": request.account_id,
            "connector_id": connector.connector_id,
            "draft_scope": connector.draft_scope,
        }

    @router.patch("/connectors/gmail/accounts/{account_id}")
    async def configure_gmail_account(
        account_id: str, request: GmailAccountPatch
    ) -> dict[str, Any]:
        gmail = gmail_for(account_id)
        next_credentials = (
            Path(request.credentials_path) if request.credentials_path else gmail.client_secrets
        )
        next_draft_scope = (
            request.draft_scope if request.draft_scope is not None else gmail.draft_scope
        )
        changed = next_credentials != gmail.client_secrets or next_draft_scope != gmail.draft_scope
        if changed:
            try:
                await asyncio.to_thread(gmail.revoke)
            except RuntimeError:
                # The optional Gmail extra may not yet be installed in a development environment.
                # No usable OAuth token can exist there, so configuration may still be saved.
                pass
            gmail.client_secrets = next_credentials
            gmail.draft_scope = next_draft_scope
            save_gmail_config(gmail, connected=False)
            persist_gmail_health(gmail)
        return {
            "account_id": gmail.account_id,
            "connector_id": gmail.connector_id,
            "credentials_path": str(gmail.client_secrets),
            "draft_scope": gmail.draft_scope,
            "authorization_required": changed,
        }

    @router.post("/connectors/gmail/connect")
    async def connect_gmail(account_id: str = "personal") -> dict[str, Any]:
        gmail = gmail_for(account_id)
        if not gmail.client_secrets.exists():
            raise HTTPException(
                status_code=400,
                detail="Google Desktop OAuth credentials.json was not found",
            )
        authenticated = await asyncio.to_thread(gmail.authenticate)
        persist_gmail_health(gmail)
        if not authenticated:
            raise HTTPException(status_code=503, detail=gmail.health().detail)
        batch = await asyncio.to_thread(gmail.initial_sync)
        results = [pipeline.process(event).model_dump(mode="json") for event in batch.events]
        database.set_connector_cursor(gmail.connector_id, batch.cursor)
        persist_gmail_health(gmail, synced=True)
        save_gmail_config(gmail, connected=True)
        bus.publish("connector_health", {"connector_id": gmail.connector_id, "status": "healthy"})
        return {"connected": True, "synced": len(results), "results": results}

    @router.post("/connectors/gmail/sync")
    async def sync_gmail(account_id: str = "personal") -> dict[str, Any]:
        gmail = gmail_for(account_id)
        results = await sync_gmail_connector(gmail)
        return {"synced": len(results), "results": results}

    @router.delete("/connectors/gmail")
    async def disconnect_gmail(account_id: str = "personal") -> dict[str, bool]:
        gmail = gmail_for(account_id)
        try:
            await asyncio.to_thread(gmail.revoke)
        except RuntimeError:
            # A development environment without the optional Gmail extra cannot
            # contain a usable Gmail token, so it is already disconnected.
            pass
        save_gmail_config(gmail, connected=False)
        persist_gmail_health(gmail)
        return {"disconnected": True}

    @router.delete("/connectors/gmail/accounts/{account_id}")
    async def remove_gmail_account(account_id: str) -> dict[str, bool]:
        gmail = gmail_for(account_id)
        await asyncio.to_thread(gmail.revoke)
        database.delete_connector_account(gmail.connector_id)
        del gmail_connectors[account_id]
        bus.publish("connector_health", {"connector_id": gmail.connector_id, "status": "removed"})
        return {"removed": True}

    @router.post("/connectors/gmail/accounts/{account_id}/reset-data")
    async def reset_gmail_account_data(
        account_id: str, request: GmailDataResetRequest
    ) -> dict[str, Any]:
        gmail = gmail_for(account_id)
        if request.confirmation != "RESET GMAIL ACCOUNT DATA":
            raise HTTPException(status_code=400, detail="exact confirmation required")
        try:
            await asyncio.to_thread(gmail.revoke)
        except RuntimeError:
            # No optional Gmail extra means no usable token exists to revoke.
            pass
        removed = database.delete_source_account_data("gmail", account_id)
        for media in database.delete_orphan_media():
            media_store.delete(media)
        save_gmail_config(gmail, connected=False)
        persist_gmail_health(gmail)
        bus.publish(
            "connector_health",
            {"connector_id": gmail.connector_id, "status": "not_configured"},
        )
        return {"reset": True, "removed": removed}

    @router.post("/drafts/{draft_id}/gmail")
    async def create_gmail_draft(draft_id: str, request: GmailDraftRequest) -> dict[str, Any]:
        if request.confirmation != "CREATE GMAIL DRAFT":
            raise HTTPException(status_code=400, detail="confirmation phrase does not match")
        draft = database.draft_detail(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="local draft was not found")
        if draft["source"] != "gmail":
            raise HTTPException(status_code=400, detail="only Gmail drafts can be synchronized")
        gmail = gmail_for(draft["account_id"])
        if not gmail.draft_scope:
            raise HTTPException(status_code=400, detail="Gmail draft scope is not enabled")
        result = await asyncio.to_thread(
            gmail.create_draft,
            recipient=draft["recipient"] or "",
            subject=draft["subject"] or "Re:",
            body=draft["body"],
            thread_id=draft["conversation_id"],
        )
        external_id = str(result.get("id", "created"))
        database.update_draft_status(draft_id, f"gmail_draft:{external_id}")
        bus.publish("card_updated", {"card_id": draft["card_id"], "action": "gmail_draft"})
        return {
            "created": True,
            "draft_id": draft_id,
            "gmail_draft_id": external_id,
            "sent": False,
        }

    @router.get("/model/health")
    def model_health() -> dict[str, Any]:
        return {
            "backend": config.model_backend,
            "model_id": config.model_id,
            "quantization": config.model_quantization,
            "ocr_max_new_tokens": config.ocr_max_new_tokens,
            "status": "disabled_rule_mode" if config.model_backend == "rule" else "configured",
            "context_tokens": 512,
            "thinking": False,
        }

    @router.get("/digest")
    def digest() -> dict[str, Any]:
        return database.digest()

    @router.get("/settings")
    def settings() -> dict[str, Any]:
        return database.settings()

    @router.patch("/settings")
    def update_settings(patch: UserSettingsPatch) -> dict[str, Any]:
        values = patch.model_dump(exclude_none=True)
        updated = database.update_settings(values)
        bus.publish("settings_updated", values)
        return updated

    @router.post("/preferences/reset")
    def reset_preferences() -> dict[str, bool]:
        database.reset_preferences()
        bus.publish("settings_updated", {"personalization_reset": True})
        return {"reset": True}

    @router.get("/rules")
    def rules() -> dict[str, Any]:
        return {"items": database.rules()}

    @router.post("/rules", status_code=201)
    def create_rule(rule: RuleCreate) -> dict[str, Any]:
        rule_id = f"rule_{uuid.uuid4().hex}"
        database.add_rule(rule_id, rule.kind, rule.pattern, rule.value)
        return {"rule_id": rule_id, **rule.model_dump()}

    @router.delete("/rules/{rule_id}")
    def delete_rule(rule_id: str) -> dict[str, bool]:
        if not database.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail="rule not found")
        return {"deleted": True}

    @router.post("/demo/seed")
    def demo_seed() -> dict[str, Any]:
        results = seed_demo(pipeline)
        database.update_settings({"onboarding_complete": True})
        return {"results": results, "counts": database.counts()}

    @router.get("/privacy/export")
    def privacy_export() -> dict[str, Any]:
        return database.export_privacy_safe()

    @router.post("/privacy/delete")
    async def privacy_delete(request: DeleteRequest) -> dict[str, bool]:
        if request.confirmation != "DELETE MY SIGNALDESK DATA":
            raise HTTPException(status_code=400, detail="confirmation phrase does not match")
        for gmail in list(gmail_connectors.values()):
            try:
                await asyncio.to_thread(gmail.revoke)
            except Exception:
                pass
        database.delete_all_personal_data()
        media_store.clear()
        gmail_connectors.clear()
        replacement = GmailConnector(
            "personal",
            default_credentials,
            draft_scope=default_draft_scope,
            media_store=media_store,
        )
        gmail_connectors["personal"] = replacement
        save_gmail_config(replacement, connected=False)
        persist_gmail_health(replacement)
        bus.publish("data_deleted", {"completed": True})
        return {"deleted": True}

    @router.get("/events/stream")
    async def event_stream(request: Request) -> StreamingResponse:
        async def generate() -> AsyncIterator[str]:
            queue = bus.subscribe()
            try:
                yield 'event: connected\ndata: {"ok":true}\n\n'
                while not await request.is_disconnected():
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=15)
                        yield (
                            f"event: {message['event']}\n"
                            f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                        )
                    except TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                bus.unsubscribe(queue)

        return StreamingResponse(generate(), media_type="text/event-stream")

    app.include_router(router)
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")
    return app


app = create_app()
