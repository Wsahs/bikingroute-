import SwiftUI
import MapKit

@main struct SidepathApp: App {
    var body: some Scene { WindowGroup { PlannerView() } }
}
struct AccessPoint: Codable, Identifiable { let id: String; let lat: Double; let lon: Double; let name: String; let distance_m: Double }
struct AccessResponse: Codable { let points: [AccessPoint]; let warning: String }
struct Segment: Codable, Identifiable { let id: String; let kind: String; let name: String; let distance_m: Double; let geometry: [[Double]] }
struct RideRoute: Codable { let distance_m: Double; let duration_seconds: Double; let street_distance_m: Double; let segments: [Segment] }
struct RouteResponse: Codable { let status: String; let primary: RideRoute?; let alternative: RideRoute?; let warnings: [String] }
struct APIError: LocalizedError { let message: String; var errorDescription: String? { message } }

@MainActor final class AddressSearch: NSObject, ObservableObject, MKLocalSearchCompleterDelegate {
    @Published var results: [MKLocalSearchCompletion] = []
    let completer = MKLocalSearchCompleter()
    override init() { super.init(); completer.delegate = self; completer.resultTypes = [.address, .pointOfInterest]; setArea("boca") }
    func setArea(_ region: String) { completer.region = MKCoordinateRegion(center: CLLocationCoordinate2D(latitude: region == "boca" ? 26.375 : 26.025, longitude: region == "boca" ? -80.12 : -80.16), span: MKCoordinateSpan(latitudeDelta: 0.16, longitudeDelta: 0.2)) }
    func update(_ text: String) { completer.queryFragment = text; if text.isEmpty { results = [] } }
    func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) { results = Array(completer.results.prefix(6)) }
    func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) { results = [] }
}

@MainActor final class Planner: ObservableObject {
    @Published var region = "boca"
    @Published var mode = "sidewalk"
    @Published var start: AccessPoint?
    @Published var end: AccessPoint?
    @Published var access: [AccessPoint] = []
    @Published var route: RideRoute?
    @Published var message = "Choose addresses, then confirm mapped access points. Coverage is incomplete."
    @Published var busy = false
    @Published var focus: CLLocationCoordinate2D?
    private var requestID = UUID()
    func editAddress(start isStart: Bool) { requestID = UUID(); busy = false; access = []; route = nil; if isStart { start = nil } else { end = nil } }
    func invalidate() { requestID = UUID(); busy = false; route = nil; access = []; start = nil; end = nil }
    func request<T: Decodable>(_ path: String, base: String, body: [String:String]? = nil) async throws -> T {
        guard let url = URL(string: base + path), ["http", "https"].contains(url.scheme ?? "") else { throw APIError(message: "Enter the routing server URL in Settings.") }
        #if !DEBUG
        guard url.scheme == "https" else { throw APIError(message: "Production requires an HTTPS routing service.") }
        #endif
        var req = URLRequest(url: url); req.timeoutInterval = 30
        if let body { req.httpMethod = "POST"; req.setValue("application/json", forHTTPHeaderField: "Content-Type"); req.httpBody = try JSONSerialization.data(withJSONObject: body) }
        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            let json = (try? JSONSerialization.jsonObject(with: data)) as? [String:Any]
            throw APIError(message: json?["error"] as? String ?? "The routing service is unavailable.")
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
    func findAccess(_ item: MKLocalSearchCompletion, base: String) async {
        let id = UUID(); requestID = id; busy = true; access = []; route = nil
        defer { if requestID == id { busy = false } }
        do {
            let response = try await MKLocalSearch(request: MKLocalSearch.Request(completion: item)).start()
            guard requestID == id, let place = response.mapItems.first else { return }
            let p = place.placemark.coordinate
            let result: AccessResponse = try await request("/api/access?dataset=\(region)&lat=\(p.latitude)&lon=\(p.longitude)&mode=\(mode)", base: base)
            guard requestID == id else { return }
            focus = p; access = result.points; message = access.isEmpty ? "No assessed path access within 500 metres. A real connection may be missing from the map." : result.warning
        } catch { if requestID == id { message = error.localizedDescription } }
    }
    func calculate(base: String) async {
        guard let start, let end else { return }
        let id = UUID(); requestID = id; busy = true; route = nil
        defer { if requestID == id { busy = false } }
        do {
            let result: RouteResponse = try await request("/api/route", base: base, body: ["dataset":region,"mode":mode,"start":start.id,"end":end.id])
            guard requestID == id else { return }
            route = result.primary
            message = result.primary == nil ? "No continuous route found in the assessed network. This does not prove no sidewalk route exists." : "Mapped route between the access points. Address-to-path connections are not included."
            if result.alternative != nil { message += " Street alternatives still require the per-connection review flow; they have not been selected." }
        } catch { if requestID == id { message = error.localizedDescription } }
    }
}

struct PlannerView: View {
    @StateObject private var model = Planner()
    @StateObject private var search = AddressSearch()
    @AppStorage("serverURL") private var serverURL = "http://127.0.0.1:8768"
    @State private var startText = ""
    @State private var endText = ""
    @State private var editingStart = true
    @State private var settings = false
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text("Early development · Not ready for navigation").font(.caption).foregroundStyle(.secondary)
                    Picker("Area", selection: $model.region) { Text("Boca Raton").tag("boca"); Text("Hollywood").tag("hollywood") }.pickerStyle(.segmented)
                    RouteMap(route: model.route, focus: model.focus, region: model.region).frame(height: 310).clipShape(RoundedRectangle(cornerRadius: 16))
                    TextField("Start address", text: $startText).textFieldStyle(.roundedBorder).onChange(of: startText) { _, text in editingStart = true; model.editAddress(start: true); search.update(text) }
                    TextField("Destination", text: $endText).textFieldStyle(.roundedBorder).onChange(of: endText) { _, text in editingStart = false; model.editAddress(start: false); search.update(text) }
                    ForEach(Array(search.results.enumerated()), id: \.offset) { _, result in
                        Button { search.results = []; Task { await model.findAccess(result, base: serverURL) } } label: { VStack(alignment: .leading) { Text(result.title); Text(result.subtitle).font(.caption).foregroundStyle(.secondary) } }.buttonStyle(.borderless)
                    }
                    if !model.access.isEmpty { Text("Confirm a mapped access point").font(.headline) }
                    ForEach(model.access) { point in
                        Button("\(point.name) · \(Int(point.distance_m)) m straight-line") {
                            if editingStart { model.start = point } else { model.end = point }; model.access = []; model.focus = CLLocationCoordinate2D(latitude: point.lat, longitude: point.lon)
                        }.buttonStyle(.bordered)
                    }
                    if let p = model.start { Label("Start access: \(p.name)", systemImage: "a.circle") }
                    if let p = model.end { Label("Destination access: \(p.name)", systemImage: "b.circle") }
                    Picker("Road preference", selection: $model.mode) { Text("Sidewalks & trails").tag("sidewalk"); Text("Bike roads are fine").tag("bicycle") }.pickerStyle(.segmented)
                    Button("Let’s continue") { Task { await model.calculate(base: serverURL) } }.buttonStyle(.borderedProminent).disabled(model.start == nil || model.end == nil || model.busy)
                    if model.busy { ProgressView("Searching…") }
                    Text(model.message).font(.callout).accessibilityAddTraits(.updatesFrequently)
                    if let route = model.route {
                        Text(String(format: "%.2f mi · %.0f min · %.2f mi on streets", route.distance_m/1609.344, route.duration_seconds/60, route.street_distance_m/1609.344)).font(.headline)
                        Text("Directions between mapped access points").font(.headline)
                        ForEach(route.segments) { segment in HStack { Image(systemName: segment.kind == "street" ? "car" : "bicycle"); Text("\(segment.name) · \(Int(segment.distance_m)) m") }.foregroundStyle(segment.kind == "street" ? .red : .primary) }
                    }
                }.padding()
            }.navigationTitle("Sidepath").tint(Color(red: 0.12, green: 0.38, blue: 0.25))
                .toolbar { Button("Settings", systemImage: "gear") { settings = true } }
                .sheet(isPresented: $settings) { NavigationStack { Form { TextField("Routing server URL", text: $serverURL).textInputAutocapitalization(.never).autocorrectionDisabled(); Text("On an iPhone, enter your Mac’s LAN address on the same Wi-Fi. Run the development server with --host 0.0.0.0. The app does not run a routing server itself.") }.navigationTitle("Development server").toolbar { Button("Done") { settings = false; model.invalidate() } } } }
                .onChange(of: model.region) { _, region in model.invalidate(); search.setArea(region); search.results = [] }
                .onChange(of: model.mode) { _, _ in model.invalidate() }
        }
    }
}

