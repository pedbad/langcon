// ────────────────────────────────────────────────────────────────
// App bootstrap + progressive enhancement hooks
// ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  console.log("[DOMContentLoaded] fired");
  window.APP = { env: document.body.dataset.env || "prod" };
  console.log("[APP] ready, env =", window.APP.env);

  // =================================================================
  // Feature: Exam Details Toggle (open/close animated panel)
  // =================================================================
  const examDetailsEl = document.getElementById("exam-details");

  function isExamYesSelected() {
    const yesRadio = document.querySelector('input[name="has_recent_english_exam"][value="True"]');
    return !!yesRadio && yesRadio.checked;
  }

  function renderExamDetails() {
    if (!examDetailsEl) return;
    const show = isExamYesSelected();
    examDetailsEl.dataset.open = show ? "true" : "false";
    if (show) {
      examDetailsEl.style.overflow   = "hidden";
      examDetailsEl.style.maxHeight  = examDetailsEl.scrollHeight + "px";
      examDetailsEl.style.opacity    = "1";
      const done = () => {
        examDetailsEl.style.maxHeight = "none";
        examDetailsEl.style.overflow  = "visible";
        examDetailsEl.removeEventListener("transitionend", done);
      };
      examDetailsEl.addEventListener("transitionend", done);
    } else {
      examDetailsEl.style.overflow  = "hidden";
      examDetailsEl.style.maxHeight = "0px";
      examDetailsEl.style.opacity   = "0";
    }
  }

  // =================================================================
  // Feature: Exam Scores — dynamic ranges + overall auto-calc
  // =================================================================
  const $ = (sel) => document.querySelector(sel);

  // Inputs
  const reading   = $('#id_reading_score');
  const listening = $('#id_listening_score');
  const writing   = $('#id_writing_score');
  const speaking  = $('#id_speaking_score');
  const overall   = $('#id_overall_score');
  const override  = $('#id_overall_manual_override');

  // Exam type (ShadCN <c-select id="id_exam_type"> and potential hidden mirror)
  const examTypeEl = $('#id_exam_type');
  const hiddenExam = document.querySelector('input[type="hidden"][name="exam_type"]');

  const EXAM_RULES = {
    ielts: { subMin: 0,   subMax: 9,   subStep: 0.5, overallMin: 0,   overallMax: 9,   overallKind: 'avg_half' },
    toefl: { subMin: 0,   subMax: 30,  subStep: 1,   overallMin: 0,   overallMax: 120, overallKind: 'sum' },
    c1:    { subMin: 160, subMax: 210, subStep: 1,   overallMin: 160, overallMax: 210, overallKind: 'avg_int' },
    c2:    { subMin: 200, subMax: 230, subStep: 1,   overallMin: 200, overallMax: 230, overallKind: 'avg_int' },
  };

  function getExamType() {
    // 1) native select (if used)
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
  function roundHalf(x) { return Math.round(x * 2) / 2; }
  function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

  // Snap to step and clamp to range (handles 0.5 and 1.0 steps)
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

    // Require all four sub-scores
    if (r == null || l == null || w == null || s == null) return;

    // Respect manual override
    if (override && override.checked) return;

    let val;
    if (rules.overallKind === 'sum') {
      val = r + l + w + s;
    } else if (rules.overallKind === 'avg_half') {
      val = roundHalf((r + l + w + s) / 4);
    } else {
      val = Math.round((r + l + w + s) / 4);
    }
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
    }
  }

  // ── Single, unified listeners ────────────────────────────────────
  document.addEventListener("input", (evt) => {
    const t = evt.target;
    if (!t) return;

    // Sub-scores: live snap + compute
    if (t === reading || t === listening || t === writing || t === speaking) {
      cleanSubscore(t);
      computeOverallIfNeeded();
      return;
    }

    // Overall: keep in range if manual
    if (t === overall) {
      cleanOverallIfManual();
      return;
    }

    // Manual override checkbox (rarely fires on input, but cheap)
    if (t === override) {
      syncOverrideState();
      return;
    }
  });

  document.addEventListener("change", (evt) => {
    const t = evt.target;
    if (!t) return;

    // Exam panel toggle (yes/no)
    if (t.name === "has_recent_english_exam") {
      renderExamDetails();
      return;
    }

    // Native select fallback for exam type
    if (t.name === "exam_type") {
      maybeApplyExamRules();
      return;
    }

    if (t === override) {
      syncOverrideState();
      return;
    }
  });

  // Observe ShadCN <c-select> and hidden mirror input
  if (examTypeEl) {
    const obsSel = new MutationObserver(maybeApplyExamRules);
    obsSel.observe(examTypeEl, { attributes: true, attributeFilter: ["value"] });
  }
  if (hiddenExam) {
    hiddenExam.addEventListener("input",  maybeApplyExamRules);
    hiddenExam.addEventListener("change", maybeApplyExamRules);
    const obsHidden = new MutationObserver(maybeApplyExamRules);
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
  renderExamDetails();
});
