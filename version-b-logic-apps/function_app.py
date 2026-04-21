"""
Version B — Azure Function that validates expense payloads.
Called by the Logic App as an HTTP action.

Returns:
  200 + { valid: true }  if the expense is valid
  200 + { valid: false, reason: "..." }  if invalid
"""

import azure.functions as func
import logging
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}


@app.route(route="validate")
def validate(req: func.HttpRequest) -> func.HttpResponse:
    try:
        expense = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"valid": False, "reason": "Invalid JSON"}),
            status_code=200,
            mimetype="application/json",
        )

    required = ["employee_name", "employee_email", "amount", "category", "description", "manager_email"]
    missing = [f for f in required if not expense.get(f)]
    if missing:
        return _response(False, f"Missing required fields: {', '.join(missing)}")

    if expense.get("category") not in VALID_CATEGORIES:
        return _response(False, f"Invalid category '{expense.get('category')}'. Valid: {', '.join(sorted(VALID_CATEGORIES))}")

    try:
        amount = float(expense["amount"])
        if amount <= 0:
            return _response(False, "Amount must be greater than 0")
    except (TypeError, ValueError):
        return _response(False, "Amount must be a number")

    logging.info("Expense validated successfully for %s", expense.get("employee_email"))
    return _response(True, "OK")


def _response(valid: bool, reason: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"valid": valid, "reason": reason}),
        status_code=200,
        mimetype="application/json",
    )
