(function () {
  // ────────────────────────────────────────────────────────────────
  // 1) Alpine: lightweight theme store (dark / light / system)
  // ────────────────────────────────────────────────────────────────
  document.addEventListener("alpine:init", () => {
    const A = window.Alpine;
    if (!A.store("theme")) {
      const stored = localStorage.getItem("theme") || "system";
      A.store("theme", {
        value: stored,
        systemDark: window.matchMedia("(prefers-color-scheme: dark)").matches,
        set(next) {
          this.value = next;
          localStorage.setItem("theme", next);
          this.apply();
        },
        apply() {
          const useDark =
            this.value === "dark" ||
            (this.value === "system" && this.systemDark);
          document.documentElement.classList.toggle("dark", useDark);
        },
      });
      A.store("theme").apply();
      window
        .matchMedia("(prefers-color-scheme: dark)")
        .addEventListener("change", (e) => {
          A.store("theme").systemDark = e.matches;
          if (A.store("theme").value === "system") A.store("theme").apply();
        });
    }
  });

  // ────────────────────────────────────────────────────────────────
  // 1b) Shared helpers: word count + chip styling
  // ────────────────────────────────────────────────────────────────
  const countWords = (s) => {
    s = (s || "").trim();
    return s ? s.split(/\s+/).filter(Boolean).length : 0;
  };

  function styleWordChip(chipEl, n, maxWords, warningThreshold) {
    if (!chipEl) return;

    chipEl.textContent = `${n} / ${maxWords} words`;

    // neutral styling
    chipEl.classList.remove("text-red-600", "border-red-600", "bg-red-50");
    chipEl.classList.add("text-slate-700", "border-slate-400", "bg-slate-50");

    // warning tint near upper limit
    if (n >= warningThreshold) {
      chipEl.classList.remove(
        "text-slate-700",
        "border-slate-400",
        "bg-slate-50"
      );
      chipEl.classList.add("text-red-600", "border-red-600", "bg-red-50");
    }
  }

  // ────────────────────────────────────────────────────────────────
  // 2) Module: Assessment Writing (word count, toast, submit toggle)
  // ────────────────────────────────────────────────────────────────
  function initAssessmentsWriting() {
    const writingTa = document.getElementById("id_writing_answer");
    const wordChip = document.getElementById("word-count");
    const submitBtn = document.getElementById("submit-writing");
    const warnToast = document.getElementById("client-word-warning");
    const warnToastText = warnToast
      ? warnToast.querySelector("[data-role='word-warning-text']")
      : null;
    const actionField = document.getElementById("assessment-action");
    const submitStatus = document.getElementById("submit-status");

    if (!writingTa || !wordChip) return;

    const MIN = 250;
    const MAX = 300;
    const WARNING = 295;

    const showClientWarning = (show, text) => {
      if (!warnToast) return;
      if (show) {
        if (text && warnToastText) warnToastText.textContent = text;
        warnToast.classList.remove("hidden");
      } else {
        warnToast.classList.add("hidden");
      }
    };

    const setSubmitEnabled = (enabled) => {
      if (!submitBtn) return;
      submitBtn.disabled = !enabled;
      submitBtn.setAttribute("aria-disabled", String(!enabled));
      submitBtn.classList.toggle("opacity-60", !enabled);
      submitBtn.classList.toggle("cursor-not-allowed", !enabled);
    };

    // When we manually block an invalid submit, we don't want auto-hide
    let manualWarning = false;

    // ────────────────────────────────────────────────────────────────
    //  HTMX submit guard for 250–300 words
    // ────────────────────────────────────────────────────────────────
    if (actionField && submitBtn) {
      submitBtn.addEventListener(
        "click",
        (evt) => {
          const n = countWords(writingTa.value);

          if (n < MIN || n > MAX) {
            // BLOCK HTMX
            evt.preventDefault();
            evt.stopPropagation();

            // Clear any fake “submitting” banner
            if (submitStatus) submitStatus.classList.add("hidden");

            // Mark that we are showing a manual warning
            manualWarning = true;

            // Show strong client warning
            showClientWarning(
              true,
              `Your answer is ${n} words. It must be between ${MIN} and ${MAX} words to submit.`
            );

            // Re-enable Submit button
            submitBtn.disabled = false;
            submitBtn.setAttribute("aria-disabled", "false");
            submitBtn.classList.remove("opacity-60", "cursor-not-allowed");

            return; // stop here — NO POST
          }

          // If valid → allow HTMX, set action to "submit"
          actionField.value = "submit";

          if (submitStatus) {
            submitStatus.classList.remove("hidden");
          }

          // Lock button
          submitBtn.disabled = true;
          submitBtn.setAttribute("aria-disabled", "true");
          submitBtn.classList.add("opacity-60", "cursor-not-allowed");
        },
        { capture: true } // ensure we run before HTMX’s bubbling handler
      );
    }

    const renderCount = (evt) => {
      const n = countWords(writingTa.value);

      // If the user is typing, clear any manual warning flag
      if (evt && evt.type === "input") {
        manualWarning = false;
      }

      styleWordChip(wordChip, n, MAX, WARNING);

      // live client warning: only > MAX; short answers are allowed to *attempt* submit
      if (n > MAX) {
        showClientWarning(
          true,
          "Your answer exceeds 300 words. You can still save a draft, but you must reduce it to 300 words to submit."
        );
        setSubmitEnabled(false);
      } else {
        // Only auto-hide the toast if we DON'T have a manual warning active
        if (!manualWarning) {
          showClientWarning(false);
        }
        setSubmitEnabled(true);
      }
    };

    // Initial paint + listeners
    renderCount();
    writingTa.addEventListener("input", renderCount);
    writingTa.addEventListener("change", renderCount);
  }

  // ────────────────────────────────────────────────────────────────
  // 2b) Shared helper: LLM Question modules (Q1, Q2)
  // ────────────────────────────────────────────────────────────────
  function initLlmQuestionModule(config) {
    const {
      textareaId,
      chipId,
      submitBtnId,
      actionFieldId,
      submitActionValue,
      spinnerId,
      warnToastId,
      warnTextDataAttr,
      minWords = 250,
      maxWords = 300,
      warningThreshold = 295,
    } = config;

    const ta = document.getElementById(textareaId);
    const chip = document.getElementById(chipId);
    const submitBtn = document.getElementById(submitBtnId);
    const actionField = document.getElementById(actionFieldId);
    const spinner = spinnerId ? document.getElementById(spinnerId) : null;
    const warnToast = document.getElementById(warnToastId);
    const warnToastText =
      warnToast && warnTextDataAttr
        ? warnToast.querySelector(warnTextDataAttr)
        : null;

    // If we're not on this card, bail out quietly
    if (!ta || !chip) return;

    const MIN = minWords;
    const MAX = maxWords;
    const WARNING = warningThreshold;

    const showClientWarning = (show, text) => {
      if (!warnToast) return;
      if (show) {
        if (text && warnToastText) warnToastText.textContent = text;
        warnToast.classList.remove("hidden");
      } else {
        warnToast.classList.add("hidden");
      }
    };

    const setSubmitEnabled = (enabled) => {
      if (!submitBtn) return;
      submitBtn.disabled = !enabled;
      submitBtn.setAttribute("aria-disabled", String(!enabled));
      submitBtn.classList.toggle("opacity-60", !enabled);
      submitBtn.classList.toggle("cursor-not-allowed", !enabled);
    };

    const renderCount = () => {
      const n = countWords(ta.value);
      styleWordChip(chip, n, MAX, WARNING);

      // live warning + disable submit if outside [MIN, MAX]
      if (n < MIN || n > MAX) {
        showClientWarning(
          true,
          "Your answer must be between 250 and 300 words to submit. You can still save a draft."
        );
        setSubmitEnabled(false);
      } else {
        showClientWarning(false);
        setSubmitEnabled(true);
      }
    };

    // Initial render + live updates
    renderCount();
    ta.addEventListener("input", renderCount);
    ta.addEventListener("change", renderCount);

    // HTMX submit + hard client-side enforcement
    if (submitBtn && actionField) {
      submitBtn.addEventListener(
        "click",
        (evt) => {
          const n = countWords(ta.value);

          if (n < MIN || n > MAX) {
            // BLOCK HTMX
            evt.preventDefault();
            evt.stopPropagation();

            // Ensure spinner is hidden
            if (spinner) spinner.classList.add("hidden");

            // Strong warning with exact word count
            showClientWarning(
              true,
              `Your answer is ${n} words. It must be between ${MIN} and ${MAX} words to submit.`
            );

            setSubmitEnabled(false);
            return; // ❌ no POST
          }

          // ✅ Valid → set action to the configured submit value and let HTMX POST
          actionField.value = submitActionValue;

          if (spinner) {
            spinner.classList.remove("hidden");
          }

          // HTMX will reload the page; we just keep the state consistent
          setSubmitEnabled(true);
        },
        { capture: true } // run before HTMX to be able to block it
      );
    }
  }

  // Thin wrappers for clarity / backwards compatibility
  function initAssessmentLlmQuestion1() {
    initLlmQuestionModule({
      textareaId: "id_llm_question_1_answer",
      chipId: "llm-q1-word-count",
      submitBtnId: "submit-llm-q1",
      actionFieldId: "q1-action",
      submitActionValue: "q1_submit",
      spinnerId: "q1-submit-status",
      warnToastId: "q1-client-word-warning",
      warnTextDataAttr: "[data-role='q1-word-warning-text']",
      minWords: 250,
      maxWords: 300,
      warningThreshold: 295,
    });
  }

  function initAssessmentLlmQuestion2() {
    initLlmQuestionModule({
      textareaId: "id_llm_question_2_answer",
      chipId: "llm-q2-word-count",
      submitBtnId: "submit-llm-q2",
      actionFieldId: "q2-action",
      submitActionValue: "q2_submit",
      spinnerId: "q2-submit-status",
      warnToastId: "q2-client-word-warning",
      warnTextDataAttr: "[data-role='q2-word-warning-text']",
      minWords: 250,
      maxWords: 300,
      warningThreshold: 295,
    });
  }

  // ────────────────────────────────────────────────────────────────
  // 3) Module: Profile Exam Form (panels, exam rules, auto overall)
  // ────────────────────────────────────────────────────────────────
  function initProfileExamForm() {
    // Panels that expand/collapse with smooth height/opacity
    const examDetailsEl = document.getElementById("exam-details");
    const cambridgeExtraEl = document.getElementById("cambridge-extra");

    // Smooth show/hide helper for the panels above
    function animatePanel(el, show) {
      if (!el) return;
      el.dataset.open = show ? "true" : "false";
      el.setAttribute("aria-hidden", show ? "false" : "true");
      if (show) {
        el.style.overflow = "hidden";
        el.style.maxHeight = el.scrollHeight + "px";
        el.style.opacity = "1";
        const done = () => {
          el.style.maxHeight = "none";
          el.style.overflow = "visible";
          el.removeEventListener("transitionend", done);
        };
        el.addEventListener("transitionend", done);
      } else {
        el.style.overflow = "hidden";
        el.style.maxHeight = "0px";
        el.style.opacity = "0";
      }
    }

    // Small helpers
    const $ = (sel) => document.querySelector(sel);
    const getCheckedValue = (name) => {
      const el = document.querySelector(`input[name="${name}"]:checked`);
      return el ? el.value : null;
    };

    // Names/refs for inputs we care about
    const hasExamName = "has_recent_english_exam";

    const examTypeSel = $('select[name="exam_type"]');
    const examDay = $("#id_exam_day");
    const examMonth = $("#id_exam_month");
    const examYear = $("#id_exam_year");

    const reading = $("#id_reading_score");
    const listening = $("#id_listening_score");
    const writing = $("#id_writing_score");
    const speaking = $("#id_speaking_score");
    const overall = $("#id_overall_score");
    const override = $("#id_overall_manual_override");

    // Cambridge only fields
    const camGrade = $("#id_cambridge_grade");
    const camUse = $("#id_cambridge_use_of_english"); // optional

    const profileForm =
      document.querySelector("form#profile-form") ||
      document.querySelector("form[action*='profiles']") ||
      document.querySelector("form");
    const formReadOnly = profileForm?.dataset?.readonly === "true";
    if (formReadOnly) {
      // Form is locked; skip interactive behavior.
      return;
    }

    // 3.a) HTML5 required flags (so reportValidity() behaves correctly)
    const setRequired = (el, on) => {
      if (!el) return;
      if (on) el.setAttribute("required", "required");
      else el.removeAttribute("required");
    };
    const isCambridge = (et) => et === "c1" || et === "c2";
    const currentExamType = () =>
      (examTypeSel && examTypeSel.value ? examTypeSel.value : "").toLowerCase();

    function applyRequiredRules() {
      const hasExam = getCheckedValue(hasExamName) === "True";

      // When the student has taken an exam, date/type + all subs become required
      setRequired(examTypeSel, hasExam);
      setRequired(examDay, hasExam);
      setRequired(examMonth, hasExam);
      setRequired(examYear, hasExam);
      setRequired(reading, hasExam);
      setRequired(listening, hasExam);
      setRequired(writing, hasExam);
      setRequired(speaking, hasExam);

      // Overall is only required if they're manually overriding it
      const needOverall = hasExam && override && override.checked === true;
      setRequired(overall, needOverall);

      // Cambridge grade is required only for C1/C2 when hasExam is True
      setRequired(camGrade, hasExam && isCambridge(currentExamType()));

      // Cambridge "Use of English" is optional (never force required)
      if (camUse) camUse.removeAttribute("required");
    }

    // 3.b) Panel rendering + clearing helpers
    function clearExamEverything() {
      if (examTypeSel) examTypeSel.value = "";
      if (examDay) examDay.value = "";
      if (examMonth) examMonth.value = "";
      if (examYear) examYear.value = "";

      [reading, listening, writing, speaking, overall].forEach((el) => {
        if (el) el.value = "";
      });
      if (override) override.checked = false;

      if (camGrade) camGrade.value = "";
      if (camUse) camUse.value = "";
    }

    function renderExamDetails() {
      const v = getCheckedValue(hasExamName);
      const show = v === "True";
      animatePanel(examDetailsEl, show);
      if (!show) {
        // If the student selects “No”, wipe any stray values and close Cambridge extras.
        clearExamEverything();
        animatePanel(cambridgeExtraEl, false);
      }
      applyRequiredRules();
      // Re-apply exam rules (placeholders/min/max) whenever the big toggle changes
      applyExamRules();
      computeOverallIfNeeded();
    }

    function renderCambridgeExtra() {
      const et = currentExamType();
      const show = isCambridge(et);
      animatePanel(cambridgeExtraEl, show);
      if (!show) {
        // Leaving C1/C2 → clear its extras so nothing sneaks into POST
        if (camGrade) camGrade.value = "";
        if (camUse) camUse.value = "";
      }
      applyRequiredRules();
    }

    // When switching exam type, wipe sub-scores/overall so user re-enters valid values
    let lastExamType = currentExamType();
    function onExamTypeChanged() {
      const next = currentExamType();
      if (next !== lastExamType) {
        [reading, listening, writing, speaking, overall].forEach((el) => {
          if (el) el.value = "";
        });
        lastExamType = next;
      }
      renderCambridgeExtra();
      applyExamRules();
      computeOverallIfNeeded();
    }

    // 3.c) Dynamic exam rules: placeholders, min/max/step, auto-overall
    const EXAM_RULES = {
      ielts: {
        subMin: 0,
        subMax: 9,
        subStep: 0.5,
        overallMin: 0,
        overallMax: 9,
        overallKind: "avg_half",
      },
      toefl: {
        subMin: 0,
        subMax: 30,
        subStep: 1,
        overallMin: 0,
        overallMax: 120,
        overallKind: "sum",
      },
      c1: {
        subMin: 160,
        subMax: 210,
        subStep: 1,
        overallMin: 160,
        overallMax: 210,
        overallKind: "avg_int",
      },
      c2: {
        subMin: 200,
        subMax: 230,
        subStep: 1,
        overallMin: 200,
        overallMax: 230,
        overallKind: "avg_int",
      },
    };

    const toNum = (el) => {
      if (!el) return null;
      const v = String(el.value ?? "").trim();
      if (v === "") return null;
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    };
    const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
    const roundHalf = (x) => Math.round(x * 2) / 2;

    // Apply per-exam ranges/steps and informative placeholders to sub-score inputs
    function applyExamRules() {
      if (!examTypeSel) return;
      const et = (examTypeSel.value || "").toLowerCase();
      const rules = EXAM_RULES[et];
      if (!rules) return;

      const setAttrs = (el) => {
        if (!el) return;
        el.setAttribute("min", String(rules.subMin));
        el.setAttribute("max", String(rules.subMax));
        el.setAttribute("step", String(rules.subStep));

        // IELTS → show “0–9 (0.5 steps)”
        // all others → show “0–30”, “160–210”, etc.
        let ph = `${rules.subMin}–${rules.subMax}`;
        if (et === "ielts") ph += ` (${rules.subStep} steps)`;
        el.setAttribute("placeholder", ph);
      };

      setAttrs(reading);
      setAttrs(listening);
      setAttrs(writing);
      setAttrs(speaking);

      if (overall) {
        overall.setAttribute(
          "aria-description",
          `Overall range ${rules.overallMin}–${rules.overallMax}`
        );
      }
    }

    // Snap a sub-score to the nearest allowed step and clamp to range
    function cleanSubscore(el) {
      if (!el || !examTypeSel) return;
      const et = (examTypeSel.value || "").toLowerCase();
      const rules = EXAM_RULES[et];
      if (!rules) return;

      const v = toNum(el);
      if (v == null) return;

      // Step snapping from the lower bound. For IELTS step=0.5; for others step=1
      const step = rules.subStep;
      const snapped =
        Math.round((v - rules.subMin) / step) * step + rules.subMin;
      const fixed =
        step === 1 ? Math.round(snapped) : Math.round(snapped * 2) / 2;
      const clamped = clamp(fixed, rules.subMin, rules.subMax);

      if (clamped !== v) el.value = String(clamped);
    }

    // Compute overall from subs unless manual override is enabled
    function computeOverallIfNeeded() {
      if (!overall || !examTypeSel) return;

      const et = (examTypeSel.value || "").toLowerCase();
      const rules = EXAM_RULES[et];
      if (!rules) return;

      const r = toNum(reading);
      const l = toNum(listening);
      const w = toNum(writing);
      const s = toNum(speaking);

      // need all four sub-scores present
      if (r == null || l == null || w == null || s == null) return;

      // if overriding, do nothing—user controls overall directly
      if (override && override.checked) return;

      let val;
      if (rules.overallKind === "sum") {
        val = r + l + w + s; // TOEFL
      } else if (rules.overallKind === "avg_half") {
        val = roundHalf((r + l + w + s) / 4); // IELTS → nearest 0.5
      } else {
        val = Math.round((r + l + w + s) / 4); // C1/C2 → nearest integer
      }

      overall.value = String(clamp(val, rules.overallMin, rules.overallMax));
    }

    // Keep the “overall” input readonly unless manual override is ticked
    function syncOverrideState() {
      if (!overall || !override) return;
      if (override.checked) {
        overall.removeAttribute("readonly");
        overall.removeAttribute("aria-readonly");
      } else {
        overall.setAttribute("readonly", "true");
        overall.setAttribute("aria-readonly", "true");
        computeOverallIfNeeded(); // refresh auto value if the subs are present
      }
      applyRequiredRules(); // overall required only if overriding
    }

    // 3.d) Event wiring
    document.addEventListener("change", (evt) => {
      const t = evt.target;
      if (!t) return;

      if (t.name === hasExamName) {
        renderExamDetails();
        return;
      }

      if (t === examTypeSel) {
        onExamTypeChanged();
        return;
      }

      if (t === override) {
        syncOverrideState();
        return;
      }

      if (t === reading || t === listening || t === writing || t === speaking) {
        cleanSubscore(t);
        computeOverallIfNeeded();
      }
    });

    // Live input: snap sub-scores to valid steps and recompute overall
    document.addEventListener("input", (evt) => {
      const t = evt.target;
      if (!t) return;

      if (t === reading || t === listening || t === writing || t === speaking) {
        computeOverallIfNeeded();
        return;
      }

      if (t === overall && override && override.checked && examTypeSel) {
        // If the user is overriding overall, gently clamp to the right range/step
        const et = (examTypeSel.value || "").toLowerCase();
        const rules = EXAM_RULES[et];
        if (rules) {
          const v = toNum(overall);
          if (v != null) {
            const step = rules.overallKind === "avg_half" ? 0.5 : 1;
            const snapped =
              Math.round((v - rules.overallMin) / step) * step +
              rules.overallMin;
            const fixed =
              step === 1 ? Math.round(snapped) : Math.round(snapped * 2) / 2;
            const clamped = clamp(fixed, rules.overallMin, rules.overallMax);
            if (clamped !== v) overall.value = String(clamped);
          }
        }
      }
    });

    // 3.e) Initial paint
    renderExamDetails(); // opens/closes the big region
    renderCambridgeExtra(); // opens/closes the C1/C2 extras
    applyRequiredRules(); // makes native validation aware
    applyExamRules(); // sets placeholders/min/max/step
    syncOverrideState(); // sets overall readonly appropriately
    computeOverallIfNeeded();

    // 3.f) Client-side “block + scroll-to-first-invalid”
    if (profileForm) {
      profileForm.addEventListener(
        "submit",
        (e) => {
          // Ensure required flags + rules are correct right before submit
          applyRequiredRules();
          applyExamRules();

          // Let the browser do its validity checks; if something’s wrong,
          // prevent the POST and scroll focus to the first offender.
          if (!profileForm.reportValidity()) {
            e.preventDefault();
            const firstInvalid = profileForm.querySelector(":invalid");
            if (firstInvalid) {
              try {
                firstInvalid.focus({ preventScroll: true });
              } catch {}
              firstInvalid.scrollIntoView({
                behavior: "smooth",
                block: "center",
              });
            }
          }
        },
        { capture: true }
      );
    }
  }

  // ────────────────────────────────────────────────────────────────
  // 4) Module: Global UX invalid highlighting
  // ────────────────────────────────────────────────────────────────
  function initGlobalInvalidHighlight() {
    // Highlight the first invalid control on any form
    document.addEventListener(
      "invalid",
      (evt) => {
        const el = evt.target;
        // Remove prior highlights
        document.querySelectorAll(".ring-2.ring-red-500").forEach((n) => {
          if (n !== el) n.classList.remove("ring-2", "ring-red-500");
        });
        // Emphasize current invalid element
        el.classList.add("ring-2", "ring-red-500");
        try {
          el.focus({ preventScroll: true });
        } catch {}
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      },
      true // capture so we run before the browser aborts submit
    );

    // As soon as a field becomes valid again, clear the highlight
    document.addEventListener("input", (evt) => {
      if (evt.target.matches(":valid")) {
        evt.target.classList.remove("ring-2", "ring-red-500");
      }
    });
  }

  // ────────────────────────────────────────────────────────────────
  // 5) App bootstrap + progressive enhancement
  // ────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    window.APP = { env: document.body.dataset.env || "prod" };

    // Each init is safe to call on any page; they no-op if elements are missing.
    initAssessmentsWriting();
    initProfileExamForm();
    initGlobalInvalidHighlight();
    initAssessmentLlmQuestion1();
    initAssessmentLlmQuestion2();

    // ── Respect hash for assessment flow (e.g. #followup-q1-card / #followup-q2-card) ──
    const hash = window.location.hash;
    if (hash) {
      const target = document.querySelector(hash);
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    }
  });
})();