struct RouteMap: UIViewRepresentable {
    let route: RideRoute?
    let focus: CLLocationCoordinate2D?
    let region: String
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeUIView(context: Context) -> MKMapView { let map = MKMapView(); map.delegate = context.coordinator; return map }
    func updateUIView(_ map: MKMapView, context: Context) {
        let key = (route?.segments.map(\.id).joined(separator: ",") ?? "") + region
        if context.coordinator.key != key {
            context.coordinator.key = key; map.removeOverlays(map.overlays)
            for segment in route?.segments ?? [] {
                let coordinates = segment.geometry.filter { $0.count >= 2 }.map { CLLocationCoordinate2D(latitude: $0[1], longitude: $0[0]) }
                let line = MKPolyline(coordinates: coordinates, count: coordinates.count); line.title = segment.kind; map.addOverlay(line)
            }
            if !map.overlays.isEmpty { let rect = map.overlays.reduce(MKMapRect.null) { $0.union($1.boundingMapRect) }; map.setVisibleMapRect(rect, edgePadding: UIEdgeInsets(top: 35, left: 35, bottom: 35, right: 35), animated: false) }
            else { map.setRegion(MKCoordinateRegion(center: CLLocationCoordinate2D(latitude: region == "boca" ? 26.375 : 26.025, longitude: region == "boca" ? -80.12 : -80.16), span: MKCoordinateSpan(latitudeDelta: 0.06, longitudeDelta: 0.06)), animated: false) }
        }
        if let focus, route == nil, context.coordinator.lastFocus != "\(focus.latitude),\(focus.longitude)" { context.coordinator.lastFocus = "\(focus.latitude),\(focus.longitude)"; map.setCenter(focus, animated: false) }
    }
    final class Coordinator: NSObject, MKMapViewDelegate {
        var key: String?; var lastFocus: String?
        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            guard let line = overlay as? MKPolyline else { return MKOverlayRenderer(overlay: overlay) }
            let renderer = MKPolylineRenderer(polyline: line); renderer.strokeColor = line.title == "street" ? .systemRed : .systemGreen; renderer.lineWidth = 6; return renderer
        }
    }
}
