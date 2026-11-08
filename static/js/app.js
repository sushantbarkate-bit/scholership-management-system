// Portal interactions: confirmation dialogs, sidebar toggle, toast dismissal,
// file-name preview and double-submit protection. Progressive enhancement
// only: every page still works without this script.
(function () {
  "use strict";

  // Forms: confirm first, then lock the submit button (unless cancelled).
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var message = form.getAttribute("data-confirm");
      if (message && !window.confirm(message)) {
        event.preventDefault();
        return;
      }
      form.querySelectorAll("button[type=submit]").forEach(function (button) {
        if (!button.hasAttribute("data-no-lock")) {
          button.disabled = true;
        }
      });
    });
  });

  // Links and buttons (outside a form) with data-confirm
  document.addEventListener("click", function (event) {
    var target = event.target.closest("a[data-confirm], button[data-confirm]");
    if (target && !window.confirm(target.getAttribute("data-confirm"))) {
      event.preventDefault();
    }
  });

  // Mobile sidebar toggle
  var toggle = document.getElementById("msp-menu-toggle");
  var sidebar = document.getElementById("msp-sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
  }

  // Auto-dismiss toast notifications after 6 seconds
  document.querySelectorAll(".msp-toast").forEach(function (toast) {
    setTimeout(function () {
      if (window.bootstrap && bootstrap.Toast) {
        bootstrap.Toast.getOrCreateInstance(toast).hide();
      } else {
        toast.remove();
      }
    }, 6000);
  });

  // Show the chosen file name under file inputs
  document.querySelectorAll("input[type=file][data-preview]").forEach(function (input) {
    input.addEventListener("change", function () {
      var target = document.getElementById(input.getAttribute("data-preview"));
      if (target) {
        target.textContent = input.files && input.files.length ? input.files[0].name : "";
      }
    });
  });
})();
