import json as js
import os
from datetime import datetime, timezone


def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return js.load(f)


def export_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        js.dump(data, f, ensure_ascii=False, indent=2)


def _score_payout(row, positive_signals, risk_signals):
    payout_type = row.get("payout_type")
    payout_amount = row.get("payout_amount_original")
    payout_percent = row.get("payout_percent")

    points = 0

    if payout_type in ("CPA", "CPL"):
        positive_signals.append("CPA_PAYOUT_PRESENT")
        if payout_amount is None:
            risk_signals.append("PAYOUT_AMOUNT_UNKNOWN")
            return 0
        if payout_amount >= 150:
            positive_signals.append("PAYOUT_ABOVE_150_USD")
            return 35
        if payout_amount >= 80:
            positive_signals.append("PAYOUT_ABOVE_80_USD")
            return 30
        if payout_amount >= 30:
            return 22
        if payout_amount >= 15:
            return 20
        return 3

    if payout_type == "RevShare":
        positive_signals.append("REVSHARE_PAYOUT_PRESENT")
        if payout_percent is None:
            risk_signals.append("PAYOUT_PERCENT_UNKNOWN")
            return 0
        if payout_percent >= 50:
            return 25
        if payout_percent >= 25:
            return 20
        if payout_percent >= 10:
            return 14
        if payout_percent >= 5:
            return 8
        return 4

    if payout_type == "Hybrid":
        risk_signals.append("HYBRID_PAYOUT_NEEDS_NORMALIZATION")
        # Prefer stronger of amount/percent path for preliminary score.
        if payout_amount is not None:
            points = max(points, _score_payout({"payout_type": "CPA", "payout_amount_original": payout_amount}, positive_signals, risk_signals))
        if payout_percent is not None:
            points = max(points, _score_payout({"payout_type": "RevShare", "payout_percent": payout_percent}, positive_signals, risk_signals))
        if payout_amount is None and payout_percent is None:
            risk_signals.append("PAYOUT_UNKNOWN")
        return points

    risk_signals.append("PAYOUT_UNKNOWN")
    return 0


def _score_epc(row, risk_signals):
    three_month_epc = row.get("three_month_epc_original")
    seven_day_epc = row.get("seven_day_epc_original")

    if three_month_epc is None and seven_day_epc is None:
        risk_signals.append("EPC_MISSING")
        return 0

    epc_value = three_month_epc if three_month_epc is not None else seven_day_epc

    if epc_value is None:
        return 0
    if epc_value >= 100:
        return 20
    if epc_value >= 50:
        return 16
    if epc_value >= 20:
        return 12
    if epc_value >= 5:
        risk_signals.append("EPC_TOO_LOW")
        return 7
    if epc_value > 0:
        risk_signals.append("EPC_TOO_LOW")
        return 3

    risk_signals.append("EPC_ZERO")
    return 0


def _score_market(row, positive_signals, risk_signals):
    markets = row.get("target_markets") or []
    if not markets:
        risk_signals.append("NO_AVAILABLE_MARKETS")
        return 0

    if "U.S." in markets or "UNITED STATES" in markets:
        positive_signals.append("US_MARKET_SIGNAL")
        return 20
    return 15


def _score_data_completeness(row, positive_signals):
    points = 0

    if row.get("partner_terms_available"):
        positive_signals.append("PARTNER_TERMS_PRESENT")
        points += 5

    if row.get("cookie_window_days") is not None:
        positive_signals.append("COOKIE_WINDOW_PRESENT")
        points += 5

    return points

def _filter_categories(row, risk_signals):
    pass

def _score_access(row, risk_signals):
    difficulty = row.get("affiliate_approval_difficulty")
    access_status = row.get("affiliate_access_status")

    if access_status == "not_applied":
        risk_signals.append("NOT_APPLIED")

    if row.get("approval_required_before_scaling"):
        risk_signals.append("APPROVAL_REQUIRED_BEFORE_SCALING")

    if difficulty == "easy":
        return 5
    if difficulty == "medium":
        return 3
    if difficulty == "premium":
        return 1
    return 2


