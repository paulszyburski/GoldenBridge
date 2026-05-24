from bs4 import BeautifulSoup
from datetime import datetime
import json
import os

def import_html(path):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    return html

def extract_raw_data_from_html(html, path):
    soup = BeautifulSoup(html, "html.parser")
    extracted_data = []

    rows = soup.find_all(class_="adv-row")
    for row in rows:
        platform_id = "cj"
        adv_name = row.find(class_="adv-name")
        adv_id = row.find(class_="adv-id").text[:-3]
        category = row.find(class_="category-name").text
        adv_id_tag = adv_name.find(class_="adv-id") if adv_name else None

        three_month_epc = row.find(id="threeMonthEpc").text
        seven_day_epc = row.find(id="sevenDayEpc").text
        sale_commission_raw = row.find(class_="commission-value sale-terms").text
        lead_commission_raw = row.find(class_="commission-value lead-terms").text

        application_approval_signal_raw = row.find(class_="approval-odds-text").text
        relationship_raw = "not applied"

        adv_servicable_area = row.find

        source_platform = "cj"
        source_file = path
        raw_fragment = str(row)
        earnings_raw = None
        
        for i in range(0,5):
            if row.find(class_=f"fl network-earnings-common network-earnings-bar_{i}") != None:
                earnings_raw = i
                break

        if adv_id_tag:
            adv_id_tag.extract() 
        
        
        if three_month_epc[-3:] != "USD":
            continue
        print(three_month_epc[-3:])

        name = adv_name.get_text(strip=True) if adv_name else None
        print(sale_commission_raw == "")
        data = {
            "platform_id": platform_id if sale_commission_raw else "Unknown",
            "name": name if name else "Unknown",
            "id": adv_id if adv_id else "Unknown",
            "category": category if category else "Unknown",
            "earnings_raw": earnings_raw if earnings_raw else "Unknown",
            "three_month_epc": three_month_epc if three_month_epc else "Unknown",
            "seven_day_epc": seven_day_epc if seven_day_epc else "Unknown",
            "sale_commission_raw": sale_commission_raw if sale_commission_raw else "Unknown",
            "lead_commission_raw": lead_commission_raw if lead_commission_raw else "Unknown",
            "application_approval_signal_raw": application_approval_signal_raw if sale_commission_raw else "Unknown",
            "relationship_raw": relationship_raw if sale_commission_raw else "Unknown",
            "source_platform": source_platform if sale_commission_raw else "Unknown",
            "source_file": source_file if source_file else "Unknown",
            "raw_fragment": raw_fragment if raw_fragment else "Unknown",
        }
        extracted_data.append(data)
    return extracted_data

def save_json(extracted_data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")
    path = f"data/raw/cj/advertisers/24-05-2026/html"

    json_path = f"data/normalized/cj/advertisers/{today}/{now}.json"

    html = import_html(path)
    extracted_data = extract_raw_data_from_html(html, path)
    save_json(extracted_data, json_path)
