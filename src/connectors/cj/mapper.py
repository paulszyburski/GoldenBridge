import json

def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    

def create_offer_candidate(row):
    sale_commission_raw = row["sale_commission_raw"]
    lead_commission_raw = row["lead_commission_raw"]
    three_month_epc = row["three_month_epc"]
    seven_day_epc = row["seven_day_epc"]

    payout_type = "NotProvided"
    payout_percent = "NotProvided"
    payout_amount_original = "NotProvided"
    payout_currency = "NotProvided"

    three_month_epc_original = "NotProvided"
    three_month_epc_currency = "NotProvided"
    seven_day_epc_original = "NotProvided"
    seven_day_epc_currency = "NotProvided"

    cookie_window_days = "Unknown"
    
    
    if sale_commission_raw != "Unknown" and lead_commission_raw == "Unknown":
        sale_commission_raw_splitted = sale_commission_raw.split()
        if sale_commission_raw[-1] == "%":#check if its a percent payout
            payout_type = "RevShare"
            payout_percent = int(sale_commission_raw_splitted[-1][:-1])
        else:
            payout_type = "CPA"
            payout_amount_original = float(sale_commission_raw_splitted[1])
            payout_currency = sale_commission_raw_splitted[2]

    elif sale_commission_raw == "Unknown" and lead_commission_raw != "Unknown":
        lead_commission_raw_splitted = lead_commission_raw.split()
        if lead_commission_raw[-1] == "%":#check if its a percent payout
            payout_type = "RevShare"
            payout_percent = int(lead_commission_raw_splitted[-1][:-1])
        else:
            payout_type = "CPL"
            payout_amount_original = float(lead_commission_raw_splitted[1])
            payout_currency = lead_commission_raw_splitted[2]
    
    elif sale_commission_raw != "Unknown" and lead_commission_raw != "Unknown":
        payout_type = "Hybrid"

    print(payout_type, payout_percent, payout_amount_original, payout_currency)


        
    

    data = {
        "payout_type": row["sale_commission_raw"][:-3],
        "payout_amount_original": row["sale_commission_raw"],
        "payout_currency": row["three_month_epc"][-3:],
        "payout_percent":"",
        "payout_amount_usd":""
    }

def map_json(json):
    mapped_json = []
    for row in json:
        mapped_row = create_offer_candidate(row)
        mapped_json.append(mapped_row)
    return mapped_json

if __name__ == "__main__":
    path = f"data/normalized/cj/advertisers/24-05-2026/12-11-56.json"
    jsonn = import_json(path)
    map_json(jsonn)