def score_row(row, file):
    positive_signals = []
    risk_signals = []
    blocking_reasons = []

    payout_points = _score_payout(row, positive_signals, risk_signals)
    epc_points = _score_epc(row, risk_signals)
    market_points = _score_market(row, positive_signals, risk_signals)
    data_completeness_points = _score_data_completeness(row, positive_signals)
    access_points = _score_access(row, risk_signals)

    composite_offer_score = min(100, max(0, payout_points + epc_points + market_points + data_completeness_points + access_points))/100

    if composite_offer_score >= 0.7:
        score_offer_tier = "high"
    elif 0.69 >= composite_offer_score >= 0.55:
        score_offer_tier = "medium"
    elif 0.54 >= composite_offer_score >= 0.35:
        score_offer_tier = "low"
    else:
        score_offer_tier = "reject"

    if "NO_AVAILABLE_MARKETS" in risk_signals:
        blocking_reasons.append("NO_AVAILABLE_MARKETS")
    if "PAYOUT_UNKNOWN" in risk_signals:
        blocking_reasons.append("PAYOUT_UNKNOWN")
    if row["cookie_window_days"] == "Unknown":
        blocking_reasons.append("COOKIE_WINDOW_DAYS_UNKNOWN")
    elif row["cookie_window_days"] >= 30:
        blocking_reasons.append("COOKIE_WINDOW_DAYS_TOO_SHORT")
    if "PROHIBITED_CATEGORY" in risk_signals:
        blocking_reasons.append("PROHIBITED_CATEGORY")
    if row["partner_terms_available"] == False:
        blocking_reasons.append("TERMS_UNKNOWN")
    if score_offer_tier == "reject":
        blocking_reasons.append("SCORE_TOO_LOW")

    if blocking_reasons:
        scoring_status = "blocked"
    elif any(code in risk_signals for code in ["PAYOUT_AMOUNT_UNKNOWN", "PAYOUT_PERCENT_UNKNOWN", "EPC_MISSING"]):
        scoring_status = "needs_enrichment"
    else:
        scoring_status = "scoreable_basic"

    source_file = row.get("source_file")
    source_row_id = row.get("source_row_id")

    return {
        "platform_id": row.get("platform_id"),
        "offer_id": row.get("offer_id"),
        "partner_id": row.get("partner_id", row.get("offer_id")),
        "offer_name": row.get("offer_name"),
        "category": row.get("category"),
        "scoring_type": "preliminary_offer_score",
        "scoring_version": "v0.1",
        "composite_offer_score": composite_offer_score,
        "score_max_points": 1,
        "score_tier": score_offer_tier,
        "scoring_status": scoring_status,
        "score_breakdown": {
            "payout_points": payout_points,
            "epc_points": epc_points,
            "market_points": market_points,
            "data_completeness_points": data_completeness_points,
            "access_points": access_points,
        },
        "positive_signals": sorted(set(positive_signals)),
        "risk_signals": sorted(set(risk_signals)),
        "next_actions": [
            "APPLY_TO_PROGRAM_IF_SELECTED",
            "FETCH_PROGRAM_URL",
        ],
        "blocking_reasons": blocking_reasons,
        "source_offer_ref": {
            "source_file": source_file,
            "processed_source_file": file,
            "source_row_id": source_row_id,
        },
        "scored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def shape_json(rows, file):
    return [score_row(row, file) for row in rows]


if __name__ == "__main__":
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")
    input_path = "data/processed/cj/advertisers/26-05-2026/21-48-46.json"
    output_path = f"data/scored/cj/advertisers/{today}/{now}.json"

    raw_json = import_json(input_path)
    scored_json = shape_json(raw_json, input_path)
    print(len(scored_json))
    export_json(output_path, scored_json)
