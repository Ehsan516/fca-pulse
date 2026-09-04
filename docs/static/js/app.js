(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);

  var searchInput = document.getElementById("search-input");
  var filterSource = document.getElementById("filter-source");
  var filterArea = document.getElementById("filter-area");
  var filterDoctype = document.getElementById("filter-doctype");
  var filterImpact = document.getElementById("filter-impact");
  var resultCount = document.getElementById("result-count");
  var emptyState = document.getElementById("empty-state");

  if (!searchInput) return; // deadlines page has no filter UI

  var cards = Array.prototype.slice.call(document.querySelectorAll("#items .card"));

  function applyFromParams() {
    if (params.has("q")) searchInput.value = params.get("q");
    if (params.has("source")) filterSource.value = params.get("source");
    if (params.has("area")) filterArea.value = params.get("area");
    if (params.has("doctype")) filterDoctype.value = params.get("doctype");
    if (params.has("impact")) filterImpact.value = params.get("impact");
  }

  function updateUrl() {
    var p = new URLSearchParams();
    if (searchInput.value) p.set("q", searchInput.value);
    if (filterSource.value) p.set("source", filterSource.value);
    if (filterArea.value) p.set("area", filterArea.value);
    if (filterDoctype.value) p.set("doctype", filterDoctype.value);
    if (filterImpact.value) p.set("impact", filterImpact.value);
    var qs = p.toString();
    history.replaceState(null, "", qs ? "?" + qs : window.location.pathname);
  }

  function matches(card) {
    var q = searchInput.value.trim().toLowerCase();
    if (q && card.dataset.search.indexOf(q) === -1) return false;
    if (filterSource.value && card.dataset.source !== filterSource.value) return false;
    if (filterDoctype.value && card.dataset.doctype !== filterDoctype.value) return false;
    if (filterImpact.value && card.dataset.impact !== filterImpact.value) return false;
    if (filterArea.value) {
      var areas = card.dataset.areas ? card.dataset.areas.split(",") : [];
      if (areas.indexOf(filterArea.value) === -1) return false;
    }
    return true;
  }

  function refresh() {
    var visible = 0;
    cards.forEach(function (card) {
      var show = matches(card);
      card.hidden = !show;
      if (show) visible += 1;
    });
    resultCount.textContent = visible + " of " + cards.length + " item" + (cards.length === 1 ? "" : "s");
    if (emptyState) emptyState.hidden = visible !== 0 || cards.length === 0;
    updateUrl();
  }

  [searchInput, filterSource, filterArea, filterDoctype, filterImpact].forEach(function (el) {
    el.addEventListener("input", refresh);
  });

  applyFromParams();
  refresh();
})();
