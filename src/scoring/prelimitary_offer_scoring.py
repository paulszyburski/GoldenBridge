import os
import json as js
from datetime import datetime

def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = js.load(f)

    return data

def export_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        js.dump(data, f, ensure_ascii=False, indent=2)

def score_json(json):
    points = 0
    risk_signals = []
    next_action = []

    if json["payout_type"] == "CPA":
        if json["payout_amount_original"] == "Unknown": 
            points += 0
            risk_signals.append("PAYOUT_AMOUNT_UNKNOWN")
        elif json["payout_amount_original"] >= 150: points += 35
        elif json["payout_amount_original"] >= 80: points += 30
        elif json["payout_amount_original"] >= 30: points += 22
        elif json["payout_amount_original"] >= 15: points += 20
        elif json["payout_amount_original"] < 15 : points += 3

    elif json["payout_type"] == "RevShare":
        if json["payout_percent"] == "Unknown":
            points += 0
            risk_signals.append("PAYOUT_PERCENT_UNKNOWN")
        elif json["payout_percent"] >= 50: points += 25
        elif json["payout_percent"] >= 25: points += 20
        elif json["payout_percent"] >= 10: points += 14
        elif json["payout_percent"] >= 5: points += 8
        elif json["payout_percent"] < 5: points += 4
        risk_signals.append("REVSHARE_REQUIRES_ESTIMATION")
    
    if json["payout_percent"] == None and json["payout_amount_original"] == None:
        risk_signals.append("PAYOUT_UNKNOWN")
    elif json["payout_type"] == "Hybrid":
        if json["payout_percent"] == None: risk_signals.append("PAYOUT_PERCENT_UNKNOWN")
        elif json["payout_amount_original"] == None: risk_signals.append("PAYOUT_AMOUNT_UNKNOWN")

        elif json["payout_percent"] > json["payout_amount_original"]: 
            if json["payout_percent"] == "Unknown":
                points += 0
                risk_signals.append("PPAYOUT_ERCENT_UNKNOWN")
            elif json["payout_percent"] >= 50: points += 25
            elif json["payout_percent"] >= 25: points += 20
            elif json["payout_percent"] >= 10: points += 14
            elif json["payout_percent"] >= 5: points += 8
            elif json["payout_percent"] < 5: points += 4
            risk_signals.append("REVSHARE_REQUIRES_ESTIMATION")

        elif json["payout_percent"] < json["payout_amount_original"]:
            if json["payout_amount_original"] == "Unknown": 
                points += 0
                risk_signals.append("PAYOUT_AMOUNT_UNKNOWN")
            elif json["payout_amount_original"] >= 150: point += 35
            elif json["payout_amount_original"] >= 80: point += 30
            elif json["payout_amount_original"] >= 30: point += 22
            elif json["payout_amount_original"] >= 15: point += 20
            elif json["payout_amount_original"] < 15 : point += 3
        risk_signals.append("HYBRID_PAYOUT_NEEDS_NORMALIZATION")

    if json["three_month_epc_original"] == "Unknown" and json["seven_day_epc_original"] == "Unknown":
        risk_signals.append("EPC_MISSING")

    if json["three_month_epc_original"] != "Unknown":
        if json["three_month_epc_original"] >= 100: points += 20
        elif json["three_month_epc_original"] >= 50: points += 16
        elif json["three_month_epc_original"] >= 20: points += 12
        elif json["three_month_epc_original"] >= 5: points += 7
        elif json["three_month_epc_original"] < 0: points += 3
        else: risk_signals.append("EPC_ZERO")
    
    if json["seven_day_epc_original"] != None:
        if json["seven_day_epc_original"] >= 100: points += 20
        elif json["seven_day_epc_original"] >= 50: points += 16
        elif json["seven_day_epc_original"] >= 20: points += 12
        elif json["seven_day_epc_original"] >= 5: points += 7
        elif json["seven_day_epc_original"] < 0: points += 3
        else: risk_signals.append("EPC_ZERO")

    if len(json["target_markets"]) != 0: points += 15
    else: risk_signals.append("NO_AVAILABLE_MARKETS")

    if json["affiliate_approval_difficulty"] == "Unknown": points -= 1
    if json["affiliate_approval_difficulty"] == "easy": points += 2
    if json["affiliate_approval_difficulty"] == "medium": points += 0
    if json["affiliate_approval_difficulty"] == "premium": points -= 3

    if json["payout_type"] == "Unknown" or "NO_AVAILABLE_MARKETS" in risk_signals:
        next_action.append("blocked")
    elif "COOKIE_WINDOW_UNKNOWN" in json["reason_codes"] or "TERMS_UNKNOWN" in json["reason_codes"] or "REVSHARE_REQUIRES_ESTIMATION" in risk_signals:
        next_action.append("needs_enrichment")

    else:
        next_action.append("scorable_basic")
    #TODO: ADD OTHER ROWS LIKE COOKIE WINDOW

    return points, risk_signals, next_action
   

def shape_json(json):
    scored_jsons = []
    for row in json:
        print(row)
        points, risk_signals, next_action = score_json(row)
        scored_json = {
            "platform_id": row["platform_id"],
            "offer_id": row["offer_id"],
            "offer_name": row["offer_name"],
            "preliminary_score": points,
            "next_action": next_action,
            "risk_signals": risk_signals,
        }
        scored_jsons.append(scored_json)
    return scored_jsons

if __name__ == "__main__":
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")
    input_path = "data/processed/cj/advertisers/25-05-2026/17-51-48.json"
    output_path = f"data/scored/cj/advertisers/{today}/{now}.json"

    json = import_json(input_path)
    scored_json = shape_json(json)
    export_json(output_path, scored_json)