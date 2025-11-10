(function () {
  // Theme store (unchanged)
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

  document.addEventListener("DOMContentLoaded", () => {
    window.APP = { env: document.body.dataset.env || "prod" };

    const examDetailsEl    = document.getElementById("exam-details");
    const cambridgeExtraEl = document.getElementById("cambridge-extra");

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

    // Helpers + field refs
    const $ = (sel) => document.querySelector(sel);
    const getCheckedValue = (name) => {
      const el = document.querySelector(`input[name="${name}"]:checked`);
      return el ? el.value : null;
    };

    const hasExamName = "has_recent_english_exam";

    // Core fields
    const examTypeSel  = $('select[name="exam_type"]');
    const examDay      = $('#id_exam_day');
    const examMonth    = $('#id_exam_month');
    const examYear     = $('#id_exam_year');

    const reading   = $('#id_reading_score');
    const listening = $('#id_listening_score');
    const writing   = $('#id_writing_score');
    const speaking  = $('#id_speaking_score');
    const overall   = $('#id_overall_score');
    const override  = $('#id_overall_manual_override');

    // Cambridge only
    const camGrade  = $('#id_cambridge_grade');
    const camUse    = $('#id_cambridge_use_of_english'); // optional

    // ── Required toggling so HTML5 validation works ────────────────
    function setRequired(el, on) {
      if (!el) return;
      if (on) el.setAttribute("required", "required");
      else el.removeAttribute("required");
    }
    function isCambridge(et) {
      return et === "c1" || et === "c2";
    }
    function currentExamType() {
      return (examTypeSel && examTypeSel.value ? examTypeSel.value : "").toLowerCase();
    }

    function applyRequiredRules() {
      const hasExam = getCheckedValue(hasExamName) === "True";

      // Base exam requirements when user said "Yes"
      const baseRequired = hasExam;
      setRequired(examTypeSel,  baseRequired);
      setRequired(examDay,      baseRequired);
      setRequired(examMonth,    baseRequired);
      setRequired(examYear,     baseRequired);
      setRequired(reading,      baseRequired);
      setRequired(listening,    baseRequired);
      setRequired(writing,      baseRequired);
      setRequired(speaking,     baseRequired);

      // Overall isn’t required when auto-calculated; only require if override is checked
      const needOverall = baseRequired && override && override.checked === true;
      setRequired(overall, needOverall);

      // Cambridge grade required only for C1/C2
      const et = currentExamType();
      setRequired(camGrade, baseRequired && isCambridge(et));

      // Optional: never required
      if (camUse) camUse.removeAttribute("required");
    }

    // ── Panels and clearing ────────────────────────────────────────
    function renderExamDetails() {
      const v = getCheckedValue(hasExamName);
      const show = v === "True";
      animatePanel(examDetailsEl, show);
      if (!show) {
        clearExamEverything();
        animatePanel(cambridgeExtraEl, false);
      }
      applyRequiredRules();
    }

    function renderCambridgeExtra() {
      const et = currentExamType();
      const show = isCambridge(et);
      animatePanel(cambridgeExtraEl, show);
      if (!show) {
        if (camGrade) camGrade.value = "";
        if (camUse)   camUse.value   = "";
      }
      applyRequiredRules();
    }

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

    // Reset subscores when switching exam type
    let lastExamType = currentExamType();
    function onExamTypeChanged() {
      const next = currentExamType();
      if (next !== lastExamType) {
        [reading, listening, writing, speaking, overall].forEach((el) => { if (el) el.value = ""; });
        lastExamType = next;
      }
      renderCambridgeExtra();
    }

    // Wire listeners
    document.addEventListener("change", (evt) => {
      const t = evt.target;
      if (!t) return;
      if (t.name === hasExamName) renderExamDetails();
      if (t === examTypeSel)      onExamTypeChanged();
      if (t === override)         applyRequiredRules();
    });

    // Initial paint
    renderExamDetails();
    renderCambridgeExtra();
    applyRequiredRules();

    // ── Client-side block + scroll-to-first-invalid ────────────────
    const profileForm =
      document.querySelector("form#profile-form") ||
      document.querySelector("form[action*='profiles']") ||
      document.querySelector("form");

    if (profileForm) {
      profileForm.addEventListener(
        "submit",
        (e) => {
          // Make sure required flags are correct at submit time
          applyRequiredRules();

          // If the browser thinks it's invalid, stop and scroll
          if (!profileForm.reportValidity()) {
            e.preventDefault();
            const firstInvalid = profileForm.querySelector(":invalid");
            if (firstInvalid) {
              try { firstInvalid.focus({ preventScroll: true }); } catch {}
              firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
            }
          }
        },
        { capture: true }
      );
    }
  });

  // ── highlight invalids on the fly (unchanged) ───────────────────
  document.addEventListener(
    "invalid",
    (evt) => {
      const el = evt.target;
      document.querySelectorAll(".ring-2.ring-red-500").forEach((n) => {
        if (n !== el) n.classList.remove("ring-2", "ring-red-500");
      });
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
