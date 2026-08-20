/* ===========================================================================
   Landing-page summary chart — the site's ONE canonical bar chart (it used to
   appear again on Works-over-time; that instance was removed so this is the
   single place it lives).

   Read-only on purpose: no filter, no metric toggle, no re-ranking. Its job is
   to establish what the data can support before the reader reaches anything
   interactive.

   No tiers. Every work is one row, sorted by its confident floor. The honest
   per-work uncertainty is carried by the FADE: the length of the tail is the
   ambiguous, could-not-be-placed traffic that might belong here (shared with
   collision partners, so never a subtotal). A long fade = read the bar as a
   floor. The hover adds distinct articles, collision partners, and — for
   thinly-cited works — a small-n note. Localised "uneven coverage" bands are a
   per-work concern shown on the passage view, not here.
   ======================================================================== */
window.renderLandingBars = function (host, DATA) {
  var AUTHORS = {"Magna_Moralia":"a","Meno":"p","De_Incessu_Animalium":"a","Ion":"p","Euthyphro":"p","De_Generatione_Animalium":"a","Hippias_Minor":"p","De_Respiratione":"a","Meteorology":"a","Sophist":"p","Prior_Analytics":"a","De_Partibus_Animalium":"a","Apology":"p","Posterior_Analytics":"a","Critias":"p","Cratylus":"p","Euthydemus":"p","Lysis":"p","Historia_Animalium":"a","Menexenus":"p","Parmenides":"p","Hippias_Major":"p","De_Insomniis":"a","Alcibiades_2":"p","Rival_Lovers":"p","Nicomachean_Ethics":"a","Metaphysics":"a","De_Sensu":"a","Rhetoric":"a","Poetics":"a","Hipparchus":"p","Statesman":"p","Topics":"a","De_Divinatione_per_Somnum":"a","Theages":"p","Laches":"p","De_Caelo":"a","Clitophon":"p","Crito":"p","Philebus":"p","Letters":"p","De_Generatione_et_Corruptione":"a","Alcibiades_1":"p","Rhetorica_ad_Alexandrum":"a","Charmides":"p","Republic":"p","Politics":"a","De_Somno":"a","De_Interpretatione":"a","Gorgias":"p","Eudemian_Ethics":"a","De_Motu_Animalium":"a","Symposium":"p","De_Longitudine_Vitae":"a","Phaedrus":"p","Physics":"a","Laws":"p","Sophistical_Refutations":"a","De_Juventute":"a","Categories":"a","De_Anima":"a","Epinomis":"p","Timaeus":"p","De_Memoria":"a","Minos":"p","Phaedo":"p","Protagoras":"p","Theaetetus":"p"};

  function authorName(w) { return AUTHORS[w] === "a" ? "Aristotle" : "Plato"; }
  function nice(n) { return (n || 0).toLocaleString(); }

  // one shared tooltip element, reused across every row
  var tip = document.getElementById("lb-tip");
  if (!tip) {
    tip = document.createElement("div");
    tip.id = "lb-tip";
    tip.className = "lb-tip";
    document.body.appendChild(tip);
  }

  var TRACK = 560;
  var maxTotal = 1;
  DATA.forEach(function (w) {
    maxTotal = Math.max(maxTotal, w.floor + w.unplaceable);
  });
  var SCALE = TRACK / maxTotal;

  host.innerHTML = "";

  var key = document.createElement("div");
  key.className = "lb-key";
  key.innerHTML =
    '<span class="k"><i class="sw floor"></i>placed with confidence</span>' +
    '<span class="k"><i class="sw fade"></i>detected, could not be placed</span>' +
    '<span class="k"><i class="chip p"></i>Stephanus (Plato)</span>' +
    '<span class="k"><i class="chip a"></i>Bekker (Aristotle)</span>';
  host.appendChild(key);

  // One list, ranked by the confident floor. No tiers.
  var works = DATA.slice().sort(function (a, b) { return b.floor - a.floor; });
  var rows = document.createElement("div");
  rows.className = "lb-rows";
  works.forEach(function (w) { rows.appendChild(row(w, SCALE)); });
  host.appendChild(rows);

  function row(w, SCALE) {
    var au = AUTHORS[w.work] === "a" ? "a" : "p";
    var rgb = au === "a" ? "31,158,138" : "90,84,151";
    var el = document.createElement("div");
    el.className = "lb-row";
    var fw = Math.max(1, w.floor * SCALE);
    var dw = Math.max(0, w.unplaceable * SCALE);
    var fade = "linear-gradient(90deg,rgba(" + rgb + ",.5) 0%,rgba(" + rgb +
               ",.25) 45%,rgba(" + rgb + ",0) 100%)";
    el.innerHTML =
      '<span class="lb-name">' + w.work.replace(/_/g, " ") + "</span>" +
      '<span class="lb-track">' +
        '<span class="lb-floor" style="width:' + fw + "px;background:var(--" + au + '-floor)"></span>' +
        (dw > 2 ? '<span class="lb-fade" style="width:' + Math.min(dw, 250) +
                  "px;background:" + fade + '"></span>' : "") +
      "</span>" +
      '<span class="lb-val">' + nice(w.floor) + "</span>";

    el.addEventListener("mousemove", function (e) { showTip(e, w); });
    el.addEventListener("mouseleave", hideTip);
    el.addEventListener("touchstart", function (e) { showTip(e.touches[0], w); }, { passive: true });
    el.addEventListener("touchend", hideTip);
    return el;
  }

  function showTip(e, w) {
    var bandExtra = Math.max(0, (w.band || w.floor) - w.floor);
    var total = w.floor + bandExtra + w.unplaceable;
    var html = '<div class="tt-name">' + w.work.replace(/_/g, " ") + "</div>";
    html += '<div class="tt-sub">' + authorName(w.work) + "</div>";
    html += '<div class="tt-row">floor <b>' + nice(w.floor) + "</b> placed with confidence";
    if (bandExtra > 0) html += " · +" + nice(bandExtra) + " reasonably sure";
    html += "</div>";
    if (w.unplaceable > 0) {
      html += '<div class="tt-row">+<b>' + nice(w.unplaceable) +
              "</b> detected but unplaceable <span class=\"tt-dim\">(shared with " +
              "collision partners; at most ≈" + nice(Math.round(total)) +
              " if every one belonged here)</span></div>";
    }
    html += '<div class="tt-row"><span class="tt-dim">' +
            nice(w.distinct_articles) + " distinct articles</span></div>";
    if (w.collides_with && w.collides_with.length) {
      html += '<div class="tt-col">collides with ' +
              w.collides_with.slice(0, 4).map(function (x) {
                return x.replace(/_/g, " ");
              }).join(", ") + "</div>";
    }
    if (w.small_n) {
      html += '<div class="tt-warn">Few citations — read this bar as an order ' +
              "of magnitude, not a precise count.</div>";
    }
    tip.innerHTML = html;
    tip.style.opacity = "1";
    var x = Math.min(e.clientX + 14, window.innerWidth - 300);
    tip.style.left = x + "px";
    tip.style.top = (e.clientY + 14) + "px";
  }

  function hideTip() { tip.style.opacity = "0"; }
};
