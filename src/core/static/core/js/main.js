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
    window.APP = { env: document.body.dataset.env || "prod" };

    // ===== Panels (animated) ======================================
    const examDetailsEl    = document.getElementById("exam-details");    // region for “English exam in past 5 years?”
    const cambridgeExtraEl = document.getElementById("cambridge-extra"); // optional section (C1/C2 only)

    function animatePanel(el, show) {
      if (!el) return;
      el.dataset.open = show ? "true" : "false";
      el.setAttribute("aria-hidden", show ? "false" : "true");
      if (show) {
        el.style.overflow  = "hidden";
        el.style.maxHeight = el.scrollHeight + "px";
        el.style.opacity   = "1";
        const done = () => { el.style.maxHeight = "none"; el.style.overflow = "visible"; el.removeEventListener("transitionend", done); };
        el.addEventListener("transitionend", done);
      } else {
        el.style.overflow  = "hidden";
        el.style.maxHeight = "0px";
        el.style.opacity   = "0";
      }
    }

    // Helpers
    const $ = (sel) => document.querySelector(sel);
    const getCheckedValue = (name) => {
      const el = document.querySelector(`input[name="${name}"]:checked`);
      return el ? el.value : null;
    };

    // Native inputs on the profile form
    const examTypeSel  = $('select[name="exam_type"]');
    const hasExamYesNo = 'has_recent_english_exam';
    const reading   = $('#id_reading_score');
    const listening = $('#id_listening_score');
    const writing   = $('#id_writing_score');
    const speaking  = $('#id_speaking_score');
    const overall   = $('#id_overall_score');
    const override  = $('#id_overall_manual_override');
    const camGrade  = $('#id_cambridge_grade');
    const camUse    = $('#id_cambridge_use_of_english');
    const examDay   = $('#id_exam_day');
    const examMonth = $('#id_exam_month');
    const examYear  = $('#id_exam_year');

    // Show/hide the big exam details region
    function renderExamDetails() {
      const v = getCheckedValue(hasExamYesNo);
      const show = v === "True";
      animatePanel(examDetailsEl, show);
      if (!show) {
        // If user says "No", clear all exam fields so nothing sneaks into POST
        clearExamEverything();
        // Also hide Cambridge block
        animatePanel(cambridgeExtraEl, false);
      }
    }

    // Cambridge C1/C2 panel visibility
    function currentExamType() {
      if (!examTypeSel) return "";
      return (examTypeSel.value || "").toLowerCase();
    }
    function renderCambridgeExtra() {
      const et = currentExamType();
      animatePanel(cambridgeExtraEl, et === "c1" || et === "c2");
      if (et !== "c1" && et !== "c2") {
        // Leaving Cambridge → clear its extras
        if (camGrade) camGrade.value = "";
        if (camUse)   camUse.value   = "";
      }
    }

    // Clear *all* exam-related user inputs
    function clearExamEverything() {
      if (examTypeSel) examTypeSel.value = "";
      if (examDay)   examDay.value   = "";
      if (examMonth) examMonth.value = "";
      if (examYear)  examYear.value  = "";

      [reading, listening, writing, speaking, overall].forEach((el) => { if (el) el.value = ""; });
      if (override) override.checked = false;

      if (camGrade) camGrade.value = "";
      if (camUse)   camUse.value   = "";
    }

    // When the *exam type* changes mid-flow, reset sub-scores + overall
    let lastExamType = currentExamType();
    function onExamTypeChanged() {
      const next = currentExamType();
      if (next !== lastExamType) {
        // Reset scores so the student can enter fresh values for the new scheme
        [reading, listening, writing, speaking, overall].forEach((el) => { if (el) el.value = ""; });
        // If switching away from Cambridge, extra fields are cleared in renderCambridgeExtra()
        lastExamType = next;
      }
      renderCambridgeExtra();
    }

    // Wire listeners
    document.addEventListener("change", (evt) => {
      const t = evt.target;
      if (!t) return;
      if (t.name === hasExamYesNo) renderExamDetails();
      if (t === examTypeSel)       onExamTypeChanged();
    });

    // Initial paint
    renderExamDetails();
    renderCambridgeExtra();

  });

  // ────────────────────────────────────────────────────────────────
  // UX: bring first invalid field into view and highlight
  // ────────────────────────────────────────────────────────────────
  document.addEventListener(
    "invalid",
    (evt) => {
      const el = evt.target;
      // clear previous highlights
      document.querySelectorAll(".ring-2.ring-red-500").forEach((n) => {
        if (n !== el) n.classList.remove("ring-2", "ring-red-500");
      });
      // highlight current
      el.classList.add("ring-2", "ring-red-500");
      try { el.focus({ preventScroll: true }); } catch {}
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    },
    true
  );

  document.addEventListener("input", (evt) => {
    if (evt.target.matches(":valid")) {
      evt.target.classList.remove("ring-2", "ring-red-500");
    }
  });
})();
