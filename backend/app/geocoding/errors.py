"""Errors raised by geocoding provider adapters."""


class GeocodingError(Exception):
    """Base class for expected geocoding failures."""


class GeocodingProviderError(GeocodingError):
    """Base class for failures returned or raised by a provider."""


class GeocodingHTTPError(GeocodingProviderError):
    """The provider returned an HTTP error response."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"geocoding provider returned HTTP {status_code}")
        self.status_code = status_code


class GeocodingTimeoutError(GeocodingProviderError):
    """The provider did not respond before the configured timeout."""


class GeocodingConnectionError(GeocodingProviderError):
    """The provider could not be reached."""


class GeocodingResponseError(GeocodingProviderError):
    """The provider returned an invalid or malformed response."""
