/* ===========================================================================
   Landing-page summary chart — the View A bar chart, rendered as a FIGURE.
   Read-only on purpose: no filter, no metric toggle, no re-ranking. Its job is
   to establish what the data can support before the reader reaches anything
   interactive, so it should invite reading rather than fiddling.
   ======================================================================== */
window.renderLandingBars = function (host, DATA) {
  var AUTHORS = {"Magna_Moralia":"a","Meno":"p","De_Incessu_Animalium":"a","Ion":"p","Euthyphro":"p","De_Generatione_Animalium":"a","Hippias_Minor":"p","De_Respiratione":"a","Meteorology":"a","Sophist":"p","Prior_Analytics":"a","De_Partibus_Animalium":"a","Apology":"p","Posterior_Analytics":"a","Critias":"p","Cratylus":"p","Euthydemus":"p","Lysis":"p","Historia_Animalium":"a","Menexenus":"p","Parmenides":"p","Hippias_Major":"p","De_Insomniis":"a","Alcibiades_2":"p","Rival_Lovers":"p","Nicomachean_Ethics":"a","Metaphysics":"a","De_Sensu":"a","Rhetoric":"a","Poetics":"a","Hipparchus":"p","Statesman":"p","Topics":"a","De_Divinatione_per_Somnum":"a","Theages":"p","Laches":"p","De_Caelo":"a","Clitophon":"p","Crito":"p","Philebus":"p","Letters":"p","De_Generatione_et_Corruptione":"a","Alcibiades_1":"p","Rhetorica_ad_Alexandrum":"a","Charmides":"p","Republic":"p","Politics":"a","De_Somno":"a","De_Interpretatione":"a","Gorgias":"p","Eudemian_Ethics":"a","De_Motu_Animalium":"a","Symposium":"p","De_Longitudine_Vitae":"a","Phaedrus":"p","Physics":"a","Laws":"p","Sophistical_Refutations":"a","De_Juventute":"a","Categories":"a","De_Anima":"a","Epinomis":"p","Timaeus":"p","De_Memoria":"a","Minos":"p","Phaedo":"p","Protagoras":"p","Theaetetus":"p"};

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

  ["trustworthy", "uncertain"].forEach(function (tier) {
    var works = DATA.filter(function (w) { return w.tier === tier; })
                    .sort(function (a, b) { return b.floor - a.floor; });
    if (!works.length) return;

    var sec = document.createElement("section");
    sec.className = "lb-tier";

    var h = document.createElement("div");
    h.className = "lb-h";
    h.innerHTML = tier === "trustworthy"
      ? '<h3>Reliable</h3><span class="tag t">' + works.length +
        ' works · 80%+ of citations placed</span>'
      : '<h3>Partial</h3><span class="tag u">' + works.length +
        ' works · under 80% placed</span>';
    sec.appendChild(h);

    var note = document.createElement("p");
    note.className = "lb-note";
    note.innerHTML = tier === "trustworthy"
      ? 'Bar lengths are comparable. These works can be ranked against each other.'
      : 'Bar lengths are floors only. <b>A short bar here does not mean a work is ' +
        'little studied</b> — it means much of its citation traffic could not be ' +
        'attributed. Do not rank these against the tier above.';
    sec.appendChild(note);

    var rows = document.createElement("div");
    rows.className = "lb-rows";
    works.forEach(function (w) { rows.appendChild(row(w, SCALE)); });
    sec.appendChild(rows);
    host.appendChild(sec);
  });

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
      '<span class="lb-val">' + w.floor.toLocaleString() + "</span>";
    el.title = w.work.replace(/_/g, " ") + ": " + w.floor.toLocaleString() +
               " placed" +
               (w.unplaceable ? ", " + w.unplaceable.toLocaleString() +
                " detected but unplaceable" : "") +
               " · " + Math.round(w.resolution_rate * 100) + "% placement rate";
    return el;
  }
};
