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
    const examDetailsEl     = document.getElementById("exam-details");
    const cambridgeExtraEl  = document.getElementById("cambridge-extra");

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

    function isExamYesSelected() {
      const yesRadio = document.querySelector('input[name="has_recent_english_exam"][value="True"]');
      return !!yesRadio && yesRadio.checked;
    }
    function renderExamDetails() { animatePanel(examDetailsEl, isExamYesSelected()); }

    // ===== DOM helpers ============================================
    const $ = (sel) => document.querySelector(sel);

    // Robust value readers for custom widgets
    function readCustomValue(host) {
      if (!host) return '';
      const attr = host.getAttribute('value');
      if (attr != null && attr !== '') return String(attr);
      if ('value' in host && host.value) { try { return String(host.value); } catch(_) {} }
      const opted =
        host.querySelector('[data-state="checked"]') ||
        host.querySelector('[aria-selected="true"]') ||
        host.querySelector('[role="option"][aria-selected="true"]');
      if (opted) {
        return String(opted.getAttribute('value') || opted.getAttribute('data-value') || (opted.textContent || '')).trim();
      }
      return '';
    }
    function setCustomValue(host, value) {
      if (!host) return;
      try { host.value = value; } catch (_) {}
      host.setAttribute('value', value);
      host.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // ===== Inputs ==================================================
    const reading   = $('#id_reading_score');
    const listening = $('#id_listening_score');
    const writing   = $('#id_writing_score');
    const speaking  = $('#id_speaking_score');
    const overall   = $('#id_overall_score');
    const override  = $('#id_overall_manual_override');

    // Date parts (custom <c-select> hosts)
    const examDayHost   = document.getElementById('id_exam_day');
    const examMonthHost = document.getElementById('id_exam_month');
    const examYearHost  = document.getElementById('id_exam_year');

    // Date mirrors (if present)
    const examDayMirror   = document.querySelector('input[name="exam_day"]');
    const examMonthMirror = document.querySelector('input[name="exam_month"]');
    const examYearMirror  = document.querySelector('input[name="exam_year"]');

    // Cambridge extras
    const cambridgeGradeHost  = document.getElementById('id_cambridge_grade');
    const cambridgeGradeMirror = document.querySelector('#mirror_cambridge_grade') || document.querySelector('input[name="cambridge_grade"]');
    const cambridgeUoE        = document.getElementById('id_cambridge_use_of_english');

    // Exam type sources
    const examTypeEl      = document.getElementById('id_exam_type');
    const examTypeWidget  = document.getElementById('id_exam_type_widget');
    const hiddenExam      = document.querySelector('input[type="hidden"][name="exam_type"]');
    const nativeSelect    = document.querySelector('select[name="exam_type"]');

    const EXAM_RULES = {
      ielts: { subMin: 0,   subMax: 9,   subStep: 0.5, overallMin: 0,   overallMax: 9,   overallKind: 'avg_half' },
      toefl: { subMin: 0,   subMax: 30,  subStep: 1,   overallMin: 0,   overallMax: 120, overallKind: 'sum' },
      c1:    { subMin: 160, subMax: 210, subStep: 1,   overallMin: 160, overallMax: 210, overallKind: 'avg_int' },
      c2:    { subMin: 200, subMax: 230, subStep: 1,   overallMin: 200, overallMax: 230, overallKind: 'avg_int' },
    };

    function getExamType() {
      if (hiddenExam && hiddenExam.value) return hiddenExam.value.toLowerCase();
      if (nativeSelect && nativeSelect.value) return nativeSelect.value.toLowerCase();
      const hostVal = readCustomValue(examTypeEl) || readCustomValue(examTypeWidget);
      return (hostVal || '').toLowerCase();
    }

    // ===== math helpers ===========================================
    function num(el) {
      if (!el) return null;
      const v = String(el.value ?? '').trim();
      if (v === '') return null;
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    }
    const roundHalf = (x) => Math.round(x * 2) / 2;
    const clamp     = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
    function snapToStep(value, step, min, max) {
      if (value == null) return null;
      const snapped = Math.round((value - min) / step) * step + min;
      const fixed   = step === 1 ? Math.round(snapped) : Math.round(snapped * 2) / 2;
      return clamp(fixed, min, max);
    }

    // ===== rules / compute ========================================
    function applyExamRules() {
      const et = getExamType();
      const rules = EXAM_RULES[et];
      if (!rules) return;
      const setAttrs = (el, min, max, step) => {
        if (!el) return;
        el.setAttribute('min',  String(min));
        el.setAttribute('max',  String(max));
        el.setAttribute('step', String(step));
        el.setAttribute('placeholder', `${min}–${max}`);
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
      const rules = EXAM_RULES[getExamType()];
      if (!rules || !el) return;
      const v = num(el);
      if (v == null) return;
      const fixed = snapToStep(v, rules.subStep, rules.subMin, rules.subMax);
      if (fixed !== v) el.value = String(fixed);
    }

    function cleanOverallIfManual() {
      const rules = EXAM_RULES[getExamType()];
      if (!rules || !overall || !override || !override.checked) return;
      const v = num(overall);
      if (v == null) return;
      const step  = (rules.overallKind === 'avg_half') ? 0.5 : 1;
      const fixed = snapToStep(v, step, rules.overallMin, rules.overallMax);
      if (fixed !== v) overall.value = String(fixed);
    }

    function computeOverallIfNeeded() {
      if (!overall || !reading || !listening || !writing || !speaking) return;
      const rules = EXAM_RULES[getExamType()];
      if (!rules) return;
      const r = num(reading), l = num(listening), w = num(writing), s = num(speaking);
      if (r == null || l == null || w == null || s == null) return;
      if (override && override.checked) return;
      let val;
      if (rules.overallKind === 'sum')           val = r + l + w + s;
      else if (rules.overallKind === 'avg_half') val = roundHalf((r + l + w + s) / 4);
      else                                       val = Math.round((r + l + w + s) / 4);
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

    // Hard-reset a ShadCN/cotton <c-select> by cloning it with an empty value.
    // This resets its internal selected state and trigger text.
    function resetCottonSelectById(id) {
      const el = document.getElementById(id);
      if (!el) return;
      const clone = el.cloneNode(true);
      clone.setAttribute("value", "");   // no selection
      el.replaceWith(clone);
    }

    // Soft-set a cotton select's value (won't always change the UI)
    function setCottonValueById(id, value) {
      const el = document.getElementById(id);
      if (!el) return;
      try { el.value = value; } catch (_) {}
      el.setAttribute("value", value);
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }


    // ===== NEW: clear EVERYTHING exam-related on type change =======
    function clearAllExamInputs() {
      // scores
      const scoreIds = [
        "id_reading_score",
        "id_listening_score",
        "id_writing_score",
        "id_speaking_score",
        "id_overall_score",
      ];
      scoreIds.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });

      // manual override OFF (fires change so your readonly logic runs)
      const override = document.getElementById("id_overall_manual_override");
      if (override) {
        const was = override.checked;
        override.checked = false;
        if (was) override.dispatchEvent(new Event("change", { bubbles: true }));
      }

      // date parts — reset both the visible <c-select> and any hidden mirrors
      // (hosts)
      ["id_exam_day", "id_exam_month", "id_exam_year"].forEach((id) => {
        // hard reset UI to placeholder
        resetCottonSelectById(id);
      });
      // (mirrors)
      ["exam_day", "exam_month", "exam_year"].forEach((name) => {
        const m = document.querySelector(`input[name="${name}"]`);
        if (m) {
          const prev = m.value;
          m.value = "";
          if (prev !== "") m.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });

      // Cambridge extras — **hard reset** the ShadCN select + clear mirrors
      resetCottonSelectById("id_cambridge_grade");          // UI reset
      const gradeMirror =
        document.querySelector("#mirror_cambridge_grade") ||
        document.querySelector('input[name="cambridge_grade"]');
      if (gradeMirror) {
        const prev = gradeMirror.value;
        gradeMirror.value = "";
        if (prev !== "") gradeMirror.dispatchEvent(new Event("change", { bubbles: true }));
      }
      const uoe = document.getElementById("id_cambridge_use_of_english");
      if (uoe) uoe.value = "";
    }


    function renderCambridgeExtra() {
      const et = getExamType();
      const show = et === "c1" || et === "c2";
      animatePanel(cambridgeExtraEl, show);
    }

    // Track exam-type changes robustly; clear on ANY change to a different type
    let lastExamType = getExamType() || null;

    function onExamTypeChangedHard() {
      const et = getExamType();
      if (!et) return;
      if (lastExamType && et !== lastExamType) {
        // Clear ALL exam inputs whenever we switch to a different exam
        clearAllExamInputs();
      }
      lastExamType = et;
      applyExamRules();
      computeOverallIfNeeded();
      renderCambridgeExtra();
      setTimeout(renderCambridgeExtra, 0);
    }

    // ── Listeners (no duplicates) ─────────────────────────────────
    document.addEventListener("input", (evt) => {
      const t = evt.target;
      if (t === reading || t === listening || t === writing || t === speaking) {
        cleanSubscore(t); computeOverallIfNeeded(); return;
      }
      if (t === overall)  { cleanOverallIfManual(); return; }
      if (t === override) { syncOverrideState();    return; }
    });

    document.addEventListener("change", (evt) => {
      const t = evt.target;
      if (t && t.name === "has_recent_english_exam") renderExamDetails();
      if (t === override) syncOverrideState();
      if (t && (t.name === "exam_type" || t.id === "id_exam_type" || t.id === "id_exam_type_widget")) {
        onExamTypeChangedHard();
      }
    });

    // Observe possible sources of exam type changes (custom + mirrors)
    const observeAttr = (el) => { if (!el) return;
      new MutationObserver(onExamTypeChangedHard).observe(el, { attributes: true, attributeFilter: ["value"] });
      el.addEventListener('input', onExamTypeChangedHard);
      el.addEventListener('change', onExamTypeChangedHard);
    };
    observeAttr(examTypeEl);
    observeAttr(examTypeWidget);
    observeAttr(hiddenExam);
    if (nativeSelect) {
      nativeSelect.addEventListener('change', onExamTypeChangedHard);
      nativeSelect.addEventListener('input',  onExamTypeChangedHard);
    }

    // Short-lived polling to cover first paint race conditions
    let poll = 0;
    const id = setInterval(() => {
      onExamTypeChangedHard();
      if (++poll > 10) clearInterval(id);
    }, 500);

    // Initial bootstrap
    onExamTypeChangedHard();
    syncOverrideState();
    computeOverallIfNeeded();
    renderCambridgeExtra();
    renderExamDetails();
  });
})();
