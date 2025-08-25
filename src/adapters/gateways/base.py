"""
Gateway基底クラスモジュール。

このモジュールでは、すべてのGatewayの基底となるクラスを定義します。
"""

import logging
from abc import ABC
from typing import Any

import httpx


class BaseGateway(ABC):
    """Gateway基底クラス。"""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """初期化。"""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTPクライアント取得。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """HTTPリクエスト実行。"""
        client = await self._get_client()

        for attempt in range(self._max_retries):
            try:
                response = await client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                self._logger.warning(
                    f"HTTP {e.response.status_code} error on attempt {attempt + 1}/{self._max_retries}: {e}"
                )
                if attempt == self._max_retries - 1:
                    raise
            except httpx.RequestError as e:
                self._logger.warning(
                    f"Request error on attempt {attempt + 1}/{self._max_retries}: {e}"
                )
                if attempt == self._max_retries - 1:
                    raise

        # このコードには到達しないが、型チェッカーのために
        raise RuntimeError("Unexpected error in request retry logic")

    async def _get(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """GETリクエスト。"""
        return await self._request("GET", endpoint, **kwargs)

    async def _post(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """POSTリクエスト。"""
        return await self._request("POST", endpoint, **kwargs)

    async def _put(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """PUTリクエスト。"""
        return await self._request("PUT", endpoint, **kwargs)

    async def _delete(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """DELETEリクエスト。"""
        return await self._request("DELETE", endpoint, **kwargs)

    async def close(self) -> None:
        """クライアントをクローズ。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _log_debug(self, message: str, **kwargs: Any) -> None:
        """デバッグログ出力。"""
        self._logger.debug(message, extra=kwargs)

    def _log_info(self, message: str, **kwargs: Any) -> None:
        """情報ログ出力。"""
        self._logger.info(message, extra=kwargs)

    def _log_warning(self, message: str, **kwargs: Any) -> None:
        """警告ログ出力。"""
        self._logger.warning(message, extra=kwargs)

    def _log_error(self, message: str, exception: Exception | None = None, **kwargs: Any) -> None:
        """エラーログ出力。"""
        self._logger.error(message, exc_info=exception, extra=kwargs)
