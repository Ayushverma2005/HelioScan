"""Provider-independent geocoding request and result models."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator


class GeoCoordinate(BaseModel):
    """A validated geographic point in WGS84 decimal degrees."""

    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class StructuredAddress(BaseModel):
    """Optional address components accepted by a geocoding provider."""

    model_config = ConfigDict(extra="forbid")

    amenity: str | None = None
    street: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    country: str | None = None
    postalcode: str | None = None

    @field_validator(
        "amenity",
        "street",
        "city",
        "county",
        "state",
        "country",
        "postalcode",
        mode="before",
    )
    @classmethod
    def normalize_component(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("address components must be strings")
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_component(self) -> Self:
        if not any(
            value is not None
            for value in (
                self.amenity,
                self.street,
                self.city,
                self.county,
                self.state,
                self.country,
                self.postalcode,
            )
        ):
            raise ValueError("structured address must contain at least one component")
        return self


class GeocodingSearchRequest(BaseModel):
    """Normalized search input independent of a provider's wire format."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = None
    structured: StructuredAddress | None = None
    limit: int = Field(default=10, ge=1, le=40)

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("query must be a string")
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_one_search_form(self) -> Self:
        if (self.query is None) == (self.structured is None):
            raise ValueError("provide exactly one of query or structured")
        return self


class ProviderMetadata(BaseModel):
    """Attribution and provenance metadata carried with a normalized result."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    attribution: str
    license: str | None = None
    attribution_url: str | None = None
    provider_result_id: str | None = None


class GeocodingCandidate(BaseModel):
    """A normalized geocoding candidate returned to the rest of HelioScan."""

    model_config = ConfigDict(extra="forbid")

    coordinate: GeoCoordinate
    display_name: StrictStr
    address: dict[str, StrictStr] | None = None
    provider_metadata: ProviderMetadata
