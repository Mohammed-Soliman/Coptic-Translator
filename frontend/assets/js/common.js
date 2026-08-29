// Shared helpers for the Coptic Lab frontend. Served from the same
// FastAPI app as the API itself (see backend/api/main.py's StaticFiles
// mounts), so every call below is same-origin - no base URL, no CORS.
(function (global) {
  "use strict";

  async function apiGet(path, params) {
    const url = new URL(path, window.location.origin);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          url.searchParams.set(key, value);
        }
      });
    }
    const res = await fetch(url.toString());
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`GET ${path} failed (${res.status}): ${detail}`);
    }
    return res.json();
  }

  async function apiPost(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`POST ${path} failed (${res.status}): ${detail}`);
    }
    return res.json();
  }

  function debounce(fn, waitMs) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), waitMs);
    };
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatPct(value) {
    if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
    return `${Math.round(value * 100)}%`;
  }

  function titleCase(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  global.CopticLab = { apiGet, apiPost, debounce, escapeHtml, formatPct, titleCase };
})(window);
