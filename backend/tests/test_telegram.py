import asyncio

from app.services.alerts.telegram import send_telegram_message


class _FakeResponse:
    status_code = 200
    headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        return None


def test_send_telegram_uses_proxy_and_timeout(monkeypatch):
    instances: list[object] = []

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.posts = []
            instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            self.posts.append((url, json))
            return _FakeResponse()

    monkeypatch.setattr("app.services.alerts.telegram.httpx.AsyncClient", FakeAsyncClient)

    asyncio.run(
        send_telegram_message(
            "token",
            "chat",
            "hello",
            proxy_url=" http://127.0.0.1:7890 ",
            timeout_seconds=7.5,
        )
    )

    assert len(instances) == 1
    client = instances[0]
    assert client.kwargs["proxy"] == "http://127.0.0.1:7890"
    assert client.kwargs["timeout"] == 7.5
    assert client.posts[0][1]["text"] == "hello"
