/* Ukulima global enhancements: scroll reveals and service-worker registration. */
(function () {
  "use strict";

  // Reveal-on-scroll (progressive enhancement; content is visible without JS
  // because the .reveal class only hides when this script runs).
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("in"); });
  }

  // Register the static-asset service worker (scoped to /static/).
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/static/js/sw.js").catch(function () {});
    });
  }

  // Highlight the nav link for the current page.
  var path = window.location.pathname;
  document.querySelectorAll("header nav a").forEach(function (a) {
    if (a.getAttribute("href") === path) a.classList.add("on");
  });
})();