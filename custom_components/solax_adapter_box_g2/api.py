"""Read-only client for the local HTTP API of the Adapter Box G2 (spec.md 3).

The box answers an HTTP POST with the form body
`optType=<operation>&pwd=<registration number>` with a JSON object. This
client only knows read operations; write operations such as `setReg` are
deliberately not implemented (spec.md 3e).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import OPT_READ_REALTIME, OPT_READ_SETTINGS, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class SolaxAdapterBoxError(Exception):
    """Base class for all errors of the client (spec.md 8)."""


class CannotConnect(SolaxAdapterBoxError):
    """The box could not be reached, timed out, or answered with an HTTP error."""


class InvalidResponse(SolaxAdapterBoxError):
    """The box answered, but not with the expected JSON object."""


def normalize_host(host: str) -> str:
    """Strip whitespace, a leading `http://` and a trailing `/` (spec.md 4a)."""
    host = host.strip()
    for prefix in ("http://", "https://"):
        if host.lower().startswith(prefix):
            host = host[len(prefix) :]
    return host.rstrip("/")


def serial_number(response: dict[str, Any]) -> str | None:
    """Return the serial number of a response (`sn` or `SN`, spec.md 3b)."""
    value = response.get("sn") or response.get("SN")
    return str(value) if value else None


class SolaxAdapterBoxClient:
    """Send read requests to one Adapter Box G2."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        password: str,
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._host = normalize_host(host)
        self._password = password
        self._timeout = timeout

    @property
    def url(self) -> str:
        """Return the URL of the box."""
        return f"http://{self._host}/"

    async def async_read_realtime(self) -> dict[str, Any]:
        """Read the real-time values; the answer must contain a `Data` list."""
        response = await self._async_post(OPT_READ_REALTIME)
        if not isinstance(response.get("Data"), list):
            raise InvalidResponse(f"{OPT_READ_REALTIME} answer has no Data list")
        return response

    async def async_read_settings(self) -> dict[str, Any]:
        """Read the settings (spec.md 3e); any JSON object is accepted."""
        return await self._async_post(OPT_READ_SETTINGS)

    async def _async_post(self, opt_type: str) -> dict[str, Any]:
        """Send one operation and return the decoded JSON object."""
        # A dict is sent form-encoded, exactly like `curl -d`.
        payload = {"optType": opt_type, "pwd": self._password}
        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.post(self.url, data=payload) as resp:
                    resp.raise_for_status()
                    text = await resp.text()
        except TimeoutError as err:
            raise CannotConnect(f"{opt_type}: timeout after {self._timeout} s") from err
        except aiohttp.ClientError as err:
            raise CannotConnect(f"{opt_type}: {err}") from err

        # The serial number in the answer is the password (spec.md 8).
        _LOGGER.debug(
            "%s answer from %s: %s",
            opt_type,
            self._host,
            text.replace(self._password, "**REDACTED**") if self._password else text,
        )
        try:
            response = json.loads(text)
        except ValueError as err:
            raise InvalidResponse(
                f"{opt_type} answer is not JSON: {text[:100]!r}"
            ) from err
        if not isinstance(response, dict):
            raise InvalidResponse(f"{opt_type} answer is not a JSON object")
        return response
