from __future__ import annotations

import time

from fastapi.testclient import TestClient

from signaldesk.api import create_app


def test_api_requires_local_session(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        assert client.get("/api/v1/bootstrap").status_code == 401
        root = client.get("/")
        assert root.status_code == 200
        response = client.get("/api/v1/bootstrap")
        assert response.status_code == 200
        assert response.json()["privacy"]["auto_send"] is False


def test_windows_bridge_and_no_send_endpoint(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "toast-1",
                "app_id": "LINE",
                "app_name": "LINE",
                "title": "實驗室群組",
                "body": "你可以參加明天的會議嗎？",
                "received_at": "2026-08-02T18:00:00+08:00",
            },
        )
        assert response.status_code == 201
        assert response.json()["accepted"] is True
        assert client.post("/api/v1/send", json={}).status_code == 404


def test_windows_bridge_reports_native_permission_status(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        denied = client.post(
            "/api/v1/connectors/windows/status",
            json={"status": "denied"},
        )
        assert denied.status_code == 200
        assert denied.json()["status"] == "denied"

        allowed = client.post(
            "/api/v1/connectors/windows/status",
            json={"status": "allowed"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["status"] == "healthy"
        connector = next(
            item
            for item in client.get("/api/v1/connectors").json()["items"]
            if item["connector_id"] == "windows-notifications"
        )
        assert connector["status"] == "healthy"


def test_latest_view_orders_by_recency_instead_of_priority(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        older = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "older-urgent",
                "app_id": "LINE",
                "app_name": "LINE",
                "title": "安全警示",
                "body": "緊急：帳號安全異常，請立即處理。",
                "received_at": "2026-08-03T08:00:00+08:00",
            },
        )
        assert older.status_code == 201
        time.sleep(0.002)
        newer = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "newer-normal",
                "app_id": "Messenger",
                "app_name": "Messenger",
                "title": "朋友",
                "body": "收到，謝謝。",
                "received_at": "2026-08-03T08:01:00+08:00",
            },
        )
        assert newer.status_code == 201

        items = client.get("/api/v1/cards", params={"view": "latest"}).json()["items"]
        assert items[0]["source"] == "messenger_notification"
        assert items[1]["source"] == "line_notification"


def test_windows_bridge_accepts_updated_toast_with_reused_notification_id(
    test_config, database
):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        first = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "line-conversation-stable-id",
                "app_id": "LINE",
                "app_name": "LINE",
                "title": "朋友",
                "body": "第一則測試訊息",
                "received_at": "2026-08-03T08:25:00+08:00",
            },
        )
        second = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "line-conversation-stable-id",
                "app_id": "LINE",
                "app_name": "LINE",
                "title": "朋友",
                "body": "第二則測試訊息",
                "received_at": "2026-08-03T08:27:00+08:00",
            },
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["duplicate"] is False
        assert second.json()["duplicate"] is False
        card_id = second.json()["card_id"]
        detail = client.get(f"/api/v1/cards/{card_id}").json()
        assert [event["content"] for event in detail["events"]] == [
            "第一則測試訊息",
            "第二則測試訊息",
        ]


def test_windows_bridge_ignores_browser_background_status(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "edge-background-status",
                "app_id": "Microsoft.MicrosoftEdge.Stable",
                "app_name": "Microsoft Edge",
                "title": "www.messenger.com",
                "body": "3 則同一對話訊息：這個網站已在背景更新。",
                "origin": "www.messenger.com",
                "received_at": "2026-08-03T08:28:00+08:00",
            },
        )

        assert response.status_code == 201
        assert response.json() == {
            "accepted": False,
            "reason": "browser_background_status",
        }
        items = client.get(
            "/api/v1/cards", params={"source": "messenger_notification"}
        ).json()["items"]
        assert items == []


