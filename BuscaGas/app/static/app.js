const $ = (s) => document.querySelector(s);
const state = { origin: null, destination: null, markers: new Map(), routeExtent: null };
let map, routeSource, stationsSource, endpointsSource, popupOverlay;

function debounce(fn, delay = 350) { let timer; return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); }; }
function formatNumber(value, digits = 1) { return Number(value).toLocaleString("es-ES", { minimumFractionDigits: digits, maximumFractionDigits: digits }); }
function duration(minutes) { const hours = Math.floor(minutes / 60); const mins = Math.round(minutes % 60); return hours ? `${hours} h ${mins} min` : `${mins} min`; }

function markerStyle(feature) {
  const kind = feature.get("kind"); const station = kind === "station";
  const color = kind === "origin" ? "#176b4c" : kind === "destination" ? "#d04436" : "#d4ef45";
  return new ol.style.Style({
    image: new ol.style.Circle({ radius: station ? 13 : 17, fill: new ol.style.Fill({ color }), stroke: new ol.style.Stroke({ color: station ? "#152820" : "#fff", width: station ? 2 : 4 }) }),
    text: new ol.style.Text({ text: String(feature.get("label")), font: `800 ${station ? 11 : 13}px system-ui`, fill: new ol.style.Fill({ color: station ? "#152820" : "#fff" }) })
  });
}

function initializeMap() {
  if (map) return;
  routeSource = new ol.source.Vector(); stationsSource = new ol.source.Vector(); endpointsSource = new ol.source.Vector();
  const popup = document.createElement("div"); popup.className = "map-popup"; $(".map-wrap").append(popup);
  popupOverlay = new ol.Overlay({ element: popup, positioning: "bottom-center", offset: [0, -18], stopEvent: false });
  map = new ol.Map({ target: "map", overlays: [popupOverlay], layers: [
    new ol.layer.Tile({ source: new ol.source.OSM({ crossOrigin: "anonymous" }) }),
    new ol.layer.Vector({ source: routeSource, style: [new ol.style.Style({ stroke: new ol.style.Stroke({ color: "#fff", width: 12 }) }), new ol.style.Style({ stroke: new ol.style.Stroke({ color: "#1769e0", width: 7 }) })] }),
    new ol.layer.Vector({ source: stationsSource, style: markerStyle }), new ol.layer.Vector({ source: endpointsSource, style: markerStyle })
  ], view: new ol.View({ center: ol.proj.fromLonLat([-3.7, 40.2]), zoom: 6 }) });
  map.on("singleclick", (event) => { const feature = map.forEachFeatureAtPixel(event.pixel, (item) => item); if (feature?.get("kind") === "station") showPopup(feature); else popupOverlay.setPosition(undefined); });
  map.on("pointermove", (event) => { map.getTargetElement().style.cursor = map.hasFeatureAtPixel(event.pixel) ? "pointer" : ""; });
}

function showPopup(feature) {
  const station = feature.get("station"); const popup = popupOverlay.getElement(); popup.replaceChildren();
  const name = document.createElement("strong"); name.textContent = station.name;
  const price = document.createElement("span"); price.textContent = `${formatNumber(station.price, 3)} €/L`;
  const detail = document.createElement("small"); detail.textContent = `+${formatNumber(station.detour_minutes)} min · ${station.address}`;
  popup.append(name, price, detail); popupOverlay.setPosition(feature.getGeometry().getCoordinates());
}

function setupAutocomplete(name) {
  const input = $(`#${name}`), box = $(`#${name}-results`);
  input.addEventListener("input", debounce(async () => {
    state[name] = null; box.replaceChildren(); if (input.value.trim().length < 2) return;
    try { const response = await fetch(`api/geocode?q=${encodeURIComponent(input.value.trim())}`); const data = await response.json(); if (!response.ok) throw new Error(data.detail);
      data.results.forEach((result) => { const button = document.createElement("button"); button.type = "button"; button.textContent = result.label; button.addEventListener("click", () => { state[name] = result; input.value = result.label; box.replaceChildren(); }); box.append(button); });
    } catch (error) { box.textContent = error.message || "No se pudieron cargar sugerencias"; }
  }));
  document.addEventListener("click", (event) => { if (!box.parentElement.contains(event.target)) box.replaceChildren(); });
}
setupAutocomplete("origin"); setupAutocomplete("destination");
$("#detour").addEventListener("input", (event) => { $("#detour-value").textContent = `${event.target.value} ${event.target.value === "1" ? "minuto" : "minutos"}`; });
$(".swap").addEventListener("click", () => { [state.origin, state.destination] = [state.destination, state.origin]; const value = $("#origin").value; $("#origin").value = $("#destination").value; $("#destination").value = value; });

