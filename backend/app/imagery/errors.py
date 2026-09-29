"""Errors raised by the NAIP imagery acquisition client."""


class NaipImageryError(Exception):
    """Base class for expected NAIP acquisition failures."""


class NaipHTTPError(NaipImageryError):
    """The ImageServer returned a non-success HTTP status."""

    def __init__(self, status_code: int, detail: str | None = None) -> None:
        message = f"USGS NAIP Plus ImageServer returned HTTP {status_code}"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)
        self.status_code = status_code


class NaipTimeoutError(NaipImageryError):
    """The ImageServer request exceeded its timeout."""


class NaipConnectionError(NaipImageryError):
    """The ImageServer could not be reached."""


class NaipResponseError(NaipImageryError):
    """The ImageServer returned malformed metadata or an invalid raster."""


class NaipAreaTooLargeError(NaipImageryError):
    """The requested bbox exceeds the service's single-export limits."""