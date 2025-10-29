(function () {
  document.addEventListener("alpine:init", () => {
    console.log("[alpine:init] fired");

    const A = window.Alpine;

    // Avoid duplicate stores
    if (A.store("theme")) return;

    const stored = localStorage.getItem("theme") || "system";

    A.store("theme", {
      value: stored,
      systemDark: window.matchMedia("(prefers-color-scheme: dark)").matches,

      set(next) {
        this.value = next;
        localStorage.setItem("theme", next);
        this.apply();
        console.log("[theme] set", { next });
      },

      apply() {
        const useDark =
          this.value === "dark" ||
          (this.value === "system" && this.systemDark);
        document.documentElement.classList.toggle("dark", useDark);
        console.log("[theme] apply", {
          value: this.value,
          systemDark: this.systemDark,
          useDark,
        });
      },
    });

    // Apply on load
    A.store("theme").apply();

    // Watch for OS dark mode changes (system mode)
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      A.store("theme").systemDark = e.matches;
      if (A.store("theme").value === "system") {
        A.store("theme").apply();
      }
    });
  });

  document.addEventListener("DOMContentLoaded", () => {
    console.log("[DOMContentLoaded] fired");
    window.APP = { env: document.body.dataset.env || "prod" };
    console.log("[APP] ready, env =", window.APP.env);
  });
})();
