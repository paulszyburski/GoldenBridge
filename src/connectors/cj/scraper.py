from playwright.sync_api import sync_playwright

"""THIS FILE WILL ONLY GET TO THE MAIN CJ PAGE. IT WILL BE USED IN OTHER FILES AS A SHORTCUT"""
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page()
    page.goto("https://signin.cj.com/u/login/")

    page.wait_for_timeout(2000)
    page.screenshot(path="demo.png", full_page=True)

    print(f"Current URL: {page.url[:50]}...")
    print("\n\n", page.content())

    browser.close()