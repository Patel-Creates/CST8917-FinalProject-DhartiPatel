# CST8917 Final Project - Dual Implementation of an Expense Approval Workflow

**Name:** Dharti Patel
**Student Number:** 040775191
**Course:** CST8917 - Serverless Applications
**Term:** Winter 2026
**Submission Date:** April 2026
**Youtube link:** https://youtu.be/8QOZ5Vn7JNE
---

## Project Overview

This project implements the same expense approval business workflow using two different Azure serverless orchestration approaches, then compares them based on hands-on experience.

- **Version A:** Azure Durable Functions (Python v2 programming model) - code-first orchestration
- **Version B:** Azure Logic Apps + Azure Service Bus - visual/declarative orchestration

Business rules implemented in both versions:
- Expense validation (required fields + valid category)
- Auto-approval for expenses under $100
- Manager approval workflow for expenses >= $100
- Timeout-based escalation if the manager does not respond
- Email notification to the employee with the final outcome

---

## Version A Summary - Durable Functions

**Architecture:** HTTP client function starts the orchestrator. The orchestrator calls activity functions in sequence: validate expense, check amount, wait for manager decision or timer, send notification. Manager decisions arrive via a separate HTTP endpoint that raises an external event to the running orchestrator.

**Key design decisions:**
- Used `task_any([wait_for_external_event, create_timer])` for the human approval step. This is the native Durable Functions pattern - whichever task completes first wins. The timer fires after 60 seconds in demo mode.
- Kept `send_notification` as a log-only activity locally. In production this would call Azure Communication Services or SendGrid.
- Used anonymous auth for all HTTP triggers to keep local testing simple.

**Challenges:**
- The orchestrator must be deterministic - no `datetime.now()` calls inside it. Used `context.current_utc_datetime` instead.
- zsh quoting issues with curl commands during local testing. Solved by using heredoc syntax.

---

## Version B Summary - Logic Apps + Service Bus

**Architecture:** Expense payloads are sent to the `expense-requests` Service Bus queue. The Logic App triggers on each message, calls the validation Azure Function via HTTP, then branches based on the response. Results are published to the `expense-outcomes` topic with a custom `outcome` property. Three filtered subscriptions (`approved`, `rejected`, `escalated`) route messages based on that property.

**Approach for manager approval:**
Used the Office 365 Outlook connector `Send approval email` action with a 1-minute timeout. The action pauses the Logic App run and sends a clickable Approve/Reject email to the manager. If no response arrives within the timeout, the action returns with a null `SelectedOption`, which routes to the escalated branch.

**Key design decisions:**
- Used `ApiConnectionWebhook` for the approval email so the Logic App is durably paused - no polling needed.
- Nested conditions (`Check_Manager_Decision` then `Check_Reject_Or_Timeout`) instead of `result()` function to avoid the empty-array bug on timeout.
- Service Bus `peek-lock` trigger so messages are not lost if the Logic App run fails.

**Challenges:**
- The `result()` function cannot be called on `ApiConnectionWebhook` actions. Switching to checking `SelectedOption` value (null on timeout) fixed this.
- Building complex JSON bodies in the Logic App visual designer is difficult. Used Code view to edit directly.

---

## Comparison Analysis

### 1. Development Experience

Logic Apps had a lower initial cost of entry. The visual designer gave me a runnable skeleton before writing any expressions, and connectors handled authentication automatically. That speed disappeared as expressions got complex. Writing `@result('Manager_Approval_Scope', 'Succeeded')[0]['status']` inside JSON with no type checking, no autocomplete, and no inline documentation is harder than Python. Durable Functions was slower to start — setting up the v2 Python model, installing the Durable extension, and understanding the orchestrator/activity split took time. But once scaffolded it was more productive: IntelliSense, a real debugger, real stack traces, and the ability to rename variables without breaking an invisible JSON expression tree. For a workflow this complex, the code-first model rewarded investment faster.

### 2. Testability

Durable Functions wins clearly. Activity functions are plain Python functions — I could write pytest unit tests for `validate_expense` and `check_amount` without any Azure infrastructure. The orchestrator can be tested with a mock `DurableOrchestrationContext`, so I could verify the branching logic for auto-approve, manager-approve, manager-reject, and timeout without deploying anything. Logic Apps has no local test story. The only way to verify a branch is to send a real Service Bus message and read run history in the portal. During debugging I could not isolate whether a failure was in `Parse_JSON`, the validation function call, or the topic publish step because all of them executed in one cloud run and the portal only shows the outermost failure. Automated regression testing for Logic Apps is theoretically possible with the Azure Logic Apps Test Framework, but it requires mocking connectors by hand in ARM templates — far more effort than pytest.

### 3. Error Handling

Durable Functions gives granular control via try/except blocks and per-activity `RetryOptions(max_number_of_attempts=3, first_retry_interval_in_milliseconds=5000)`. Each activity can have a different retry policy, and failures surface as typed exceptions with full stack traces. Logic Apps has built-in retry policies and `runAfter` conditions with `[Failed, TimedOut, Skipped]` which handles the common case conveniently. The difficulty is edge cases. My hardest bug was `@result('Manager_Approval_Scope', 'Succeeded')[0]['status']` throwing a runtime error on timeout because the Succeeded array was empty — the scope timed out, so no successful result existed. A Python try/except or a simple `if not results` check would have caught this immediately. In Logic Apps the portal showed a generic "ActionFailed" on `Check_Valid`, two levels above the actual problem. The fix required understanding that `result()` returns a filtered array and adding an explicit `@length(...) > 0` guard. That class of debugging — invisible until runtime, no line number, no stack — is the main reason I would not want to own a complex Logic App in production.

