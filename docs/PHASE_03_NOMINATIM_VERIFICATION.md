# Phase 3 Provider Verification: Nominatim

**Status:** Verified for initial Phase 3 evaluation
**Date checked:** 2026-09-25

## 1. Provider

The initial Phase 3 geocoding provider is **Nominatim / OpenStreetMap**. This memo covers use of the public service at `nominatim.openstreetmap.org`; it does not document a self-hosted Nominatim instance or another provider.

## 2. Official sources

- Nominatim Search API documentation: https://nominatim.org/release-docs/latest/api/Search/
- Nominatim Usage Policy: https://operations.osmfoundation.org/policies/nominatim/
- OpenStreetMap copyright and license information: https://www.openstreetmap.org/copyright

The usage policy applies specifically to the public server at `nominatim.openstreetmap.org` and may change. The implementation must be reviewed if the policy changes.

## 3. Official search endpoint

The Phase 3 provider endpoint is:

`https://nominatim.openstreetmap.org/search`

The deprecated `search.php` form will not be used.

## 4. Supported search

Nominatim Search supports:

- **Free-form queries** using the `q` parameter, such as an address or POI description.
- **Structured address queries** using address fields such as `amenity`, `street`, `city`, `county`, `state`, `country`, and `postalcode`.
- **Multiple results**, returned as multiple elements in the response array. The caller may request a result limit subject to Nominatim's documented maximum.
- **Zero results**, represented by an empty response array.

The structured form and the `q` parameter must not be combined.

## 5. Response format for HelioScan

HelioScan will request JSON explicitly with:

`format=jsonv2`

The expected top-level response is an array. Each candidate result can contain information such as `display_name`, `lat`, `lon`, address details, and OpenStreetMap identity/licensing fields.

Nominatim returns `lat` and `lon` as strings. The HelioScan backend must validate those fields, convert them to numeric latitude/longitude values, and reject malformed or out-of-range coordinates. The frontend must never invent coordinates or display a pin when validated coordinates are unavailable.

## 6. Request requirements

Every outbound request made by the backend must include:

- A meaningful application-specific HTTP `User-Agent`. A stock HTTP-library User-Agent is not sufficient.
- An appropriate `Referer` when applicable to the deployed application context.
- A finite connect/read timeout so a provider request cannot wait indefinitely.
- Traffic limited to no more than **one request per second per application**, including the combined traffic from all users of that application.

The backend should send only the query and parameters needed for the requested search. Personal, confidential, or unnecessary sensitive information must not be submitted.

## 7. Policy restrictions

The Phase 3 design must comply with the public Nominatim Usage Policy:

- Do not implement client-side autocomplete against the public Nominatim API.
- Do not perform systematic or bulk querying, including grid scans, complete postcode/town lists, or downloading all POIs in an area.
- Do not submit personal data or confidential material to the service.
- The application must be able to switch away from Nominatim if requested or if operational needs change.
- Display OpenStreetMap attribution wherever Nominatim results are shown.
- Keep total application traffic within the documented limit; the one-request-per-second limit applies across all users, not independently per browser.

## 8. Attribution and licensing

User-visible result views must display attribution suitable for the medium, including **OpenStreetMap attribution** and a link to the applicable OpenStreetMap copyright/license information.

Nominatim results identify the underlying data as OpenStreetMap data under the **Open Database License (ODbL)**. Any use, storage, presentation, or later redistribution of result data must be reviewed against the ODbL and the current OpenStreetMap attribution guidance. The application must preserve provider/license metadata where needed to support correct attribution.

## 9. Error cases to handle

The Phase 3 backend must distinguish or safely handle all of the following cases:

- Zero results: return a valid empty-result state; do not create a coordinate or pin.
- Multiple results: return validated candidates so the user can choose among them.
- HTTP 4xx responses: surface a controlled provider/request error without treating the response as a successful geocode.
- HTTP 5xx responses: surface a controlled provider availability error.
- Timeout: stop waiting at the configured timeout and return a controlled failure state.
- Connection failure: return a controlled provider-unavailable state.
- Invalid JSON: reject the body as an invalid provider response.
- Malformed result: reject a result missing required fields or with fields of the wrong shape.
- Invalid latitude/longitude: reject non-numeric, non-finite, or out-of-range values after conversion.

Default automated tests must mock HTTP responses and must not call the live public service.

## 10. Rate-limit strategy

The public Nominatim API will be called only by the Phase 3 backend, never directly by browser clients. The backend will use one centralized per-application rate limiter for all Nominatim requests. Before dispatching a request, that limiter will reserve a slot such that successive outbound requests are at least one second apart. Concurrent searches will wait for an available slot or receive a controlled error rather than bypassing the limit.

The application should cache successful normalized searches where appropriate, so repeated identical user searches do not create repeated provider traffic. The limiter and cache must account for all application instances if the deployment is scaled; separate instance-local limiters must not collectively exceed the application-wide policy limit. Bulk jobs, periodic polling, and automated systematic searches are outside Phase 3 and must not be added as a workaround.

This section documents the intended strategy only. It does not implement the limiter or cache.

## 11. Future autocomplete

Public Nominatim will **not** be used for client-side autocomplete or type-ahead suggestions. If autocomplete or suggested search is added later, it must use a different provider or a different architecture that is explicitly verified for that use. The Phase 3 UI will submit deliberate user searches rather than making a request on every keystroke.

## 12. Provider switching

The rest of HelioScan must depend on an internal geocoding contract, not on Nominatim-specific response fields or request construction. The Phase 3 backend should isolate Nominatim behind a provider adapter/service that:

- accepts the application's normalized search request;
- returns the application's normalized candidate/result model;
- maps provider-specific failures into application-level error categories; and
- keeps provider configuration and selection outside callers such as API routes and frontend code.

This allows a different verified provider or a self-hosted service to be selected through configuration and an adapter without requiring the rest of the application to understand Nominatim. Provider-specific attribution and licensing metadata must remain available to the presentation layer.

## 13. Verification conclusion

Nominatim is suitable as the initial Phase 3 provider only for deliberate, backend-mediated user searches that comply with the public usage policy. It is not approved here for client-side autocomplete, bulk/systematic querying, or unrestricted production-scale traffic. Implementation must preserve provider switching, enforce the documented request limit, validate every response and coordinate, and show OpenStreetMap attribution.