async function resolveLocation(name) {
  if (state[name]) return state[name]; const query = $(`#${name}`).value.trim();
  const response = await fetch(`api/geocode?q=${encodeURIComponent(query)}`), data = await response.json();
  if (!response.ok || !data.results?.length) throw new Error(`No hemos encontrado ${name === "origin" ? "el origen" : "el destino"}.`);
  state[name] = data.results[0]; return state[name];
}

function pointFeature(location, kind, label, station = null) {
  const feature = new ol.Feature(new ol.geom.Point(ol.proj.fromLonLat([location.longitude, location.latitude]))); feature.setProperties({ kind, label, station }); return feature;
}

function render(data) {
  $("#summary").classList.remove("hidden"); $("#results-layout").classList.remove("hidden"); initializeMap(); map.updateSize();
  $("#summary").replaceChildren(); const title = document.createElement("strong"); title.textContent = `Ruta: ${state.origin.label} → ${state.destination.label}`; const detail = document.createElement("span"); detail.textContent = `${formatNumber(data.route.distance_km, 0)} km · ${duration(data.route.duration_minutes)}`; $("#summary").append(title, detail); $("#count").textContent = `${data.stations.length} resultados`;
  routeSource.clear(); stationsSource.clear(); endpointsSource.clear(); state.markers.clear(); popupOverlay.setPosition(undefined);
  const route = new ol.format.GeoJSON().readFeature({ type: "Feature", properties: {}, geometry: data.route.geometry }, { dataProjection: "EPSG:4326", featureProjection: "EPSG:3857" }); routeSource.addFeature(route); state.routeExtent = route.getGeometry().getExtent();
  endpointsSource.addFeatures([pointFeature(state.origin, "origin", "A"), pointFeature(state.destination, "destination", "B")]);
  const list = $("#stations"); list.replaceChildren();
  if (!data.stations.length) { const empty = document.createElement("div"); empty.className = "empty"; empty.textContent = `No hemos encontrado gasolineras alcanzables con ${$("#autonomy").value} km de autonomía y un desvío máximo de ${$("#detour").value} minutos.`; list.append(empty); }
  data.stations.forEach((station, index) => {
    const feature = pointFeature(station, "station", index + 1, station); stationsSource.addFeature(feature); state.markers.set(station.id, feature);
    const card = document.createElement("article"); card.className = "station-card"; card.tabIndex = 0; const top = document.createElement("div"); top.className = "station-top";
    const identity = document.createElement("div"); identity.innerHTML = `<span class="rank">#${index + 1}</span>`; const name = document.createElement("h3"); name.textContent = station.name; identity.append(name); const price = document.createElement("div"); price.className = "price"; price.textContent = `${formatNumber(station.price, 3)} €/L`; top.append(identity, price);
    const reach = document.createElement("div"); reach.className = "reach"; reach.textContent = `A ${formatNumber(station.distance_from_origin_km, 0)} km del origen`; const metrics = document.createElement("div"); metrics.className = "metrics"; metrics.textContent = `Desvío: +${formatNumber(station.detour_minutes)} min · +${formatNumber(station.extra_distance_km)} km`; const address = document.createElement("p"); address.textContent = [station.address, station.municipality, station.province].filter(Boolean).join(" · "); card.append(top, reach, metrics, address);
    const select = () => { document.querySelectorAll(".station-card.selected").forEach((item) => item.classList.remove("selected")); card.classList.add("selected"); showPopup(feature); map.getView().animate({ center: feature.getGeometry().getCoordinates(), zoom: 13, duration: 500 }); };
    card.addEventListener("click", select); card.addEventListener("keydown", (event) => { if (event.key === "Enter") select(); }); list.append(card);
  });
  requestAnimationFrame(() => { map.updateSize(); map.getView().fit(state.routeExtent, { padding: [55, 55, 55, 55], maxZoom: 13, duration: 350 }); });
}

$("#reset-map").addEventListener("click", () => { if (map && state.routeExtent) map.getView().fit(state.routeExtent, { padding: [55, 55, 55, 55], maxZoom: 13, duration: 350 }); });
$("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const button = $("#submit"); button.disabled = true; button.textContent = "Buscando las mejores gasolineras…"; $("#status").className = "loading"; $("#status").textContent = "Calculando ruta y comparando precios reales…";
  try { const [origin, destination] = await Promise.all([resolveLocation("origin"), resolveLocation("destination")]); const response = await fetch("api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin, destination, fuel_type: $("#fuel").value, max_detour_minutes: Number($("#detour").value), autonomy_km: Number($("#autonomy").value) }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || "No se ha podido calcular la ruta."); render(data); $("#status").textContent = ""; $("#status").className = ""; }
  catch (error) { $("#status").className = "error"; $("#status").textContent = error.message || "No se ha podido calcular la ruta."; }
  finally { button.disabled = false; button.innerHTML = "Buscar gasolineras <span>→</span>"; }
});