### 4. Human Interaction Pattern

This is where the two platforms differ most fundamentally. Durable Functions uses `context.task_any([wait_for_external_event("ManagerDecision"), create_timer(deadline)])` — one expression, durably checkpointed, instance-correlated. The orchestrator dehydrates while waiting and resumes only when an event arrives or the timer fires. No polling, no wasted compute, no ambiguity about which instance gets the event. Logic Apps uses the `Send approval email` `ApiConnectionWebhook` action with a scope timeout. The action generates a unique callback URL and pauses the run. This works, but callback URLs are embedded in the email body and expire when the run leaves the Running state. A manager who clicks the link after it expires receives a portal error. A manager who clicks an old email from a previous test run can accidentally influence the wrong workflow instance. Durable Functions avoids both problems by design — events are routed by orchestration instance ID, not by URL.

### 5. Observability

Logic Apps wins for the demo: a visual workflow diagram with green checkmarks per action, expandable inputs and outputs, and one-click Application Insights integration. For a stakeholder walkthrough it is the better tool. For debugging it is weaker. The empty-array bug surfaced as a red X on `Check_Valid`, not on the expression that actually failed. Expanding each action to read raw JSON inputs and outputs is tedious when there are fifteen actions in a run. Durable Functions requires more setup — Application Insights plus structured logging — but once configured gives richer data: queryable orchestration history, per-activity execution times, and the ability to replay an orchestration from a specific checkpoint. At scale, the structured history is more useful than a visual diagram.

### 6. Cost

**Assumptions:** each expense triggers 1 validation function call, 1 conditional branch, 1 Service Bus or storage operation, 1 notification, and (for the 25% needing manager review) 1 approval email action. Durable Functions storage uses Azure Storage at standard rates. Logic Apps Standard tier pricing applies.

| Scenario | Durable Functions | Logic Apps + Service Bus |
|----------|-------------------|--------------------------|
| 100 expenses/day (~3,000/month) | ~$1–2/month | ~$8–12/month |
| 10,000 expenses/day (~300,000/month) | ~$35–50/month | ~$600–900/month |

Logic Apps Standard bills per action execution. One expense run uses 10–15 actions; at 10,000 expenses/day that is roughly 4.5 million action executions per month. Durable Functions bills per execution plus GB-seconds of memory, and idle waits cost nothing because the orchestrator is dehydrated. At high volume the difference is roughly an order of magnitude.

---

## Recommendation

**For production: Durable Functions.**

Manager approval with timeout is the business-critical requirement of this workflow, and Durable Functions models it natively with `task_any`. That single design choice eliminated three failure modes I encountered in Version B: expired callback URLs in approval emails, empty-array runtime errors on scope timeout, and the risk of a stale email triggering the wrong workflow instance. Beyond correctness, the code-first model enables unit testing of every activity function, structured error handling with typed exceptions, and a cost curve that stays flat at volume — roughly $35–50/month at 10,000 expenses/day versus $600–900/month for Logic Apps at the same load.

The tradeoff is setup complexity. Durable Functions requires understanding the orchestrator/activity split, the determinism rules (no `datetime.now()` inside the orchestrator), and the v2 Python programming model. Logic Apps gets a simple workflow running in under an hour.

**Logic Apps is the right choice when:** the team building and owning the workflow is not composed of developers, the volume is low (under 100 per day), or deep integration with pre-built SaaS connectors — Salesforce, ServiceNow, SAP, Office 365 — matters more than programmability. The managed connectors and visual designer are real advantages in those scenarios, and the higher per-action cost is acceptable at low scale.

For a team with developers building a workflow that is central to a business process, Durable Functions is the more reliable, more testable, and more cost-effective choice at any non-trivial volume.

---

## Repository Structure

```
CST8917-FinalProject-DhartiPatel/
├── README.md
├── version-a-durable-functions/
│   ├── function_app.py
│   ├── requirements.txt
│   ├── host.json
│   ├── local.settings.example.json
│   └── test-durable.http
├── version-b-logic-apps/
│   ├── README.md
│   ├── function_app.py
│   ├── requirements.txt
│   ├── host.json
│   ├── local.settings.example.json
│   ├── test-expense.http
│   └── screenshots/
└── presentation/
    ├── slides.pptx
    └── video-link.md
```

---

## How to Run

### Version A - Durable Functions

```bash
cd version-a-durable-functions
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp local.settings.example.json local.settings.json
func start
```

Open `test-durable.http` in VS Code with the REST Client extension and run each scenario.

### Version B - Logic Apps + Service Bus

See `version-b-logic-apps/README.md` for Azure resource details and the screenshots folder for test evidence.

---

## References

- [Azure Durable Functions docs](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Durable Functions Human Interaction pattern](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview#human)
- [Azure Logic Apps docs](https://learn.microsoft.com/en-us/azure/logic-apps/)
- [Azure Service Bus docs](https://learn.microsoft.com/en-us/azure/service-bus-messaging/)
- [Service Bus SQL filters](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-messaging-sql-filter)
- [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)

---

## AI Disclosure

AI tools were used during this project as follows:
- **Tool(s):** Claude (Anthropic)
- **How used:** Debugging Logic Apps JSON errors, fixing curl quoting issues, generating test payloads, editing workflow JSON, explaining error messages and structure the readme
- **What was NOT AI-generated:** Architecture decisions, technical observations in the comparison, the recommendation, and the hands-on testing experience

All AI-suggested code and writing was reviewed and understood before inclusion. All external references are cited above.
