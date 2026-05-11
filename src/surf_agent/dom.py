"""DOM extraction: snapshot interactable elements and label them with numeric ids.

The agent operates on this labeled snapshot rather than raw HTML. Each
interactable element (link / button / input / select / textarea / role-based
clickable) gets a stable `target_id` for the current observation.

The same numbering is shared with the browser controller via the
`InteractableElement` list so that `click(target_id=5)` can be translated back
into a Playwright locator.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import Page

# JavaScript that walks the DOM and returns interactable elements with
# normalized metadata. Runs in the page context, so we don't ship every node
# back to Python.
_SNAPSHOT_JS = r"""
() => {
  const out = [];
  const seen = new WeakSet();

  function visible(el) {
    if (!el || !el.getBoundingClientRect) return false;
    const r = el.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) return false;
    const style = window.getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') return false;
    if (parseFloat(style.opacity || '1') < 0.05) return false;
    // Must be within viewport (loosely)
    if (r.bottom < -50 || r.top > window.innerHeight + 50) return false;
    return true;
  }

  function label(el) {
    const aria = el.getAttribute('aria-label');
    if (aria) return aria.trim();
    const placeholder = el.getAttribute('placeholder');
    if (placeholder) return placeholder.trim();
    const title = el.getAttribute('title');
    if (title) return title.trim();
    const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
    if (text) return text.slice(0, 120);
    const name = el.getAttribute('name');
    if (name) return name.trim();
    return '';
  }

  function tagOf(el) {
    const role = el.getAttribute('role');
    if (role) return role.toLowerCase();
    return el.tagName.toLowerCase();
  }

  const candidates = document.querySelectorAll(
    'a, button, input, select, textarea, ' +
    '[role="button"], [role="link"], [role="textbox"], [role="checkbox"], ' +
    '[role="menuitem"], [role="tab"], [role="combobox"], ' +
    '[onclick], [contenteditable="true"]'
  );

  candidates.forEach((el) => {
    if (seen.has(el)) return;
    if (!visible(el)) return;
    if (el.disabled) return;
    seen.add(el);
    out.push({
      tag: tagOf(el),
      type: (el.getAttribute('type') || '').toLowerCase(),
      label: label(el),
      value: el.value || '',
      href: el.getAttribute('href') || '',
    });
  });

  return {
    url: window.location.href,
    title: document.title,
    elements: out,
  };
}
"""


# Same selector list as `_SNAPSHOT_JS`, so the n-th snapshot element maps to
# the n-th element from `page.locator(...).nth(i)`.
_SELECTOR = (
    "a, button, input, select, textarea, "
    '[role="button"], [role="link"], [role="textbox"], [role="checkbox"], '
    '[role="menuitem"], [role="tab"], [role="combobox"], '
    "[onclick], [contenteditable=\"true\"]"
)


@dataclass
class InteractableElement:
    target_id: int
    tag: str
    type: str
    label: str
    value: str
    href: str


@dataclass
class PageSnapshot:
    url: str
    title: str
    elements: list[InteractableElement]

    def to_prompt(self, max_elements: int = 80) -> str:
        """Render a compact, token-frugal view for the LLM."""
        lines = [f"URL: {self.url}", f"TITLE: {self.title}", "", "INTERACTABLE ELEMENTS:"]
        shown = self.elements[:max_elements]
        for el in shown:
            descriptor = el.tag
            if el.type:
                descriptor += f":{el.type}"
            label = el.label or "<no label>"
            extra = ""
            if el.value:
                extra += f" value={el.value!r}"
            if el.href:
                extra += f" href={el.href[:60]!r}"
            lines.append(f"  [{el.target_id}] <{descriptor}> {label}{extra}")
        if len(self.elements) > max_elements:
            lines.append(
                f"  ... ({len(self.elements) - max_elements} more elements truncated)"
            )
        return "\n".join(lines)


async def snapshot_page(page: Page) -> PageSnapshot:
    raw = await page.evaluate(_SNAPSHOT_JS)
    elements = [
        InteractableElement(
            target_id=i,
            tag=item.get("tag", ""),
            type=item.get("type", ""),
            label=item.get("label", ""),
            value=item.get("value", ""),
            href=item.get("href", ""),
        )
        for i, item in enumerate(raw.get("elements", []))
    ]
    return PageSnapshot(url=raw.get("url", ""), title=raw.get("title", ""), elements=elements)


def locator_selector() -> str:
    """The CSS selector matching the same set used in the snapshot.

    Combine with `.nth(target_id)` to recover the element corresponding to a
    given numeric id from the most-recent snapshot.
    """
    return _SELECTOR
