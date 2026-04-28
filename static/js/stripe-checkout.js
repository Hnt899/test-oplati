(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  ready(function () {
    var cfg = window.OPLATI_CONFIG;
    if (!cfg || !cfg.publishableKey || !cfg.itemId) {
      return;
    }

    var stripe = Stripe(cfg.publishableKey);
    var btn = document.getElementById("buy-btn");
    var errEl = document.getElementById("buy-error");

    if (!btn) {
      return;
    }

    btn.addEventListener("click", function () {
      errEl.classList.add("d-none");
      btn.disabled = true;
      fetch("/buy/" + cfg.itemId + "/", { method: "GET", credentials: "same-origin" })
        .then(function (res) {
          if (!res.ok) {
            throw new Error("Checkout failed");
          }
          return res.json();
        })
        .then(function (data) {
          return stripe.redirectToCheckout({ sessionId: data.session_id });
        })
        .then(function (result) {
          if (result.error) {
            throw new Error(result.error.message);
          }
        })
        .catch(function (e) {
          errEl.textContent = e.message || "Unable to start checkout.";
          errEl.classList.remove("d-none");
          btn.disabled = false;
        });
    });
  });
})();
