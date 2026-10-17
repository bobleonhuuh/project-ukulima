/* Report form: GPS capture and photo preview. */
(function () {
  "use strict";
  var gpsBtn = document.getElementById("gpsBtn");
  var gpsStatus = document.getElementById("gpsStatus");
  var lat = document.getElementById("lat");
  var lng = document.getElementById("lng");

  if (gpsBtn) {
    gpsBtn.addEventListener("click", function () {
      if (!("geolocation" in navigator)) {
        gpsStatus.textContent = "Geolocation is not available on this device — you can still submit without it.";
        return;
      }
      gpsStatus.textContent = "Locating…";
      gpsBtn.disabled = true;
      navigator.geolocation.getCurrentPosition(function (pos) {
        lat.value = pos.coords.latitude.toFixed(4);
        lng.value = pos.coords.longitude.toFixed(4);
        gpsStatus.textContent = "Location captured ✓ (rounded to ~1 km on the map)";
        gpsBtn.disabled = false;
      }, function () {
        gpsStatus.textContent = "Could not get your location — you can still submit without it.";
        gpsBtn.disabled = false;
      }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 });
    });
  }

  var photo = document.getElementById("photo");
  var preview = document.getElementById("preview");
  var dropText = document.getElementById("dropText");
  if (photo) {
    photo.addEventListener("change", function () {
      var file = photo.files && photo.files[0];
      if (!file) return;
      if (file.size > 8 * 1024 * 1024) {
        dropText.innerHTML = "<b style='color:#b3261e'>That photo is larger than 8 MB. Please choose a smaller one.</b>";
        photo.value = "";
        return;
      }
      var url = URL.createObjectURL(file);
      preview.src = url;
      preview.classList.remove("hidden");
      dropText.innerHTML = "<b>" + file.name + "</b><br><span class='small muted'>Tap to change</span>";
    });
  }
})();