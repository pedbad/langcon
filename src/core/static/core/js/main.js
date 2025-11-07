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

    // ===== Panels (animated) ======================================
    const examDetailsEl     = document.getElementById("exam-details");
    const cambridgeExtraEl  = document.getElementById("cambridge-extra");

    function isExamYesSelected() {
      const yesRadio = document.querySelector('input[name="has_recent_english_exam"][value="True"]');
      return !!yesRadio && yesRadio.checked;
    }

    function animatePanel(el, show) {
      if (!el) return;
      el.dataset.open = show ? "true" : "false";
      el.setAttribute("aria-hidden", show ? "false" : "true"); // <-- add this

      if (show) {
        el.style.overflow  = "hidden";
        el.style.maxHeight = el.scrollHeight + "px";
        el.style.opacity   = "1";
        const done = () => {
          el.style.maxHeight = "none";
          el.style.overflow  = "visible";
          el.removeEventListener("transitionend", done);
        };
        el.addEventListener("transitionend", done);
      } else {
        el.style.overflow  = "hidden";
        el.style.maxHeight = "0px";
        el.style.opacity   = "0";
      }
    }


    function renderExamDetails() {
      animatePanel(examDetailsEl, isExamYesSelected());
    }

    function renderCambridgeExtra() {
      // Show extra panel for Cambridge C1/C2
      const et = getExamType();
      const show = et === "c1" || et === "c2";
      animatePanel(cambridgeExtraEl, show);
    }

    // ===== Exam Scores: dynamic ranges + overall auto-calc =========
    const $ = (sel) => document.querySelector(sel);

    // Inputs
    const reading   = $('#id_reading_score');
    const listening = $('#id_listening_score');
    const writing   = $('#id_writing_score');
    const speaking  = $('#id_speaking_score');
    const overall   = $('#id_overall_score');
    const override  = $('#id_overall_manual_override');

    // Exam type (ShadCN <c-select> and/or hidden mirror)
    const examTypeEl = $('#id_exam_type');
    const hiddenExam = document.querySelector('input[type="hidden"][name="exam_type"]');

    const EXAM_RULES = {
      ielts: { subMin: 0,   subMax: 9,   subStep: 0.5, overallMin: 0,   overallMax: 9,   overallKind: 'avg_half' },
      toefl: { subMin: 0,   subMax: 30,  subStep: 1,   overallMin: 0,   overallMax: 120, overallKind: 'sum' },
      c1:    { subMin: 160, subMax: 210, subStep: 1,   overallMin: 160, overallMax: 210, overallKind: 'avg_int' },
      c2:    { subMin: 200, subMax: 230, subStep: 1,   overallMin: 200, overallMax: 230, overallKind: 'avg_int' },
    };

    function getExamType() {
      // 1) native select (if present)
      const native = document.querySelector('select[name="exam_type"]');
      if (native && native.value) return native.value.toLowerCase();

      // 2) ShadCN <c-select id="id_exam_type" value="...">
      if (examTypeEl) {
        const v = examTypeEl.getAttribute('value') || examTypeEl.value || '';
        if (v) return String(v).toLowerCase();
      }

      // 3) hidden mirror input
      if (hiddenExam && hiddenExam.value) return hiddenExam.value.toLowerCase();

      return '';
    }

    // Helpers
    function num(el) {
      if (!el) return null;
      const v = String(el.value ?? '').trim();
      if (v === '') return null;
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    }
    const roundHalf = (x) => Math.round(x * 2) / 2;
    const clamp     = (x, lo, hi) => Math.max(lo, Math.min(hi, x));

    // Snap to step and clamp to range
    function snapToStep(value, step, min, max) {
      if (value == null) return null;
      const snapped = Math.round((value - min) / step) * step + min;
      const fixed   = step === 1 ? Math.round(snapped) : Math.round(snapped * 2) / 2;
      return clamp(fixed, min, max);
    }

    function applyExamRules() {
      const et = getExamType();
      const rules = EXAM_RULES[et];
      if (!rules) return;

      const setAttrs = (el, min, max, step) => {
        if (!el) return;
        el.setAttribute('min',  String(min));
        el.setAttribute('max',  String(max));
        el.setAttribute('step', String(step));
        el.setAttribute('placeholder', `${min}–${max}`); // en dash
      };

      setAttrs(reading,   rules.subMin, rules.subMax, rules.subStep);
      setAttrs(listening, rules.subMin, rules.subMax, rules.subStep);
      setAttrs(writing,   rules.subMin, rules.subMax, rules.subStep);
      setAttrs(speaking,  rules.subMin, rules.subMax, rules.subStep);

      if (overall) {
        overall.setAttribute('aria-description', `Overall range ${rules.overallMin}–${rules.overallMax}`);
      }
    }

    function cleanSubscore(el) {
      const et = getExamType();
      const rules = EXAM_RULES[et];
      if (!rules || !el) return;
      const v = num(el);
      if (v == null) return;
      const fixed = snapToStep(v, rules.subStep, rules.subMin, rules.subMax);
      if (fixed !== v) el.value = String(fixed);
    }

    function cleanOverallIfManual() {
      const et = getExamType();
      const rules = EXAM_RULES[et];
      if (!rules || !overall || !override || !override.checked) return;
      const v = num(overall);
      if (v == null) return;
      const step  = (rules.overallKind === 'avg_half') ? 0.5 : 1;
      const fixed = snapToStep(v, step, rules.overallMin, rules.overallMax);
      if (fixed !== v) overall.value = String(fixed);
    }

    function computeOverallIfNeeded() {
      if (!overall || !reading || !listening || !writing || !speaking) return;

      const et = getExamType();
      const rules = EXAM_RULES[et];
      if (!rules) return;

      const r = num(reading);
      const l = num(listening);
      const w = num(writing);
      const s = num(speaking);

      if (r == null || l == null || w == null || s == null) return; // need all 4
      if (override && override.checked) return;                      // respect manual

      let val;
      if (rules.overallKind === 'sum')       val = r + l + w + s;
      else if (rules.overallKind === 'avg_half') val = roundHalf((r + l + w + s) / 4);
      else                                    val = Math.round((r + l + w + s) / 4);

      overall.value = String(clamp(val, rules.overallMin, rules.overallMax));
    }

    function syncOverrideState() {
      if (!overall || !override) return;
      if (override.checked) {
        overall.removeAttribute('readonly');
        overall.removeAttribute('aria-readonly');
      } else {
        overall.setAttribute('readonly', 'true');
        overall.setAttribute('aria-readonly', 'true');
        computeOverallIfNeeded();
      }
    }

    // Track exam-type changes robustly
    let lastExamType = null;
    function maybeApplyExamRules() {
      const et = getExamType();
      if (et && et !== lastExamType) {
        lastExamType = et;
        applyExamRules();
        computeOverallIfNeeded();
        renderCambridgeExtra();
        // Re-run after layout settles to get correct scrollHeight for animations
        setTimeout(renderCambridgeExtra, 0);
      }
    }

    // ── Single, unified listeners (no duplicates) ──────────────────
    document.addEventListener("input", (evt) => {
      const t = evt.target;
      if (!t) return;

      if (t === reading || t === listening || t === writing || t === speaking) {
        cleanSubscore(t);
        computeOverallIfNeeded();
        return;
      }

      if (t === overall)  { cleanOverallIfManual(); return; }
      if (t === override) { syncOverrideState();    return; }
    });

    document.addEventListener("change", (evt) => {
      const t = evt.target;
      if (!t) return;

      if (t.name === "has_recent_english_exam") { renderExamDetails();  return; }
      if (t.name === "exam_type")               { maybeApplyExamRules(); return; }
      if (t === override)                       { syncOverrideState();   return; }
    });

    // Observe ShadCN <c-select> and hidden mirror input
    const onExamTypeChanged = () => { maybeApplyExamRules(); };

    if (examTypeEl) {
      const obsSel = new MutationObserver(onExamTypeChanged);
      obsSel.observe(examTypeEl, { attributes: true, attributeFilter: ["value"] });
    }
    if (hiddenExam) {
      hiddenExam.addEventListener("input",  onExamTypeChanged);
      hiddenExam.addEventListener("change", onExamTypeChanged);
      const obsHidden = new MutationObserver(onExamTypeChanged);
      obsHidden.observe(hiddenExam, { attributes: true, childList: true, characterData: true });
    }

    // Short-lived polling to cover first paint race conditions
    let poll = 0;
    const id = setInterval(() => {
      maybeApplyExamRules();
      if (++poll > 10) clearInterval(id); // ~5s
    }, 500);

    // Initial bootstrap
    maybeApplyExamRules();
    syncOverrideState();
    computeOverallIfNeeded();
    renderCambridgeExtra();
    renderExamDetails();
  });
})();
