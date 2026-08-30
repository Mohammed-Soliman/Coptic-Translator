(function () {
  "use strict";
  const { apiPost, debounce, escapeHtml, formatPct } = window.CopticLab;

  const sourceInput = document.getElementById("source-input");
  const targetOutput = document.getElementById("target-output");
  const sourceLabel = document.getElementById("source-label");
  const targetLabel = document.getElementById("target-label");
  const swapBtn = document.getElementById("swap-btn");
  const dialectBohairicBtn = document.getElementById("dialect-bohairic-btn");
  const dialectSahidicBtn = document.getElementById("dialect-sahidic-btn");
  const confidenceFill = document.getElementById("confidence-fill");
  const confidenceLabel = document.getElementById("confidence-label");
  const copySourceBtn = document.getElementById("copy-source-btn");
  const copyTargetBtn = document.getElementById("copy-target-btn");

  const state = {
    direction: "en2cop",
    dialect: "bohairic",
  };

  const ACTIVE_DIALECT_CLASSES = ["bg-terracotta", "text-white"];
  const INACTIVE_DIALECT_CLASSES = ["text-on-surface-variant"];

  function setDialectButtons() {
    const bohairicActive = state.dialect === "bohairic";
    dialectBohairicBtn.classList.toggle("bg-terracotta", bohairicActive);
    dialectBohairicBtn.classList.toggle("text-white", bohairicActive);
    dialectBohairicBtn.classList.toggle("text-on-surface-variant", !bohairicActive);
    dialectSahidicBtn.classList.toggle("bg-terracotta", !bohairicActive);
    dialectSahidicBtn.classList.toggle("text-white", !bohairicActive);
    dialectSahidicBtn.classList.toggle("text-on-surface-variant", bohairicActive);
  }

  function setLabelsForDirection() {
    if (state.direction === "en2cop") {
      sourceLabel.textContent = "Source (English)";
      targetLabel.textContent = "Target (Coptic)";
      targetOutput.classList.add("coptic-glyphs");
      sourceInput.classList.remove("coptic-glyphs");
      sourceInput.placeholder = "Enter text to translate...";
    } else {
      sourceLabel.textContent = "Source (Coptic)";
      targetLabel.textContent = "Target (English)";
      sourceInput.classList.add("coptic-glyphs");
      targetOutput.classList.remove("coptic-glyphs");
      sourceInput.placeholder = "ⲧⲱϣ ⲛⲟⲩⲥⲉϫⲓ ⲛ̀ⲕⲟⲡⲧⲓⲕⲟⲛ...";
    }
  }

  function resetConfidence() {
    confidenceFill.style.width = "0%";
    confidenceLabel.textContent = "—";
  }

  function applyConfidence(validation) {
    if (!validation) {
      resetConfidence();
      return;
    }
    const pct = Math.round(validation.overall * 100);
    confidenceFill.style.width = `${pct}%`;
    confidenceLabel.textContent = `${pct}% ${validation.label}`;
  }

  async function runTranslation() {
    const text = sourceInput.value.trim();
    if (!text) {
      targetOutput.textContent = "";
      resetConfidence();
      return;
    }

    targetOutput.classList.add("opacity-50");
    try {
      const data = await apiPost("/translate", {
        text,
        direction: state.direction,
        dialect: state.dialect,
      });
      targetOutput.textContent = data.output_text;
      applyConfidence(data.validation);
    } catch (err) {
      console.error(err);
      targetOutput.textContent = "";
      targetOutput.innerHTML =
        '<span class="text-error text-body-md">Translation service unavailable — is the API running?</span>';
      resetConfidence();
    } finally {
      targetOutput.classList.remove("opacity-50");
    }
  }

  const debouncedTranslate = debounce(runTranslation, 600);

  sourceInput.addEventListener("input", debouncedTranslate);

  dialectBohairicBtn.addEventListener("click", () => {
    state.dialect = "bohairic";
    setDialectButtons();
    runTranslation();
  });

  dialectSahidicBtn.addEventListener("click", () => {
    state.dialect = "sahidic";
    setDialectButtons();
    runTranslation();
  });

  swapBtn.addEventListener("click", () => {
    state.direction = state.direction === "en2cop" ? "cop2en" : "en2cop";
    setLabelsForDirection();

    const previousOutput = targetOutput.textContent;
    sourceInput.value = previousOutput;
    targetOutput.textContent = "";
    resetConfidence();
    if (previousOutput.trim()) {
      runTranslation();
    }
  });

  function copyToClipboard(text) {
    if (!text) return;
    navigator.clipboard?.writeText(text).catch(() => {});
  }

  copySourceBtn?.addEventListener("click", () => copyToClipboard(sourceInput.value));
  copyTargetBtn?.addEventListener("click", () => copyToClipboard(targetOutput.textContent));

  setDialectButtons();
  setLabelsForDirection();
  resetConfidence();
})();
