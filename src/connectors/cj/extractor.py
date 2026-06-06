from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
from typing import List

def get_text_or_none(parent, **find_kwargs):
    tag = parent.find(**find_kwargs)
    if not tag:
        return None
    text = tag.get_text(" ", strip=True)
    return text if text else None

def get_compact_text(parent, selector):
    tag = parent.select_one(selector)
    if not tag:
        return None
    text = tag.get_text(" ", strip=True)
    return text if text else None

def import_html(path):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    return html


def list_raw_html_files(raw_folder_path: str) -> List[str]:
    if not os.path.isdir(raw_folder_path):
        return []
    files = []
    for entry in sorted(os.listdir(raw_folder_path)):
        candidate = os.path.join(raw_folder_path, entry)
        if os.path.isfile(candidate):
            files.append(candidate)
    return files

def extract_raw_data_from_html(html, path, now):
    soup = BeautifulSoup(html, "html.parser")
    extracted_data = []

    rows = soup.find_all(class_="adv-row-wrapper")
    for row in rows:
        platform_id = "cj"
        adv_id = row.find(class_="adv-id").text[:-3]


        adv_name = row.find(class_="adv-name")
        adv_url_tag = row.find(class_="link-to-url content ui-link")
        adv_url = adv_url_tag.get("href") if adv_url_tag else None

        category = row.find(class_="category-name").text
        adv_id_tag = adv_name.find(class_="adv-id") if adv_name else None

        three_month_epc = row.find(id="threeMonthEpc").text
        seven_day_epc = row.find(id="sevenDayEpc").text
        sale_commission_raw = row.find(class_="commission-value sale-terms").text
        lead_commission_raw = row.find(class_="commission-value lead-terms").text

        application_approval_signal_raw_tag = row.find(class_="approval-odds-text")
        application_approval_signal_raw = application_approval_signal_raw_tag.text if application_approval_signal_raw_tag else None

        relationship_raw = "not applied"

        adv_description = get_text_or_none(row, id="advertiser-description")
        adv_servicable_area = row.find(class_="serviceable-areas-content serv-area-all")
        program_terms_text = get_compact_text(row, ".advertiser-program-terms")

        relationship_history_text = get_compact_text(row, ".advertiser-relationship-history")
        linked_accounts_text = get_compact_text(row, ".advertiser-linked-accounts")
        detail_tabs_loaded = bool(row.select("ul.more-information-relationship-history-switch li[data-nav-id]"))

        refferal_period_tag = row.find(class_="action-item-grid-contents action-referral-period content")
        if refferal_period_tag != None:
            try:
                refferal_period = int(refferal_period_tag.text.split()[0])
                print(refferal_period)
            except ValueError:
                refferal_period = "Unknown"
        else:
            refferal_period = "Unknown"
        
        source_platform = "cj"
        source_file = path
        raw_fragment = str(row)
        earnings_raw = None
        
        for i in range(0,5):
            if row.find(class_=f"fl network-earnings-common network-earnings-bar_{i}") != None:
                earnings_raw = i
                break

        if adv_servicable_area:
            adv_servicable_area = adv_servicable_area.text.strip()

        if adv_id_tag:
            adv_id_tag.extract() 
        
        
        if three_month_epc[-3:] != "USD":
            continue

        name = adv_name.get_text(strip=True) if adv_name else None
        data = {
            "platform_id": platform_id if platform_id else "Unknown",
            "id": adv_id if adv_id else "Unknown",

            "name": name if name else "Unknown",
            "offer_url": adv_url if adv_url else "Unknown",
            "category": category if category else "Unknown",
            "description_raw": adv_description if adv_description else "Unknown",

            "earnings_raw": earnings_raw if earnings_raw else "Unknown",
            "three_month_epc": three_month_epc if three_month_epc else "Unknown",
            "seven_day_epc": seven_day_epc if seven_day_epc else "Unknown",
            "sale_commission_raw": sale_commission_raw if sale_commission_raw else "Unknown",
            "lead_commission_raw": lead_commission_raw if lead_commission_raw else "Unknown",

            "application_approval_signal_raw": application_approval_signal_raw if application_approval_signal_raw else "Unknown",
            "relationship_raw": relationship_raw if relationship_raw else "Unknown",
            "refferal_period": refferal_period if refferal_period else "Unknown",

            "servicable_area_raw": adv_servicable_area if adv_servicable_area else "Unknown",
            "program_terms_raw": program_terms_text if program_terms_text else "Unknown",

            "relationship_history_raw": relationship_history_text if relationship_history_text else "Unknown",
            "linked_accounts_raw": linked_accounts_text if linked_accounts_text else "Unknown",
            "detail_tabs_loaded": detail_tabs_loaded,

            "source_platform": source_platform if source_platform else "Unknown",
            "source_file": source_file if source_file else "Unknown",
            "raw_fragment": raw_fragment if raw_fragment else "Unknown",
            "raw_source_file": path,

            "extracted_at": now
        }
        #TODO: ADD OTHER UN ADDED ROWS LIKE COOKIE WINDOW
        extracted_data.append(data)
    return extracted_data

def save_json(extracted_data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)


def extract_from_raw_folder(raw_folder_path, extracted_at):
    extracted_data = []
    html_files = list_raw_html_files(raw_folder_path)
    for html_file in html_files:
        html = import_html(html_file)
        extracted_data.extend(extract_raw_data_from_html(html, html_file, extracted_at))
    return extracted_data


if __name__ == "__main__":
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")
    raw_folder_path = f"data/raw/cj/advertisers/{today}"

    json_path = f"data/normalized/cj/advertisers/{today}/{now}.json"

    date = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    extracted_data = extract_from_raw_folder(raw_folder_path, date)
    save_json(extracted_data, json_path)
