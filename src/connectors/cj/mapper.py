import json
import re
import os
from datetime import datetime

def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def export_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_epc(epc_raw):
    if epc_raw is None:
        return None, None
    epc_raw = epc_raw.strip()
    if not epc_raw:
        return None, None

    # Accept both "2.42 USD" and "(2.42 USD)" raw formats.
    if epc_raw.startswith("(") and epc_raw.endswith(")"):
        epc_raw = epc_raw[1:-1].strip()

    parts = epc_raw.split()
    if len(parts) < 2:
        return None, None
    return parts[0], parts[1]

def convert_target_markets(target_markets):
    modified_target_markets = ''
    if not target_markets:
        return []
    normalized = {str(x).strip().upper() for x in target_markets}
    if "U.S." in normalized or "UNITED STATES" in normalized or "USA" in normalized:
        modified_target_markets = "EN-US"
    return modified_target_markets

def extract_number(value):
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def remove_commas_keep_dots(value):
    if value is None:
        return value
    return value.replace(",", "")


def add_reason(reason_codes, condition, code):
    if condition:
        reason_codes.append(code)


def create_offer_candidate(row, file):
    platform_id = row["platform_id"]
    partner_id = row["id"]
    offer_id = row["id"]

    offer_name = row["name"]
    offer_url = row["offer_url"]
    #program_url
    category = row["category"]
    description = row["description_raw"]

    payout_type = None
    payout_amount_original = None
    payout_currency = None
    payout_amount_usd = None
    payout_percent = None

    #estimated_order_value_usd
    #estimated_cpa_usd
    #revshare_estimation_source
    #revshare_estimation_confidence

    lead_commission_raw = row["lead_commission_raw"]
    sale_commission_raw = row["sale_commission_raw"]
    

    three_month_epc_raw = row["three_month_epc"]
    seven_day_epc_raw = row["seven_day_epc"]

    three_month_epc_original = None
    three_month_epc_currency = None
    seven_day_epc_original = None
    seven_day_epc_currency = None
    partner_terms_available = row["program_terms_raw"] != "Unknown"

    cookie_window_days = row["refferal_period"]
    cookie_window_source = "More Info Tab"

    target_markets_raw = row["servicable_area_raw"].split(", ")
    target_markets_filtered = []

    raw_source_file = row["raw_source_file"]

    if target_markets_raw != None:
        target_markets_raw_splitted = row["servicable_area_raw"].split(", ")
        for target_market in ["U.S.", "UNITED STATES"]:
            if target_market in target_markets_raw_splitted:
                target_markets_filtered.append(target_market)

    target_markets_processed = convert_target_markets(target_markets_raw)

    affiliate_access_status = "not_applied"
    approval_required_before_scaling = True
    affiliate_approval_difficulty = "filled in code below"

    normalized_at = row["extracted_at"]

    source_platform = "cj"
    source_file = file
    source_row_id = row["id"]
    reason_codes = []


    if sale_commission_raw != "Unknown" and lead_commission_raw == "Unknown":
        sale_commission_raw_splitted = sale_commission_raw.split()
        if sale_commission_raw[-1] == "%":#check if its a percent payout
            payout_type = "RevShare"
            parsed_percent = extract_number(sale_commission_raw)
            payout_percent = parsed_percent if parsed_percent is not None else None
        else:
            payout_type = "CPA"
            parsed_amount = extract_number(sale_commission_raw)
            payout_amount_original = parsed_amount if parsed_amount is not None else None
            payout_currency = sale_commission_raw_splitted[-1] if len(sale_commission_raw_splitted) > 1 else None

    elif sale_commission_raw == "Unknown" and lead_commission_raw != "Unknown":
        lead_commission_raw_splitted = lead_commission_raw.split()
        if lead_commission_raw[-1] == "%":#check if its a percent payout
            payout_type = "RevShare"
            parsed_percent = extract_number(lead_commission_raw)
            payout_percent = parsed_percent if parsed_percent is not None else None
        else:
            payout_type = "CPL"
            parsed_amount = extract_number(lead_commission_raw)
            payout_amount_original = parsed_amount if parsed_amount is not None else None
            payout_currency = lead_commission_raw_splitted[-1] if len(lead_commission_raw_splitted) > 1 else None

    elif sale_commission_raw != "Unknown" and lead_commission_raw != "Unknown":
        payout_type = "Hybrid"

    if row["application_approval_signal_raw"].split()[0] == "Manual":
        affiliate_approval_difficulty = "medium"
    elif row["application_approval_signal_raw"].split()[0] == "Lower":
        affiliate_approval_difficulty = "premium"
    elif row["application_approval_signal_raw"].split()[0] == "Higher":
        affiliate_approval_difficulty = "easy"
    else:
        affiliate_approval_difficulty = "Unknown"

    three_month_epc_original, three_month_epc_currency = parse_epc(three_month_epc_raw)
    seven_day_epc_original, seven_day_epc_currency = parse_epc(seven_day_epc_raw)

    if three_month_epc_original != None: three_month_epc_original = float(remove_commas_keep_dots(three_month_epc_original))
    if seven_day_epc_original != None: seven_day_epc_original = float(remove_commas_keep_dots(seven_day_epc_original))

    seven_day_epc_usd = seven_day_epc_original if seven_day_epc_currency == "USD" else None
    three_month_epc_usd = three_month_epc_original if three_month_epc_currency == "USD" else None
    payout_amount_usd = payout_amount_original if payout_currency == "USD" else None

    add_reason(reason_codes, description == None, "DESCRIPTION_MISSING_IN_SOURCE")
    add_reason(reason_codes, sale_commission_raw == None and lead_commission_raw == None, "COMMISSIONS_MISSING_IN_SOURCE")
    add_reason(reason_codes, payout_type == None, "PAYOUT_TYPE_NOT_DETERMINED")
    add_reason(reason_codes, payout_percent in (None, None) and payout_type in ("RevShare", "Hybrid"), "PAYOUT_PERCENT_MISSING_OR_UNPARSEABLE")
    add_reason(reason_codes, payout_amount_original == None and payout_type in ("CPA", "CPL", "Hybrid"), "PAYOUT_AMOUNT_MISSING_OR_UNPARSEABLE")
    add_reason(reason_codes, payout_currency == None and payout_type in ("CPA", "CPL", "Hybrid"), "PAYOUT_CURRENCY_MISSING_OR_UNPARSEABLE")
    add_reason(reason_codes, three_month_epc_original == None, "THREE_MONTH_EPC_MISSING_OR_UNPARSEABLE")
    add_reason(reason_codes, three_month_epc_currency == None, "THREE_MONTH_EPC_CURRENCY_MISSING")
    add_reason(reason_codes, seven_day_epc_original == None, "SEVEN_DAY_EPC_MISSING_OR_UNPARSEABLE")
    add_reason(reason_codes, seven_day_epc_currency == None, "SEVEN_DAY_EPC_CURRENCY_MISSING")
    add_reason(reason_codes, cookie_window_days is None, "COOKIE_WINDOW_UNKNOWN")
    add_reason(reason_codes, not target_markets_processed or target_markets_processed == [], "TARGET_MARKETS_MISSING_IN_SOURCE")
    add_reason(reason_codes, affiliate_approval_difficulty == "Unknown", "APPROVAL_DIFFICULTY_NOT_DEFINED")
    add_reason(reason_codes, not partner_terms_available, "TERMS_UNKNOWN")

    data = {
        "platform_id": platform_id,
        "partner_id": partner_id,
        "offer_id": offer_id,

        "offer_name": offer_name,
        "offer_url": offer_url,
        #program_url:
        "category": category,
        "description": description,

        "payout_type": payout_type,
        "payout_amount_original": payout_amount_original,
        "payout_currency": payout_currency,
        "payout_amount_usd":payout_amount_usd,
        "payout_percent": payout_percent,

        #ESTIMATION
        #estimated_order_value_usd
        #estimated_cpa_usd
        #revshare_estimation_source
        #revshare_estimation_confidence

        "three_month_epc_original": three_month_epc_original,
        "three_month_epc_currency": three_month_epc_currency,
        "three_month_epc_usd": three_month_epc_usd,

        "seven_day_epc_original": seven_day_epc_original,
        "seven_day_epc_currency": seven_day_epc_currency,
        "seven_day_epc_usd": seven_day_epc_usd,

        "cookie_window_days": cookie_window_days,
        "cookie_window_source": cookie_window_source,

        "target_markets_raw": target_markets_raw,
        "target_markets_filtered": target_markets_filtered,
        "target_markets_processed": target_markets_processed,

        "affiliate_access_status": affiliate_access_status,
        "approval_required_before_scaling": approval_required_before_scaling,
        "affiliate_approval_difficulty": affiliate_approval_difficulty,

        "partner_terms_available": partner_terms_available,
        "partner_terms": row["program_terms_raw"],

        #allowed_promotion_methods
        #restricted_promotion_methods
        #promotion_policy_source

        #backup_offer_available

        "source_platform": source_platform,
        "source_file": source_file,
        "source_row_id": source_row_id,
        "raw_source_file": raw_source_file,

        "normalized_at": normalized_at,
        "mapped_at": datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),

        "sale_commission_raw": sale_commission_raw,
        "lead_commission_raw": lead_commission_raw,
        "three_month_epc_raw": three_month_epc_raw,
        "seven_day_epc_raw": seven_day_epc_raw,

        "reason_codes": reason_codes,
    }
    #TODO: ADD OTHER UN ADDED ROWS LIKE COOKIE WINDOW
    return data

def map_json(json_data, file):
    mapped_json = []
    for row in json_data:
        mapped_row = create_offer_candidate(row, file)
        mapped_json.append(mapped_row)
    return mapped_json

if __name__ == "__main__":
    today = datetime.now().strftime("%d-%m-%Y")
    noww = datetime.now().strftime("%H-%M-%S")
    path = f"data/normalized/cj/advertisers/06-06-2026/20-52-10.json"
    jsonn = import_json(path)
    mapped_json = map_json(jsonn, path)
    output_path = f"data/processed/cj/advertisers/{today}/{noww}.json"
    export_json(mapped_json, output_path)
    print(f"Exported mapped json to: {output_path}. {len(mapped_json)} total rows")
