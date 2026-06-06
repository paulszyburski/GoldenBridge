try:
    from .connector import open_main_page_cj
except ImportError:
    if __package__:
        raise
    from connector import open_main_page_cj
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Error as PlaywrightError
import os
from datetime import datetime

def count_cells(results_container):
    return results_container.locator(":scope > div").count()


def scroll_until_fully_loaded(page, results_container, pause_ms=1200, stable_rounds_needed=10, N_rows=100):
    stable_rounds = 0
    previous = count_cells(results_container)

    while True:
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
        if i % 100 == 0: print(i)
        wrapper = wrappers.nth(i)
        row = wrapper.locator(".adv-row .main-row-wrapper").first
        detail_row = wrapper.locator(".adv-detail-row").first

        if row.count() == 0:
            continue

        already_expanded = False
        if detail_row.count() > 0:
            try:
                detail_text = (detail_row.text_content(timeout=700) or "").strip().lower()
                already_expanded = bool(detail_text) and "loading" not in detail_text
            except (PlaywrightTimeoutError, PlaywrightError):
                # Some rows are briefly detached while the virtualized list re-renders.
                # Treat them as not expanded and continue.
                already_expanded = False

        if already_expanded:
            continue

        try:
            row.click(force=True, timeout=5000)
        except (PlaywrightTimeoutError, PlaywrightError):
            continue
        page.wait_for_timeout(pause_ms)

    page.wait_for_timeout(1500)

def open_all_detail_tabs(page, results_container, pause_ms=250):
    wrappers = results_container.locator(":scope > .adv-row-wrapper")
    wrappers_count = wrappers.count()

    for i in range(wrappers_count):
        wrapper = wrappers.nth(i)
        detail_row = wrapper.locator(".adv-detail-row").first
        if detail_row.count() == 0:
            continue

        nav_items = detail_row.locator("ul.more-information-relationship-history-switch li[data-nav-id]")
        nav_count = nav_items.count()
        if nav_count == 0:
            continue

        for j in range(nav_count):
            tab = nav_items.nth(j)
            try:
                tab.click(force=True, timeout=4000)
            except (PlaywrightTimeoutError, PlaywrightError):
                continue
            page.wait_for_timeout(pause_ms)

    page.wait_for_timeout(1200)

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
        open_all_detail_tabs(page, results_container)

        print("scraping web")
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
