/* Ukulima outbreak map — Kenya ONLY.
   No tile layer is used: the country is drawn from its 47 county boundaries
   (geoBoundaries, CC BY 4.0), so no neighbouring country can ever appear.
   Pins + heatmap + trend chart work exactly as before, on top of the counties. */
(function () {
  "use strict";
  if (typeof L === "undefined") return;

  var I18N = window.MAP_I18N || { reports: "reports", high: "high severity", top: "Most reported", none: "No reports in this period." };
  var SEV_COLOR = { low: "#2f8a5b", medium: "#e0a32e", high: "#c1553a" };
  var KENYA = L.latLngBounds([-4.8, 33.8], [5.1, 42.0]);

  var map = L.map("map", {
    scrollWheelZoom: false,
    maxBounds: KENYA.pad(0.06),
    maxBoundsViscosity: 1.0,
    minZoom: 6,
    maxZoom: 12,
    zoomControl: false,
    attributionControl: true
  });
  map.fitBounds(KENYA);
  map.attributionControl.setPrefix(false);
  map.attributionControl.addAttribution('Boundaries: <a href="https://www.geoboundaries.org" target="_blank" rel="noopener">geoBoundaries</a> (CC BY 4.0)');

  var pinLayer = L.layerGroup().addTo(map);
  var labelLayer = L.layerGroup();
  var geoLayer = null;
  var heatLayer = null;
  var showHeat = true, showPins = true, showLabels = false;
  var heatData = [];           // [{county, n, high}]
  var rows = [];               // current filtered reports
  var selected = null;         // selected county name

  var cropFilter = document.getElementById("cropFilter");
  var daysFilter = document.getElementById("daysFilter");
  var fillMode = document.getElementById("fillMode");
  var trendCtx = document.getElementById("trendChart");
  var trendChart = null;
  var card = document.getElementById("countyCard");

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function norm(s) { return String(s).toLowerCase().replace(/[^a-z0-9]/g, ""); }

  /* ---- choropleth ---- */
  var RAMP = [[233, 240, 221], [242, 217, 154], [232, 163, 60], [193, 85, 58], [124, 26, 16]];
  function rampColor(t) {
    t = Math.max(0, Math.min(1, t));
    var x = t * (RAMP.length - 1), i = Math.min(Math.floor(x), RAMP.length - 2), f = x - i;
    var a = RAMP[i], b = RAMP[i + 1];
    return "rgb(" + Math.round(a[0] + (b[0] - a[0]) * f) + "," +
                    Math.round(a[1] + (b[1] - a[1]) * f) + "," +
                    Math.round(a[2] + (b[2] - a[2]) * f) + ")";
  }
  function countyStat(name) {
    var key = norm(name);
    for (var i = 0; i < heatData.length; i++) if (norm(heatData[i].county) === key) return heatData[i];
    return { n: 0, high: 0 };
  }
  function maxStat() {
    var m = 0;
    heatData.forEach(function (d) { m = Math.max(m, fillMode.value === "high" ? d.high : d.n); });
    return m;
  }
  function styleFeature(f) {
    var s = countyStat(f.properties.name), m = maxStat();
    var v = fillMode.value === "high" ? s.high : s.n;
    var fill = fillMode.value === "none" ? "#dfe9d5" : (m > 0 ? rampColor(v / m) : "#e9f0dd");
    var isSel = selected && norm(selected) === norm(f.properties.name);
    return {
      fillColor: fill, fillOpacity: 0.92,
      color: isSel ? "#143d2b" : "#fffdf8",
      weight: isSel ? 3 : 1.3,
      opacity: 1
    };
  }
  function restyle() { if (geoLayer) geoLayer.setStyle(styleFeature); }

  /* ---- county labels ---- */
  function ringCentroid(ring) {
    var area = 0, cx = 0, cy = 0;
    for (var i = 0, n = ring.length, j = n - 1; i < n; j = i++) {
      var f = ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
      area += f; cx += (ring[j][0] + ring[i][0]) * f; cy += (ring[j][1] + ring[i][1]) * f;
    }
    if (Math.abs(area) < 1e-9) {
      var sx = 0, sy = 0;
      ring.forEach(function (p) { sx += p[0]; sy += p[1]; });
      return [sy / ring.length, sx / ring.length];
    }
    area *= 3; return [cy / area, cx / area];
  }
  function featureCentroid(f) {
    var g = f.geometry, rings = g.type === "Polygon" ? [g.coordinates[0]] : g.coordinates.map(function (p) { return p[0]; });
    var best = rings[0];
    rings.forEach(function (r) { if (r.length > best.length) best = r; });
    return ringCentroid(best);
  }
  function buildLabels(geo) {
    labelLayer.clearLayers();
    geo.features.forEach(function (f) {
      var ll = featureCentroid(f);
      L.marker(ll, {
        interactive: false,
        icon: L.divIcon({ className: "county-label", html: esc(f.properties.name), iconSize: null })
      }).addTo(labelLayer);
    });
  }

  /* ---- pins & heat ---- */
  function markerColor(r) {
    if (r.status === "verified" || r.status === "corrected") return "#143d2b";
    return SEV_COLOR[r.severity] || "#e0a32e";
  }
  function drawHeat() {
    if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
    if (!showHeat || !rows.length || typeof L.heatLayer !== "function") return;
    var pts = rows.map(function (r) {
      return [r.lat, r.lng, r.severity === "high" ? 0.9 : r.severity === "medium" ? 0.6 : 0.35];
    });
    heatLayer = L.heatLayer(pts, {
      radius: 26, blur: 20, maxZoom: 10,
      gradient: { 0.2: "#7fc79a", 0.5: "#e0a32e", 0.8: "#c1553a", 1.0: "#8a1a12" }
    }).addTo(map);
  }
  function drawPins() {
    pinLayer.clearLayers();
    if (!showPins) return;
    rows.forEach(function (r) {
      var m = L.circleMarker([r.lat, r.lng], {
        radius: 7, color: "#fff", weight: 1.5,
        fillColor: markerColor(r), fillOpacity: 0.95
      });
      m.bindPopup(
        "<b>" + esc(r.pest) + "</b><br>" + esc(r.crop) + " · " + esc(r.county) +
        "<br><span style='opacity:.7'>" + esc(r.date) + " · " + esc(r.status) + "</span>"
      );
      m.addTo(pinLayer);
    });
  }

  /* ---- county card ---- */
  function showCounty(name) {
    selected = name;
    var mine = rows.filter(function (r) { return norm(r.county) === norm(name); });
    var high = mine.filter(function (r) { return r.severity === "high"; }).length;
    var counts = {};
    mine.forEach(function (r) { counts[r.pest] = (counts[r.pest] || 0) + 1; });
    var top = Object.keys(counts).map(function (k) { return [k, counts[k]]; })
      .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 3);
    document.getElementById("countyName").textContent = name;
    document.getElementById("countyTotal").textContent = mine.length;
    document.getElementById("countyHigh").textContent = high;
    document.getElementById("countyPests").innerHTML = top.length
      ? "<h4>" + esc(I18N.top) + "</h4>" + top.map(function (p) {
          return "<div class='county-pest'><span>" + esc(p[0]) + "</span><b>" + p[1] + "</b></div>";
        }).join("")
      : "<p class='muted small'>" + esc(I18N.none) + "</p>";
    card.classList.remove("hidden");
    restyle();
  }
  function clearCounty() {
    selected = null;
    card.classList.add("hidden");
    restyle();
    map.fitBounds(KENYA);
  }

  /* ---- data loading ---- */
  function loadReports() {
    var params = new URLSearchParams({ days: daysFilter.value });
    if (cropFilter.value) params.set("crop", cropFilter.value);
    return fetch("/api/reports?" + params.toString())
      .then(function (r) { return r.json(); })
      .then(function (data) {
        rows = data;
        drawPins(); drawHeat();
        if (selected) showCounty(selected);
      })
      .catch(function () { /* keep last good layer */ });
  }
  function loadHeat() {
    return fetch("/api/heatmap").then(function (r) { return r.json(); })
      .then(function (data) { heatData = data; restyle(); })
      .catch(function () {});
  }
  function loadTrend() {
    fetch("/api/trend?days=" + daysFilter.value)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!trendCtx || typeof Chart === "undefined") return;
        var labels = data.map(function (d) { return d.date.slice(5); });
        var values = data.map(function (d) { return d.n; });
        if (trendChart) {
          trendChart.data.labels = labels;
          trendChart.data.datasets[0].data = values;
          trendChart.update();
          return;
        }
        trendChart = new Chart(trendCtx, {
          type: "line",
          data: { labels: labels, datasets: [{
            label: "Reports", data: values, fill: true, tension: 0.3,
            borderColor: "#c1553a", backgroundColor: "rgba(224,163,46,.22)",
            pointBackgroundColor: "#143d2b", pointRadius: 3, borderWidth: 2
          }] },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
          }
        });
      })
      .catch(function () {});
  }
  function reload() { loadReports(); loadTrend(); }

  /* ---- boundaries (the only base layer) ---- */
  fetch("/static/data/kenya-counties.geojson")
    .then(function (r) { return r.json(); })
    .then(function (geo) {
      geoLayer = L.geoJSON(geo, {
        style: styleFeature,
        onEachFeature: function (f, layer) {
          layer.on({
            mouseover: function (e) {
              e.target.setStyle({ weight: 2.6, color: "#1c5a3d" });
              e.target.bringToFront();
              var s = countyStat(f.properties.name);
              layer.bindTooltip(
                "<b>" + esc(f.properties.name) + "</b><br>" + s.n + " " + esc(I18N.reports) +
                " · " + s.high + " " + esc(I18N.high),
                { sticky: true, className: "county-tip", direction: "top", opacity: 1 }
              ).openTooltip();
            },
            mouseout: function (e) {
              geoLayer.resetStyle(e.target);
              layer.unbindTooltip();
            },
            click: function () {
              showCounty(f.properties.name);
              map.fitBounds(layer.getBounds().pad(0.25), { maxZoom: 9 });
            }
          });
        }
      }).addTo(map);
      buildLabels(geo);
      if (showLabels) labelLayer.addTo(map);
      return loadHeat();
    })
    .catch(function () { /* boundaries unavailable: pins still work on the plain background */ })
    .then(reload);

  /* ---- controls ---- */
  cropFilter.addEventListener("change", reload);
  daysFilter.addEventListener("change", reload);
  fillMode.addEventListener("change", restyle);

  function wireToggle(id, get, set) {
    document.getElementById(id).addEventListener("click", function () {
      set(!get());
      this.classList.toggle("on", get());
      this.setAttribute("aria-pressed", get() ? "true" : "false");
    });
  }
  wireToggle("toggleHeat", function () { return showHeat; }, function (v) { showHeat = v; drawHeat(); });
  wireToggle("togglePins", function () { return showPins; }, function (v) { showPins = v; drawPins(); });
  wireToggle("toggleLabels", function () { return showLabels; }, function (v) {
    showLabels = v;
    if (v) labelLayer.addTo(map); else map.removeLayer(labelLayer);
  });

  document.getElementById("zoomIn").addEventListener("click", function () { map.zoomIn(); });
  document.getElementById("zoomOut").addEventListener("click", function () { map.zoomOut(); });
  document.getElementById("resetView").addEventListener("click", clearCounty);
  document.getElementById("countyClose").addEventListener("click", function () {
    selected = null; card.classList.add("hidden"); restyle();
  });
  document.getElementById("countyClear").addEventListener("click", clearCounty);

  document.getElementById("exportCsv").addEventListener("click", function () {
    var head = "id,date,county,crop,pest,severity,status,lat,lng";
    var lines = rows.map(function (r) {
      return [r.id, r.date, r.county, r.crop, r.pest, r.severity, r.status, r.lat, r.lng]
        .map(function (v) { return '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"'; }).join(",");
    });
    var blob = new Blob([head + "\n" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "ukulima-reports-" + daysFilter.value + "d.csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  });

  map.on("focus", function () { map.scrollWheelZoom.enable(); });
  map.on("blur", function () { map.scrollWheelZoom.disable(); });
})();