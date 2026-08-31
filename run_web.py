"""Deployment entry point for the Social Content Studio browser MVP."""

from __future__ import annotations

import os

from services import stock_avatar_ui_server
from services.stock_avatar_ui_server import serve_stock_avatar


def _port() -> int:
    raw = os.getenv("PORT", "8787")
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return port


def _patch_stock_search_submit() -> None:
    """Prevent native form navigation and preserve the full stock result renderer."""
    button_marker = 'id="stock-submit" class="secondary" type="submit"'
    button_replacement = 'id="stock-submit" class="secondary" type="button"'
    if button_marker in stock_avatar_ui_server.HTML:
        stock_avatar_ui_server.HTML = stock_avatar_ui_server.HTML.replace(
            button_marker,
            button_replacement,
            1,
        )

    bridge = """<script>
(() => {
  const button = document.getElementById('stock-submit');
  const input = document.getElementById('stock-query');
  const status = document.getElementById('stock-status');
  const results = document.getElementById('stock-results');
  if (!button || !input || !status || !results) return;
  const escapeHtml = value => String(value).replace(/[&<>\\\"]/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;','\\\\':'&#39;'
  }[c]));
  const renderResults = rows => {
    results.textContent = '';
    if (!rows.length) {
      results.innerHTML = '<div class="stock-empty">No portrait clips found for that search.</div>';
      return;
    }
    for (const row of rows) {
      const item = document.createElement('div');
      item.className = 'stock-item';
      const thumb = document.createElement('img');
      thumb.className = 'stock-thumb';
      thumb.alt = 'Stock preview thumbnail';
      if (row.thumbnail_url) thumb.src = row.thumbnail_url;
      item.appendChild(thumb);
      const copy = document.createElement('div');
      copy.className = 'stock-copy';
      const title = document.createElement('div');
      title.className = 'stock-title';
      title.textContent = String(row.title || row.id || 'Stock video');
      copy.appendChild(title);
      const meta = document.createElement('div');
      meta.className = 'stock-meta';
      const parts = [];
      if (row.duration_seconds) parts.push(row.duration_seconds + 's');
      if (row.orientation) parts.push(row.orientation);
      if (row.width && row.height) parts.push(row.width + '×' + row.height);
      meta.textContent = parts.join(' · ') || 'Metadata unavailable';
      copy.appendChild(meta);
      const links = document.createElement('div');
      links.className = 'stock-links';
      if (row.preview_url) {
        const preview = document.createElement('a');
        preview.href = row.preview_url;
        preview.target = '_blank';
        preview.rel = 'noopener noreferrer';
        preview.textContent = 'Preview clip';
        links.appendChild(preview);
      }
      if (row.source_url) {
        const source = document.createElement('a');
        source.href = row.source_url;
        source.target = '_blank';
        source.rel = 'noopener noreferrer';
        source.textContent = 'Open source';
        links.appendChild(source);
      }
      copy.appendChild(links);
      item.appendChild(copy);
      results.appendChild(item);
    }
  };
  const runSearch = async () => {
    const query = input.value.trim();
    if (!query) {
      status.className = 'status error';
      status.textContent = 'Enter a search query.';
      return;
    }
    button.disabled = true;
    status.className = 'status';
    status.textContent = 'Searching free stock clips…';
    try {
      const response = await fetch('/api/stock-videos?query=' + encodeURIComponent(query));
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to search stock videos');
      const rows = Array.isArray(data.results) ? data.results : [];
      renderResults(rows);
      status.className = 'status ok';
      status.textContent = rows.length ? 'Found free stock clips from Pexels.' : 'No free stock clips found.';
    } catch (error) {
      status.className = 'status error';
      status.textContent = error instanceof Error ? error.message : 'Stock search is unavailable right now.';
      results.innerHTML = '<div class="stock-empty">Stock search is unavailable right now.</div>';
    } finally {
      button.disabled = false;
    }
  };
  button.addEventListener('click', runSearch);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      runSearch();
    }
  });
})();
</script>"""
    stock_avatar_ui_server.HTML = stock_avatar_ui_server.HTML.replace(
        "</body>",
        bridge + "</body>",
        1,
    )


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    _patch_stock_search_submit()
    serve_stock_avatar(host=host, port=_port())


if __name__ == "__main__":
    main()
