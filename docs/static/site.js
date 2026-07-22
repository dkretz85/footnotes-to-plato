/* Site chrome behaviour. Deliberately tiny — the interactive work lives in the
   viewers; this is just the mobile menu. */
(function () {
  var btn = document.querySelector(".navtoggle");
  var nav = document.querySelector(".mainnav");
  if (btn && nav) {
    btn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
})();
