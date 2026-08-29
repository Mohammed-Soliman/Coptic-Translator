(function () {
  "use strict";
  const { apiGet, apiPost, escapeHtml } = window.CopticLab;

  const gridEl = document.getElementById("notes-grid");
  const filtersEl = document.getElementById("note-filters");
  const newNoteBtn = document.getElementById("new-note-btn");
  const newNoteForm = document.getElementById("new-note-form");
  const cancelBtn = document.getElementById("cancel-note-btn");
  const titleInput = document.getElementById("new-note-title");
  const categorySelect = document.getElementById("new-note-category");
  const contentInput = document.getElementById("new-note-content");
  const metricLabelInput = document.getElementById("new-note-metric-label");
  const metricValueInput = document.getElementById("new-note-metric-value");

  const CATEGORY_COLORS = {
    Model: "#d4a373",
    Corpus: "#d4a373",
    Grammar: "#d4a373",
    Eval: "#d4a373",
  };

  let activeCategory = "all";

  function formatDate(isoDate) {
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return isoDate;
    return d
      .toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
      .toUpperCase()
      .replace(/ /g, ".");
  }

  function metricBarColor(value) {
    if (value >= 0.7) return "bg-secondary";
    if (value >= 0.4) return "bg-primary";
    return "bg-error";
  }

  function renderCard(note) {
    const hasMetric = note.metric_value !== null && note.metric_value !== undefined;
    const pct = hasMetric ? Math.round(note.metric_value * 100) : 0;
    return `
      <article class="sandstone-bg p-6 rounded-none guilloche-border flex flex-col gap-4">
        <div class="flex justify-between items-start guilloche-corner">
          <span class="text-label-caps font-label-caps text-on-surface-variant opacity-70">${escapeHtml(formatDate(note.date))}</span>
          <span class="bg-[#d4a373] text-[#3a2f2a] px-2 py-1 text-label-caps font-label-caps uppercase border border-[#8a726b]">${escapeHtml(note.category)}</span>
        </div>
        <h2 class="text-headline-md font-headline-md text-primary mt-2">${escapeHtml(note.title)}</h2>
        <p class="text-body-md font-body-md text-on-surface-variant flex-1">${escapeHtml(note.content)}</p>
        ${
          hasMetric
            ? `<div class="mt-4 pt-4 border-t border-outline-variant">
                <div class="flex justify-between mb-1">
                  <span class="text-label-caps font-label-caps text-on-surface-variant">${escapeHtml(note.metric_label || "Metric")}</span>
                  <span class="text-label-caps font-label-caps text-secondary font-bold">${pct}%</span>
                </div>
                <div class="w-full h-2 bg-surface-dim rounded-none overflow-hidden border border-outline-variant relative">
                  <div class="h-full ${metricBarColor(note.metric_value)}" style="width: ${pct}%"></div>
                </div>
              </div>`
            : ""
        }
      </article>`;
  }

  function render(notes) {
    if (notes.length === 0) {
      gridEl.innerHTML =
        '<p class="text-body-md font-body-md text-on-surface-variant col-span-2">No notes in this category yet.</p>';
      return;
    }
    gridEl.innerHTML = notes.map(renderCard).join("");
  }

  async function load() {
    gridEl.innerHTML =
      '<p class="text-body-md font-body-md text-on-surface-variant col-span-2">Loading notes…</p>';
    try {
      const notes = await apiGet("/lab-notes", { category: activeCategory });
      render(notes);
    } catch (err) {
      console.error(err);
      gridEl.innerHTML =
        '<p class="text-body-md font-body-md text-error col-span-2">Lab notes service unavailable — is the API running?</p>';
    }
  }

  filtersEl.querySelectorAll("button[data-category]").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeCategory = btn.dataset.category;
      filtersEl.querySelectorAll("button[data-category]").forEach((b) => {
        const active = b === btn;
        b.classList.toggle("bg-surface-tint", active);
        b.classList.toggle("text-on-primary", active);
        b.classList.toggle("sandstone-bg", !active);
        b.classList.toggle("text-on-surface-variant", !active);
      });
      load();
    });
  });

  function toggleForm(show) {
    newNoteForm.classList.toggle("hidden", !show);
    if (show) titleInput.focus();
  }

  newNoteBtn.addEventListener("click", () => toggleForm(true));
  cancelBtn.addEventListener("click", () => {
    newNoteForm.reset();
    toggleForm(false);
  });

  newNoteForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const metricValueRaw = metricValueInput.value.trim();
    const payload = {
      title: titleInput.value.trim(),
      category: categorySelect.value,
      content: contentInput.value.trim(),
      metric_label: metricLabelInput.value.trim() || null,
      metric_value: metricValueRaw ? Number(metricValueRaw) : null,
    };
    if (!payload.title || !payload.content) return;

    try {
      await apiPost("/lab-notes", payload);
      newNoteForm.reset();
      toggleForm(false);
      activeCategory = "all";
      filtersEl.querySelectorAll("button[data-category]").forEach((b) => {
        const active = b.dataset.category === "all";
        b.classList.toggle("bg-surface-tint", active);
        b.classList.toggle("text-on-primary", active);
        b.classList.toggle("sandstone-bg", !active);
        b.classList.toggle("text-on-surface-variant", !active);
      });
      load();
    } catch (err) {
      console.error(err);
      alert("Could not save the note — is the API running?");
    }
  });

  load();
})();
