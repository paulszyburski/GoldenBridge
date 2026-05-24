from dotenv import load_dotenv
import os


"""THIS FILE WILL ONLY GET TO THE MAIN CJ PAGE. IT WILL BE USED IN OTHER FILES AS A SHORTCUT"""


load_dotenv()
email = os.getenv("CJ_EMAIL")
password = os.getenv("CJ_PASSWORD")

def open_main_page_cj(page):
    page.goto("https://signin.cj.com/u/login/")

    page.get_by_label("Email").fill(email or "")
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("textbox", name="Password").fill(password or "")
    page.get_by_role("button", name="Continue").click()

    page.wait_for_timeout(1000)

    partners = page.get_by_role("button", name="Partners")
    partners.hover()
    find_advertisers = page.get_by_role("link", name="Find Advertisers")
    find_advertisers.wait_for(state="visible")
    find_advertisers.click()
