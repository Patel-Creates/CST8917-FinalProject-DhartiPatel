"""
Version A — Durable Functions implementation of Expense Approval Workflow
CST8917 Final Project

Architecture:
- Client function (HTTP trigger) → starts the orchestrator
- Orchestrator function → controls the flow
- Activity functions → validate_expense, send_notification
- Manager decision endpoint (HTTP trigger) → raises an external event to the orchestrator

Human Interaction Pattern:
The orchestrator uses a durable timer + wait_for_external_event race.
Whichever finishes first wins. If the timer wins, the expense is escalated.
"""

import azure.functions as func
import azure.durable_functions as df
import logging
import json
from datetime import timedelta

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Config — tweak for demo vs. production
VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}
AUTO_APPROVE_THRESHOLD = 100  # USD
MANAGER_TIMEOUT_SECONDS = 60  # short for demo; bump up for real use


# ---------------------------------------------------------------------------
# Client function: submit an expense
# ---------------------------------------------------------------------------
@app.route(route="submit-expense")
@app.durable_client_input(client_name="client")
async def submit_expense(req: func.HttpRequest, client) -> func.HttpResponse:
    """
    HTTP POST /api/submit-expense
    Body: { employee_name, employee_email, amount, category, description, manager_email }
    """
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    instance_id = await client.start_new("expense_orchestrator", None, payload)
    logging.info(f"Started orchestration {instance_id}")
    return client.create_check_status_response(req, instance_id)


# ---------------------------------------------------------------------------
# Manager decision endpoint: raises an external event to the waiting orchestrator
# ---------------------------------------------------------------------------
@app.route(route="manager-decision/{instance_id}")
@app.durable_client_input(client_name="client")
async def manager_decision(req: func.HttpRequest, client) -> func.HttpResponse:
    """
    HTTP POST /api/manager-decision/{instance_id}
    Body: { "decision": "approved" | "rejected" }
    """
    instance_id = req.route_params.get("instance_id")
    try:
        body = req.get_json()
        decision = body.get("decision")
    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    if decision not in ("approved", "rejected"):
        return func.HttpResponse("decision must be 'approved' or 'rejected'", status_code=400)

    await client.raise_event(instance_id, "ManagerDecision", decision)
    return func.HttpResponse(f"Decision '{decision}' sent to {instance_id}", status_code=200)


# ---------------------------------------------------------------------------
# Orchestrator: the brain of the workflow
# ---------------------------------------------------------------------------
@app.orchestration_trigger(context_name="context")
def expense_orchestrator(context: df.DurableOrchestrationContext):
    expense = context.get_input()

    # Step 1: validate
    validation = yield context.call_activity("validate_expense", expense)
    if not validation["valid"]:
        yield context.call_activity("send_notification", {
            "expense": expense,
            "outcome": "rejected",
            "reason": validation["reason"],
        })
        return {"status": "rejected", "reason": validation["reason"]}

    # Step 2: auto-approve if under threshold
    if expense["amount"] < AUTO_APPROVE_THRESHOLD:
        yield context.call_activity("send_notification", {
            "expense": expense,
            "outcome": "approved",
            "reason": "auto-approved (under threshold)",
        })
        return {"status": "approved", "reason": "auto"}

    # Step 3: human interaction — wait for manager OR time out
    due_time = context.current_utc_datetime + timedelta(seconds=MANAGER_TIMEOUT_SECONDS)
    timeout_task = context.create_timer(due_time)
    approval_task = context.wait_for_external_event("ManagerDecision")

    winner = yield context.task_any([approval_task, timeout_task])

    if winner == approval_task:
        timeout_task.cancel()
        decision = approval_task.result  # "approved" or "rejected"
        yield context.call_activity("send_notification", {
            "expense": expense,
            "outcome": decision,
            "reason": f"manager {decision}",
        })
        return {"status": decision, "reason": "manager decision"}
    else:
        # Timer fired first → escalate (auto-approve flagged)
        yield context.call_activity("send_notification", {
            "expense": expense,
            "outcome": "escalated",
            "reason": "manager did not respond in time — auto-approved and escalated",
        })
        return {"status": "escalated", "reason": "timeout"}


# ---------------------------------------------------------------------------
# Activity: validate the expense payload
# ---------------------------------------------------------------------------
@app.activity_trigger(input_name="expense")
def validate_expense(expense: dict) -> dict:
    required = ["employee_name", "employee_email", "amount", "category", "description", "manager_email"]
    missing = [f for f in required if not expense.get(f)]
    if missing:
        return {"valid": False, "reason": f"Missing required fields: {', '.join(missing)}"}

    if expense["category"] not in VALID_CATEGORIES:
        return {"valid": False, "reason": f"Invalid category '{expense['category']}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"}

    try:
        amount = float(expense["amount"])
        if amount <= 0:
            return {"valid": False, "reason": "Amount must be greater than 0"}
    except (TypeError, ValueError):
        return {"valid": False, "reason": "Amount must be a number"}

    return {"valid": True, "reason": "OK"}


# ---------------------------------------------------------------------------
# Activity: send notification email to employee
# ---------------------------------------------------------------------------
@app.activity_trigger(input_name="payload")
def send_notification(payload: dict) -> dict:
    """
    For the demo this logs the email. For a real impl, swap in SendGrid /
    Azure Communication Services / SMTP here.
    """
    expense = payload["expense"]
    outcome = payload["outcome"]
    reason = payload["reason"]

    message = (
        f"To: {expense.get('employee_email')}\n"
        f"Subject: Expense request {outcome.upper()}\n"
        f"Hi {expense.get('employee_name')},\n"
        f"Your expense request for ${expense.get('amount')} ({expense.get('category')}) "
        f"has been {outcome}. Reason: {reason}.\n"
    )
    logging.info("=== NOTIFICATION ===\n%s", message)
    return {"sent": True, "outcome": outcome}
