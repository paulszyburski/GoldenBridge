from connector import open_main_page_cj
from playwright.sync_api import sync_playwright
import os
from datetime import datetime

def count_cells(results_container):
    return results_container.locator(":scope > div").count()


def scroll_until_fully_loaded(page, results_container, max_rounds=80, pause_ms=1200, stable_rounds_needed=10, N_rows=100):
    stable_rounds = 0
    previous = count_cells(results_container)

    for _ in range(max_rounds):
        results_container.hover()
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(pause_ms)

        current = count_cells(results_container)
        if current > previous:
            previous = current
            stable_rounds = 0
        else:
            stable_rounds += 1

        if stable_rounds >= stable_rounds_needed or count_cells(results_container) > N_rows:
            break


def expand_loaded_rows(page, results_container, pause_ms=300):
    wrappers = results_container.locator(":scope > .adv-row-wrapper")
    wrappers_count = wrappers.count()

    for i in range(wrappers_count):
        wrapper = wrappers.nth(i)
        row = wrapper.locator(".adv-row .main-row-wrapper").first
        detail_row = wrapper.locator(".adv-detail-row").first

        if row.count() == 0:
            continue

        already_expanded = False
        if detail_row.count() > 0:
            detail_text = detail_row.inner_text(timeout=1000).strip().lower()
            already_expanded = bool(detail_text) and "loading" not in detail_text

        if already_expanded:
            continue

        row.click(force=True, timeout=5000)
        page.wait_for_timeout(pause_ms)

    page.wait_for_timeout(1500)

def scrape_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        open_main_page_cj(page)

        page.wait_for_load_state("domcontentloaded")
        results_container = page.locator("#advRowContainer")
        results_container.wait_for(state="visible", timeout=60000)
        page.wait_for_timeout(20000)
        scroll_until_fully_loaded(page, results_container)
        expand_loaded_rows(page, results_container)

        html = page.content()

        browser.close()
    return html

def save_html(html, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    today = datetime.now().strftime("%d-%m-%Y")
    html = scrape_html()
    path = f"data/raw/cj/advertisers/{today}/html"
    
    save_html(html, path)
