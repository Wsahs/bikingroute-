# Sidepath — Biking Route

Bicycle route planning for Boca Raton and South Florida, prioritizing sidewalks, trails, designated crossings, and clearly identified street segments.

## Setup status

The existing Sidepath prototype has been transferred into this local repository, including the Python routing service, browser interface, native iPhone project, tests, and source manifests. Large map/address datasets are available locally under `data/` and excluded from Git. Credentials were not copied.

## Run locally

```sh
python3 -m server.app --port 8768
```

Open http://127.0.0.1:8768. For iPhone development, open `ios/Sidepath.xcodeproj` in Xcode. See `README.txt` for features, data attribution, refresh commands, and current limitations; see `SETUP.txt` for infrastructure setup.

Run the existing tests with:

```sh
python3 -m unittest discover -s server/tests -v
```

A fresh GitHub clone will need its map/address datasets collected or restored before local routing works.

Google Maps credentials belong in Supabase Edge Function Secrets under `GOOGLE_MAPS_API_KEY`. Never commit keys, local environment files, or private trip data.

The current prototype includes a Python routing service, a browser interface, and native iPhone source. It is not yet a deployed production navigation app.

## Google Maps website

The default website now uses Google Maps, Google Places text search, and Google Routes cycling directions. It displays route alternatives, estimated time, distance, and Google turn instructions. The previous local sidewalk planner remains at `/experimental.html`; its approach legs and coverage are still unverified.

Set `GOOGLE_MAPS_API_KEY` (server requests) and `GOOGLE_MAPS_BROWSER_KEY` (browser map rendering) in runtime environment variables or a local `.env` file. `.env` is excluded from Git. Browser map keys are visible to the browser by design; use website restrictions on a separate production key. The current local preview uses the existing no-cost Demo Key, which is for prototyping. Google cycling directions do not guarantee sidewalk-only routing.

## Google Maps development setup

Copy `.env.example` to `.env` and configure the two named keys. The browser key
is intentionally browser-visible; the server key is only sent to Google by the
Python service. Use separate appropriately restricted keys for production.
Never commit `.env`. No Google credentials are needed for the automated tests.

The default planner uses Google Places Autocomplete and Place Details, a Google
map, and Google Routes with BICYCLE travel mode. Returned alternatives are sorted
by distance; this does not prove the shortest possible route across all streets.
The demo key is for prototyping and has daily quotas, not production deployment.

Sidewalk/trail routing remains a separate experimental planner. Google cycling
routes do not identify every sidewalk or certify sidewalk-only connectivity.
Street-segment highlighting is available for classified local-network routes;
the Google route is not automatically classified into sidewalks and streets.

The Python server currently runs locally; saving a key in Supabase does not
connect this server to Supabase or deploy it. Native iPhone build verification
and production hosting are still outstanding.

## Sidewalk planner redesign

`/experimental.html` now shares the Google Maps layout and address autocomplete
with the main planner. `/api/sidewalk-trip` checks mapped access candidates within
500 m and tries connected candidate pairs in order of combined approach distance.
The first usable sidewalk route is a suggestion between mapped points, not a
verified door-to-door route. Endpoint approaches are disclosed and never drawn
as invented route segments. Street alternatives require an explicit choice.
This simplifies access selection but does not add sidewalk coverage or implement
independent street-gap combinations.

## Boca connectivity update — October 6, 2026

Refreshed all 9,283 advertised county pedestrian records in the Boca bounds.
The importer now matches county `osm_id` to eligible unrestricted OSM ways and
links endpoints only within one metre. Ambiguous matches are excluded. County
Pathway features require an eligible matching OSM way before inclusion.
The rebuild adds 789 cross-source connections and 87 pathway features, reducing
eligible network components from 1,452 to 1,267. This is a topology improvement,
not a field survey or a guarantee of complete coverage or address access.
See `data/connectivity-update.json` for the measured counts.

Both Google maps now handle trackpad Ctrl+wheel pinch and WebKit gesture events
inside the map. Ordinary gestures remain handled by Google; page zoom outside
the map remains available. Automated gesture tests run with
`node --test web/tests/*.test.cjs`. Physical trackpad/iPhone testing is still needed.
