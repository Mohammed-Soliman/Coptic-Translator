(function () {
  "use strict";
  const { apiGet, debounce, escapeHtml, titleCase } = window.CopticLab;

  const searchInput = document.getElementById("lexicon-search-input");
  const dialectSelect = document.getElementById("lexicon-dialect-select");
  const posSelect = document.getElementById("lexicon-pos-select");
  const resultsEl = document.getElementById("lexicon-results");
  const detailEl = document.getElementById("lexicon-detail-panel");

  let currentResults = [];
  let selectedIndex = -1;

  function dialectBadge(dialects) {
    if (!dialects || dialects.length === 0) return "Unknown";
    return dialects.map(titleCase).join(" / ");
  }

  function renderResults(entries) {
    currentResults = entries;
    if (entries.length === 0) {
      resultsEl.innerHTML =
        '<p class="text-body-md font-body-md text-on-surface-variant col-span-2">No entries match those filters yet — the starter lexicon is small.</p>';
      return;
    }

    resultsEl.innerHTML = entries
      .map((entry, index) => {
        const active = index === selectedIndex;
        return `
        <div class="bg-[#F5EEDF] border ${active ? "border-primary border-opacity-80" : "border-outline border-opacity-50"} p-6 flex flex-col gap-4 relative cursor-pointer hover:bg-surface-variant transition-colors group shadow-[inset_0_0_0_1px_theme(colors.outline-variant)]" data-index="${index}">
          ${active ? '<div class="absolute -left-px top-0 bottom-0 w-1 bg-primary"></div>' : ""}
          <div class="flex justify-between items-start border-b border-outline-variant pb-4">
            <div>
              <h3 class="text-script-display font-script-display text-primary mb-1 coptic-glyphs">${escapeHtml(entry.coptic)}</h3>
              <span class="bg-[#d4b35e] text-on-surface text-[10px] font-label-caps px-2 py-1 uppercase tracking-widest">${escapeHtml(dialectBadge(entry.dialect))}</span>
            </div>
            <span class="text-label-caps font-label-caps text-on-surface-variant italic">${escapeHtml(titleCase(entry.part_of_speech || "—"))}${entry.gender ? ", " + escapeHtml(entry.gender.slice(0, 4)) + "." : ""}</span>
          </div>
          <div>
            <p class="text-body-md font-body-md text-on-surface mb-2">${escapeHtml((entry.english || []).join("; ") || "No gloss yet.")}</p>
            <p class="text-label-caps font-label-caps text-tertiary-container group-hover:text-primary transition-colors">${active ? "Viewing entry" : "View full entry →"}</p>
          </div>
        </div>`;
      })
      .join("");

    resultsEl.querySelectorAll("[data-index]").forEach((card) => {
      card.addEventListener("click", () => {
        selectedIndex = Number(card.dataset.index);
        renderResults(currentResults);
        renderDetail(currentResults[selectedIndex]);
      });
    });
  }

  async function renderDetail(entry) {
    if (!entry) {
      detailEl.innerHTML =
        '<p class="text-body-md font-body-md text-on-surface-variant">Select an entry to see its full record.</p>';
      return;
    }

    const sourcesList = (entry.sources || [])
      .map((s) => `<li>${escapeHtml(s)}</li>`)
      .join("") || "<li>No source attribution recorded.</li>";

    detailEl.innerHTML = `
      <div class="border-b-2 border-outline-variant pb-6 mb-6">
        <div class="flex justify-between items-start mb-4">
          <h2 class="text-headline-lg font-headline-lg text-primary coptic-glyphs">${escapeHtml(entry.coptic)}</h2>
        </div>
        <p class="text-body-lg font-body-lg text-on-surface font-semibold mb-2">${escapeHtml(entry.lemma)}</p>
        <p class="text-body-md font-body-md text-on-surface-variant italic">${escapeHtml(titleCase(entry.part_of_speech || "Unclassified"))}${entry.gender ? ", " + escapeHtml(entry.gender) : ""}. Dialects: ${escapeHtml(dialectBadge(entry.dialect))}</p>
      </div>
      <div class="flex-grow flex flex-col gap-8">
        <section>
          <h4 class="text-label-caps font-label-caps text-outline uppercase tracking-widest mb-3 border-b border-outline-variant pb-1">Primary Gloss</h4>
          <p class="text-body-lg font-body-lg text-on-surface mb-6">${escapeHtml((entry.english || []).join("; ") || "No gloss yet.")}</p>
          <h4 class="text-label-caps font-label-caps text-outline uppercase tracking-widest mb-3 border-b border-outline-variant pb-1">Sources</h4>
          <ul class="text-body-md font-body-md text-on-surface list-disc list-inside">${sourcesList}</ul>
        </section>
        <section>
          <h4 class="text-label-caps font-label-caps text-outline uppercase tracking-widest mb-4 border-b border-outline-variant pb-1">Corpus Attestations</h4>
          <div class="flex flex-col gap-4" id="lexicon-attestations">
            <p class="text-body-md font-body-md text-on-surface-variant text-sm">Searching corpus…</p>
          </div>
        </section>
      </div>
    `;

    const attestationsEl = document.getElementById("lexicon-attestations");
    try {
      const query = (entry.english && entry.english[0]) || entry.lemma;
      const hits = await apiGet("/corpus/search", { q: query, top_k: 3 });
      if (hits.length === 0) {
        attestationsEl.innerHTML =
          '<p class="text-body-md font-body-md text-on-surface-variant text-sm">No corpus attestations found yet — the ingested corpus is still small.</p>';
      } else {
        attestationsEl.innerHTML = hits
          .map(
            (hit) => `
          <div class="bg-[#F5EEDF] p-4 border border-outline-variant">
            <p class="text-script-display font-script-display text-primary mb-2 text-sm leading-relaxed coptic-glyphs">${escapeHtml(hit.coptic)}</p>
            <p class="text-body-md font-body-md text-on-surface text-sm mb-2 italic">"${escapeHtml(hit.english)}"</p>
            <p class="text-label-caps font-label-caps text-tertiary-container text-right">${escapeHtml(hit.source)}</p>
          </div>`
          )
          .join("");
      }
    } catch (err) {
      console.error(err);
      attestationsEl.innerHTML =
        '<p class="text-body-md font-body-md text-error text-sm">Corpus search unavailable — is the API running?</p>';
    }
  }

  async function runSearch() {
    selectedIndex = -1;
    resultsEl.innerHTML =
      '<p class="text-body-md font-body-md text-on-surface-variant col-span-2">Searching…</p>';
    try {
      const entries = await apiGet("/lexicon/search", {
        q: searchInput.value.trim(),
        dialect: dialectSelect.value,
        pos: posSelect.value,
        limit: 30,
      });
      renderResults(entries);
      renderDetail(null);
    } catch (err) {
      console.error(err);
      resultsEl.innerHTML =
        '<p class="text-body-md font-body-md text-error col-span-2">Lexicon service unavailable — is the API running?</p>';
    }
  }

  const debouncedSearch = debounce(runSearch, 400);
  searchInput.addEventListener("input", debouncedSearch);
  dialectSelect.addEventListener("change", runSearch);
  posSelect.addEventListener("change", runSearch);

  runSearch();
})();
