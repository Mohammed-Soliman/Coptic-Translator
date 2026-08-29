(function () {
  "use strict";
  const { apiGet, escapeHtml, titleCase } = window.CopticLab;

  const gridEl = document.getElementById("manuscripts-grid");
  const filtersEl = document.getElementById("manuscripts-filters");
  const searchInput = document.getElementById("manuscripts-search-input");

  const DIALECT_COLORS = {
    sahidic: "#B5502E",
    bohairic: "#1F5C7A",
    akhmimic: "#D69F4C",
    unknown: "#8A726B",
  };

  let allManuscripts = [];
  let activeDialect = "all";

  function prettySourceName(source) {
    // Source strings are sometimes filenames or long provenance notes -
    // keep the card readable without inventing details we don't have.
    const trimmed = source.length > 60 ? source.slice(0, 57) + "…" : source;
    return trimmed
      .replace(/[_-]+/g, " ")
      .replace(/\.(json|conllu)$/i, "");
  }

  function renderCard(m) {
    const color = DIALECT_COLORS[m.dialect] || DIALECT_COLORS.unknown;
    return `
      <article class="sandstone-card woven-border flex flex-col h-full hover:shadow-lg transition-shadow cursor-pointer group">
        <div class="h-32 relative border-b border-primary recessed m-1 overflow-hidden manuscript-swatch flex items-center justify-center" style="background-color: ${color}22;">
          <span class="text-script-display font-script-display coptic-glyphs text-3xl" style="color: ${color};">${escapeHtml(m.sample_coptic.slice(0, 12))}</span>
          <div class="absolute top-2 right-2 px-2 py-1 bg-surface text-on-surface text-[10px] font-label-caps border border-outline uppercase tracking-wider">${m.annotated ? "Annotated" : "Raw"}</div>
        </div>
        <div class="p-6 flex-1 flex flex-col">
          <h3 class="text-headline-md font-headline-md text-primary mb-2 leading-tight">${escapeHtml(prettySourceName(m.source))}</h3>
          <p class="text-label-caps font-label-caps text-on-surface-variant mb-2 tracking-widest">${m.sentence_count} sentence${m.sentence_count === 1 ? "" : "s"}</p>
          <p class="text-body-md font-body-md text-on-surface-variant text-sm mb-4 italic">"${escapeHtml(m.sample_english)}"</p>
          <div class="mt-auto pt-4 border-t border-outline-variant flex justify-between items-center">
            <span class="px-2 py-1 text-[#4A3B32] text-[10px] font-label-caps" style="background-color: ${color}55;">${escapeHtml(titleCase(m.dialect))}</span>
            <span class="material-symbols-outlined text-primary group-hover:translate-x-1 transition-transform">arrow_forward</span>
          </div>
        </div>
      </article>`;
  }

  function render() {
    const query = searchInput.value.trim().toLowerCase();
    const filtered = allManuscripts.filter((m) => {
      if (activeDialect !== "all" && m.dialect !== activeDialect) return false;
      if (query) {
        const haystack = `${m.source} ${m.sample_english} ${m.sample_coptic}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      gridEl.innerHTML =
        '<p class="text-body-md font-body-md text-on-surface-variant col-span-4">No ingested manuscripts match those filters yet.</p>';
      return;
    }

    gridEl.innerHTML = filtered.map(renderCard).join("");
  }

  filtersEl.querySelectorAll("button[data-dialect]").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeDialect = btn.dataset.dialect;
      filtersEl.querySelectorAll("button[data-dialect]").forEach((b) => {
        const active = b === btn;
        b.classList.toggle("bg-surface-tint", active);
        b.classList.toggle("text-on-primary", active);
        b.classList.toggle("bg-surface-tint/10", !active);
        b.classList.toggle("text-on-surface", !active);
      });
      render();
    });
  });

  searchInput.addEventListener("input", render);

  async function load() {
    try {
      allManuscripts = await apiGet("/corpus/list");
      render();
    } catch (err) {
      console.error(err);
      gridEl.innerHTML =
        '<p class="text-body-md font-body-md text-error col-span-4">Corpus service unavailable — is the API running?</p>';
    }
  }

  load();
})();