def test_browser_messenger_notification_uses_title_and_preview_sender(
    test_config, database
):
    database.update_settings(
        {"notification_allowlist": ["LINE", "Messenger", "Google Chrome", "Edge"]}
    )
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "chrome-messenger-photo",
                "app_id": "Chrome",
                "app_name": "Google Chrome",
                "title": "Messenger",
                "body": "Meta AI 傳送了 1 張相片。",
                "received_at": "2026-08-03T08:37:18+08:00",
            },
        )

        assert response.status_code == 201
        card = client.get(f"/api/v1/cards/{response.json()['card_id']}").json()
        assert card["source"] == "messenger_notification"
        assert card["sender"] == "Meta AI"
        assert card["events"][0]["conversation_id"] == "Meta AI"
        assert card["events"][0]["source_url"] == "https://www.messenger.com/"


def test_today_filter_converts_utc_card_time_to_local_date(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        response = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "line-before-utc-midnight",
                "app_id": "LINE",
                "app_name": "LINE",
                "title": "朋友",
                "body": "早安",
                "received_at": "2026-08-03T07:41:00+08:00",
            },
        )
        card_id = response.json()["card_id"]
        with database.transaction() as connection:
            connection.execute(
                "UPDATE notification_cards SET updated_at=? WHERE card_id=?",
                ("2026-08-02T23:41:00+00:00", card_id),
            )

        items = client.get(
            "/api/v1/cards",
            params={"source": "line_notification", "date": "today"},
        ).json()["items"]
        assert [item["card_id"] for item in items] == [card_id]


def test_reconciled_and_live_line_snapshots_are_deduplicated(
    test_config, database
):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        base = {
            "app_id": "LINE",
            "app_name": "LINE",
            "title": "朋友",
            "body": "同一則文字",
        }
        first = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                **base,
                "notification_id": "line-live-1",
                "received_at": "2026-08-03T07:20:00+08:00",
                "metadata": {"capture_reason": "live"},
            },
        ).json()
        replay = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                **base,
                "notification_id": "line-replay-new-id",
                "received_at": "2026-08-03T08:40:00+08:00",
                "metadata": {"capture_reason": "startup_reconcile"},
            },
        ).json()
        live_repeat = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                **base,
                "notification_id": "line-live-2",
                "received_at": "2026-08-03T08:41:00+08:00",
                "metadata": {"capture_reason": "live"},
            },
        ).json()

        assert replay["duplicate"] is True
        assert replay["card_id"] == first["card_id"]
        assert live_repeat["duplicate"] is True
        detail = client.get(f"/api/v1/cards/{first['card_id']}").json()
        assert len(detail["events"]) == 1


def test_line_group_notifications_keep_each_visible_user_in_a_separate_card(
    test_config, database
):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        first = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "line-alice",
                "app_id": "NAVER.WIN32_LINEwin8_8ptj331gd3tyt!LINE",
                "app_name": "LINE",
                "title": "小明 [旅遊群]",
                "body": "圖片已傳送",
                "received_at": "2026-08-03T08:20:00+08:00",
                "metadata": {"capture_reason": "live"},
            },
        ).json()
        second = client.post(
            "/api/v1/connectors/windows/notifications",
            json={
                "notification_id": "line-bob",
                "app_id": "NAVER.WIN32_LINEwin8_8ptj331gd3tyt!LINE",
                "app_name": "LINE",
                "title": "小華 [旅遊群]",
                "body": "圖片已傳送",
                "received_at": "2026-08-03T08:21:00+08:00",
                "metadata": {"capture_reason": "live"},
            },
        ).json()

        assert first["card_id"] != second["card_id"]
        first_detail = client.get(f"/api/v1/cards/{first['card_id']}").json()
        second_detail = client.get(f"/api/v1/cards/{second['card_id']}").json()
        assert first_detail["sender"] == "小明"
        assert second_detail["sender"] == "小華"
        assert first_detail["title"] == second_detail["title"] == "旅遊群"


def test_delete_requires_exact_confirmation(test_config, database):
    with TestClient(create_app(test_config, database)) as client:
        client.get("/")
        rejected = client.post("/api/v1/privacy/delete", json={"confirmation": "delete"})
        assert rejected.status_code == 400
        accepted = client.post(
            "/api/v1/privacy/delete", json={"confirmation": "DELETE MY SIGNALDESK DATA"}
        )
        assert accepted.status_code == 200
