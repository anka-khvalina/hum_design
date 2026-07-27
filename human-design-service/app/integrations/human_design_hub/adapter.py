from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class HumanDesignHubError(Exception):
    def __init__(self, operation: str, status: int | None, message: str, code: str = "HDHUB_ERROR"):
        super().__init__(message)
        self.operation = operation
        self.status = status
        self.code = code


class HumanDesignProvider(Protocol):
    async def search_locations(self, query: str) -> list[dict[str, Any]]: ...
    async def resolve_timezone(self, timezone: str, date: str, time: str) -> dict[str, Any]: ...
    async def calculate_bodygraph(self, datetime_iso: str) -> dict[str, Any]: ...
    async def generate_bodygraph_image(self, datetime_iso: str) -> bytes | None: ...


class HumanDesignHubAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.hd_hub_base_url.rstrip("/")
        self.api_key = settings.hd_hub_api_key
        self.timeout = settings.hd_hub_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        operation: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        expect_bytes: bool = False,
        retry: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self._headers(),
                        json=json_body,
                        params=params,
                    )
            except httpx.TimeoutException as exc:
                logger.error(
                    '"provider=human_design_hub operation=%s status=timeout attempt=%s"',
                    operation,
                    attempt,
                )
                if retry and attempt == 1:
                    await asyncio.sleep(0.8)
                    continue
                raise HumanDesignHubError(operation, None, "Timeout", "HDHUB_TIMEOUT") from exc
            except httpx.HTTPError as exc:
                logger.error(
                    '"provider=human_design_hub operation=%s status=http_error attempt=%s"',
                    operation,
                    attempt,
                )
                if retry and attempt == 1:
                    await asyncio.sleep(0.8)
                    continue
                raise HumanDesignHubError(operation, None, str(exc), "HDHUB_HTTP_ERROR") from exc

            if response.status_code == 401:
                logger.error('"provider=human_design_hub operation=%s status=401"', operation)
                raise HumanDesignHubError(operation, 401, "Unauthorized", "HDHUB_UNAUTHORIZED")
            if response.status_code == 403:
                logger.error('"provider=human_design_hub operation=%s status=403 code=HDHUB_SUBSCRIPTION_ERROR"', operation)
                raise HumanDesignHubError(operation, 403, "Subscription", "HDHUB_SUBSCRIPTION_ERROR")
            if response.status_code == 429:
                logger.error('"provider=human_design_hub operation=%s status=429"', operation)
                if retry and attempt == 1:
                    await asyncio.sleep(1.2)
                    continue
                raise HumanDesignHubError(operation, 429, "Rate limited", "HDHUB_RATE_LIMIT")
            if response.status_code >= 500:
                logger.error(
                    '"provider=human_design_hub operation=%s status=%s"',
                    operation,
                    response.status_code,
                )
                if retry and attempt == 1:
                    await asyncio.sleep(0.8)
                    continue
                raise HumanDesignHubError(
                    operation, response.status_code, "Server error", "HDHUB_SERVER_ERROR"
                )
            if response.status_code >= 400:
                raise HumanDesignHubError(
                    operation, response.status_code, response.text[:200], "HDHUB_CLIENT_ERROR"
                )

            if expect_bytes:
                content_type = response.headers.get("content-type", "")
                if "image" in content_type or response.content[:8] == b"\x89PNG\r\n\x1a\n":
                    return response.content
                # Some APIs return JSON with base64 — try parse
                try:
                    data = response.json()
                    if isinstance(data, dict) and data.get("image"):
                        import base64

                        return base64.b64decode(data["image"])
                except Exception:
                    pass
                return response.content

            return response.json()

    async def search_locations(self, query: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/v2/locations/search",
            operation="locations_search",
            params={"query": query},
            retry=False,
        )
        results = data.get("results") or data.get("items") or []
        items = []
        for row in results:
            items.append(
                {
                    "id": str(row.get("provider_id") or row.get("id") or f"{row.get('latitude')},{row.get('longitude')}"),
                    "name": row.get("name") or "",
                    "region": row.get("admin1") or row.get("region"),
                    "country": row.get("country") or "",
                    "timezone": row.get("timezone") or "",
                    "latitude": row.get("latitude"),
                    "longitude": row.get("longitude"),
                    "label": row.get("label"),
                }
            )
        return items

    async def resolve_timezone(self, timezone: str, date: str, time: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v2/timezone/resolve",
            operation="timezone_resolve",
            json_body={"timezone": timezone, "date": date, "time": time},
        )

    async def calculate_bodygraph(self, datetime_iso: str) -> dict[str, Any]:
        # Prefer full bodygraph; fall back to simple on Free plan (403)
        try:
            return await self._request(
                "POST",
                "/v2/bodygraph",
                operation="bodygraph",
                json_body={"datetime": datetime_iso, "verbose": True},
            )
        except HumanDesignHubError as exc:
            if exc.status == 403:
                logger.info('"provider=human_design_hub operation=bodygraph fallback=simple-bodygraph"')
                return await self._request(
                    "POST",
                    "/v2/simple-bodygraph",
                    operation="simple_bodygraph",
                    json_body={"datetime": datetime_iso},
                )
            raise

    async def generate_bodygraph_image(self, datetime_iso: str) -> bytes | None:
        try:
            return await self._request(
                "POST",
                "/v2/prompt/bodygraph-image",
                operation="bodygraph_image",
                json_body={"datetime": datetime_iso, "width": 800, "height": 1000},
                expect_bytes=True,
            )
        except HumanDesignHubError as exc:
            if exc.status in (403, 404):
                logger.info('"provider=human_design_hub operation=bodygraph_image unavailable status=%s"', exc.status)
                return None
            raise
