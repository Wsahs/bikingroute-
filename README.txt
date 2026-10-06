WEBSITE UPDATE — 2026-10-05
The default page now uses Google Maps, Google Places search, and Google cycling
directions. See README.md for current setup. The original local sidewalk planner
is available at /experimental.html. The notes below describe that prototype.

SIDEPATH — FIRST DEVELOPMENT BUILD

Start the local routing service from this directory:
  python3 -m server.app --port 8768
Open http://127.0.0.1:8768 in a browser.

The working browser planner loads the imported Boca Raton and Hollywood networks,
lets you select explicit mapped access points, and computes real connected paths.
The separate web/index.html is the older illustrative design, not live routing.

Native iPhone source:
  Open ios/Sidepath.xcodeproj in Xcode (iOS 17 or newer).
  Select your signing team and an iPhone simulator, then Run.
  The simulator's default routing service is http://127.0.0.1:8768.
  A physical phone needs the Mac's LAN address in the app's Settings and a server
  started with: python3 -m server.app --host 0.0.0.0 --port 8768
  Only expose this unauthenticated development server on a trusted local network.
  Release builds require an HTTPS API; hosting/authentication are not implemented.

Native features implemented in source: Apple MapKit address suggestions, explicit
mapped access-point selection, Boca/Hollywood area selection, sidewalks/trails and
shortest bicycle-permitted road mode, route geometry and segment instructions.

DATA
Hollywood pilot: bbox south25.97 west-80.26 north26.09 east-80.10, including nearby
areas. 36,935 mapped highway ways; 2,888 directed segments pass current conservative
eligibility checks. This is not complete city coverage or a field survey.
Boca pilot and additional county evidence: data/sources/index.html.
OSM attribution: https://www.openstreetmap.org/copyright (ODbL).
Independent GIS evidence is not silently connected to the routing graph.

LIMITS
Not ready for navigation. The native project has NOT been built with an iOS SDK
or run on an iPhone: Xcode and iOS SDKs are absent from this Mac. Swift parsing and
project/plist structure checks passed, which are not compilation or device tests.
The browser searches a local SQLite address index first, with Photon fallback for additional places.
285,149 county address records were downloaded and indexed (145,785 Boca-area;
139,364 Hollywood-area). This is an inventory of source records, not a guarantee
that every real-world address is present. Wrong street suffixes yield clearly
labelled suggestions; selection never silently changes a house number.
After address selection, explicit mapped access confirmation is still required
when address-to-path connectivity has not been verified. Public Photon is a
development dependency; production needs a supported geocoding service.
No address-to-path leg is invented. Instructions currently list named segments,
not fully generated intersection maneuvers. Quiet-road fallback evidence is not
available in the imported pilots. Independent per-gap Yes/No choices remain in
the earlier design demo and still need integration with real alternative routes.
The service retains legacy detour-threshold logic internally; the new independent
choice policy is not yet implemented there. No ride recording.

TESTS
  python3 -m unittest discover -s server/tests -v
81 tests pass. Live HTTP smoke tests exercised both real datasets, their maps,
access-point lookup, and nonempty routes. Frontend JS syntax and native Swift
syntax were checked. Browser autocomplete was verified against the reported address. Native-device QA remains outstanding.

DATA REFRESH
  python3 -m server.collect_addresses boca
  python3 -m server.collect_addresses hollywood
  python3 -m server.evidence
Address collectors verify every advertised object ID and retain source manifests.
County GIS evidence is indexed separately from routing topology. Amber map lines
show existing sidewalk evidence, not verified cycling directions.
Conventional-bicycle defaults apply to mapped sidewalks and designated crossings
within reviewed Boca/unincorporated Palm Beach pilot bounds; explicit bans,
private access, conditional rules and barriers still take precedence.
Hollywood unknown sidewalk permissions remain excluded pending business-district
restriction mapping. See server/jurisdictions.py and source municipal polygons.

Expanded Boca routing bounds: south 26.32, west -80.245, north 26.43, east -80.055.
Rebuild with python3 -m server.rebuild_boca after collecting sources.
Existing county sidewalk/shared-use centerlines and marked crossings are imported
with source-coordinate connectivity only. Proposed facilities and unmarked
crossings are excluded; independent county/OSM layers are not arbitrarily snapped.

BOCA CONNECTION REVIEW — 2026-10-01
Driveway crossings now preserve sidewalk continuity when shared OSM nodes show a
short crossing of service roads, with sidewalks at both ends and no shared road
segment. Explicit access/bicycle bans still override this rule. Pedestrian refuge
islands now preserve eligible crossing continuity. Ordinary unmarked road crossings
remain excluded. Four driveway crossings were individually checked against county
2026 aerial imagery; the generalized rule is not a field survey of every driveway.

Run python3 -m server.audit_boca after rebuilding the graph. The review database
(data/boca-review.sqlite) inventories all 34,299 imported highway ways and retains
unresolved crossing/access/road review categories. See data/boca-review-summary.json.
The live map now offers Palm Beach County 2026 aerial imagery for inspecting the
physical network. Imagery is evidence of pavement, not proof of cycling permission.
Address-to-path distances are straight-line distances, not accessible approach legs;
water, fences and other barriers may intervene. The reported trip has a connected
13,779 m route between selected mapped access points, but its address approach legs
remain unverified. It must not be presented as a completed door-to-door route.

NAMED DIRECTIONS AND ROUTE DISPLAY — 2026-10-01
The official Palm Beach County road-centerline inventory now contains 9,873
records in the expanded Boca bounds. Route directions use those street names as
explicitly inferred nearby-road context: parallel roads within 40 m, with ambiguous
matches left unnamed. Crossings name a road only when their geometry intersects
its centerline. This does not add connections or certify physical conditions.
Turn instructions are computed from route geometry; they are not Apple directions.
Tap a direction to inspect that section on the map. The selected route is blue;
street-riding pieces are red on their real geometry. Mapping evidence is optional.
An Apple Maps link opens a separate cycling route for the selected addresses.
It does not export Sidepath's sidewalk route. Embedded Apple Maps/data is not
connected: this requires an Apple Developer Maps token. No Apple map data was
scraped or stored. See https://developer.apple.com/documentation/mapkitjs/creating-a-maps-token

GOOGLE MAPS PROVIDER CHOICE
The external cycling-directions button now opens Google Maps with the selected
origin and destination using its documented Maps URLs API (no key required).
This opens Google's own route, not the sidewalk-only route computed locally.
Embedded Google Maps is not active: a Google Maps JavaScript API key is required.
Google offers a no-cost Demo Key for prototyping without billing information:
https://developers.google.com/maps/documentation/javascript/demo-key
Production setup: https://developers.google.com/maps/documentation/javascript/get-api-key
