(function () {
  // ────────────────────────────────────────────────────────────────
  // Alpine bootstrapping: Theme store (dark / light / system)
  // ────────────────────────────────────────────────────────────────
  document.addEventListener("alpine:init", () => {
  const A = window.Alpine;
  if (!A.store("theme")) {
    const stored = localStorage.getItem("theme") || "system";
    A.store("theme", {
      value: stored,
      systemDark: window.matchMedia("(prefers-color-scheme: dark)").matches,
      set(next){ this.value = next; localStorage.setItem("theme", next); this.apply(); },
      apply(){
        const useDark = this.value === "dark" || (this.value === "system" && this.systemDark);
        document.documentElement.classList.toggle("dark", useDark);
      },
    });
    A.store("theme").apply();
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      A.store("theme").systemDark = e.matches;
      if (A.store("theme").value === "system") A.store("theme").apply();
    });
  }
});


  // ────────────────────────────────────────────────────────────────
  // App bootstrap + progressive enhancement hooks
  // ────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    console.log("[DOMContentLoaded] fired");
    window.APP = { env: document.body.dataset.env || "prod" };
    console.log("[APP] ready, env =", window.APP.env);

    // =================================================================
    // Feature: Exam Details Toggle
    // Goal:
    //   Show the #exam-details section only when the student selects
    //   "Yes" for: Have you taken an English language exam in the past
    //   five years?
    //
    // Why delegated events?
    //   - Robust if the radio inputs are re-rendered by Django or HTMX.
    //   - No dependency on specific element IDs (but they can exist).
    //
    // HTML expectations:
    //   - Two radios named "has_recent_english_exam" with values "True"/"False"
    //     <input type="radio" name="has_recent_english_exam" value="True"  id="exam_yes"  .../>
    //     <input type="radio" name="has_recent_english_exam" value="False" id="exam_no"   .../>
    //   - Placeholder container:
    //     <div id="exam-details" class="hidden opacity-0 transition-all duration-500 ease-in-out overflow-hidden"> ... </div>
    // =================================================================

    const examDetailsEl = document.getElementById("exam-details");

    /**
     * Returns true if the "Yes" radio (value="True") is currently checked.
     * Uses a name-based selector to be resilient to DOM changes.
     */
    function isExamYesSelected() {
      const yesRadio = document.querySelector(
        'input[name="has_recent_english_exam"][value="True"]'
      );
      return !!yesRadio && yesRadio.checked;
    }

    /**
     * Apply show/hide styles to the exam details block with a smooth transition.
     * - State is driven by a data attribute: `data-open="true|false"` on #exam-details.
     * - We animate height via `max-height` and fade via `opacity` on the container.
     * - Child elements (e.g., ShadCN triggers) fade/slide using
     *   Tailwind group selectors: `group-[data-open=true]/exam:*`.
     * - We intentionally DO NOT toggle `hidden`; keeping the element in-flow
     *   allows children to transition with the panel instead of popping in.
     */
    function renderExamDetails() {
      if (!examDetailsEl) return;

      const show = isExamYesSelected();

      // Toggle the data attribute (drives child transitions)
      examDetailsEl.dataset.open = show ? "true" : "false";

      // Opacity is handled by CSS via the data attribute; keep height animated here
      if (show) {
        // First measure content height
        // Set to a large-enough value to trigger transition
        examDetailsEl.style.maxHeight = examDetailsEl.scrollHeight + "px";
        examDetailsEl.style.opacity = "1"; // optional; CSS handles it but harmless
      } else {
        // Collapse smoothly
        examDetailsEl.style.maxHeight = "0px";
        examDetailsEl.style.opacity = "0"; // optional
      }

      console.log("[exam] render", { show });
    }


    /**
     * Event delegation: listen for changes on the entire document.
     * Only react when the target input belongs to the radio group
     * `has_recent_english_exam`.
     */
    document.addEventListener("change", (evt) => {
      const t = evt.target;
      if (t && t.name === "has_recent_english_exam") {
        console.log("[exam] change", { name: t.name, value: t.value });
        renderExamDetails();
      }
    });

    // Initialize state on first paint
    renderExamDetails();
  });



})();
