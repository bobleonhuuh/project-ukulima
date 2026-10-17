/* Outbreak map: Leaflet pins + heatmap, and a Chart.js trend line. Kenya-only. */
(function () {
  "use strict";
  if (typeof L === "undefined") return;

  var SEV_COLOR = { low: "#2f8a5b", medium: "#e0a32e", high: "#c1553a" };

  // Kenya's bounding box — the map is locked to this area.
  var KENYA = L.latLngBounds([-4.8, 33.8], [5.1, 42.0]);

  var map = L.map("map", {
    scrollWheelZoom: false,
    maxBounds: KENYA,
    maxBoundsViscosity: 1.0,
    minZoom: 6,
  });
  map.fitBounds(KENYA);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    minZoom: 6,
    bounds: KENYA,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  var pinLayer = L.layerGroup().addTo(map);
  var heatLayer = null;
  var showHeat = true;
  var showPins = true;

  var cropFilter = document.getElementById("cropFilter");
  var daysFilter = document.getElementById("daysFilter");
  var trendCtx = document.getElementById("trendChart");
  var trendChart = null;

  function markerColor(r) {
    if (r.status === "verified" || r.status === "corrected") return "#143d2b";
    return SEV_COLOR[r.severity] || "#e0a32e";
  }

  function drawHeat(points) {
    if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
    if (!showHeat || !points.length || typeof L.heatLayer !== "function") return;
    heatLayer = L.heatLayer(points, {
      radius: 26, blur: 20, maxZoom: 10,
      gradient: { 0.2: "#7fc79a", 0.5: "#e0a32e", 0.8: "#c1553a", 1.0: "#8a1a12" },
    }).addTo(map);
  }

  function drawPins(rows) {
    pinLayer.clearLayers();
    if (!showPins) return;
    rows.forEach(function (r) {
      var m = L.circleMarker([r.lat, r.lng], {
        radius: 7, color: "#fff", weight: 1.5,
        fillColor: markerColor(r), fillOpacity: 0.95,
      });
      m.bindPopup(
        "<b>" + r.pest + "</b><br>" + r.crop + " · " + r.county +
        "<br><span style='opacity:.7'>" + r.date + " · " + r.status + "</span>"
      );
      m.addTo(pinLayer);
    });
  }

  function loadReports() {
    var params = new URLSearchParams({ days: daysFilter.value });
    if (cropFilter.value) params.set("crop", cropFilter.value);
    fetch("/api/reports?" + params.toString())
      .then(function (r) { return r.json(); })
      .then(function (rows) {
        var pts = rows.map(function (r) {
          return [r.lat, r.lng, r.severity === "high" ? 0.9 : r.severity === "medium" ? 0.6 : 0.35];
        });
        drawPins(rows);
        drawHeat(pts);
      })
      .catch(function () { /* leave last good layer */ });
  }

  function loadTrend() {
    fetch("/api/trend?days=" + daysFilter.value)
      .then(function (r) { return r.json(); })
      .then(function (rows) {
        if (!trendCtx || typeof Chart === "undefined") return;
        var labels = rows.map(function (d) { return d.date.slice(5); });
        var data = rows.map(function (d) { return d.n; });
        if (trendChart) {
          trendChart.data.labels = labels;
          trendChart.data.datasets[0].data = data;
          trendChart.update();
          return;
        }
        trendChart = new Chart(trendCtx, {
          type: "line",
          data: { labels: labels, datasets: [{
            label: "Reports", data: data, fill: true, tension: 0.3,
            borderColor: "#c1553a", backgroundColor: "rgba(224,163,46,.22)",
            pointBackgroundColor: "#143d2b", pointRadius: 3, borderWidth: 2,
          }] },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
          },
        });
      })
      .catch(function () {});
  }

  function reload() { loadReports(); loadTrend(); }

  cropFilter.addEventListener("change", reload);
  daysFilter.addEventListener("change", reload);

  document.getElementById("toggleHeat").addEventListener("click", function () {
    showHeat = !showHeat;
    this.classList.toggle("ghost", !showHeat);
    this.style.opacity = showHeat ? "1" : "0.5";
    loadReports();
  });
  document.getElementById("togglePins").addEventListener("click", function () {
    showPins = !showPins;
    this.style.opacity = showPins ? "1" : "0.5";
    loadReports();
  });

  reload();
})();