# CST8917 Final Project - Dual Implementation of an Expense Approval Workflow

**Name:** Dharti Patel
**Student Number:** 040775191
**Course:** CST8917 - Serverless Applications
**Term:** Winter 2026
**Submission Date:** April 2026

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

Logic Apps had a lower initial cost of entry. The visual designer gave me a runnable skeleton before writing any expressions, and connectors handled authentication automatically. That speed disappeared as expressions got complex. Writing `@result('Manager_Approval_Scope', 'Succeeded')[0]['status']` inside JSON with no type checking, no autocomplete, and no inline documentation is harder than Python. Durable Functions was slower to start but more productive once scaffolded - IntelliSense, a real debugger, and real stack traces made iteration faster.

### 2. Testability

Durable Functions wins. Activity functions are plain Python functions, unit-testable with pytest. Orchestrator tests can use a mock `DurableOrchestrationContext`. Logic Apps has no local test story - the only way to verify a branch is to send a real message and inspect run history in the portal. During debugging I could not isolate whether a failure was in `Parse_JSON`, the validation function, or the topic publish because all three ran in a single cloud execution.

### 3. Error Handling

Durable Functions gives granular control via try/except and per-activity `RetryOptions`. Logic Apps has built-in retry policies and `runAfter` with `[Failed, TimedOut]` which is convenient for common cases but breaks down at edge cases. My biggest issue was `@result('Manager_Approval_Scope', 'Succeeded')[0]['status']` throwing on an empty array when the scope timed out. A Python try/except would have caught this immediately. In Logic Apps the signal was a generic "ActionFailed" on `Check_Valid` - two levels above the actual bug. Fix was `@length(result(...)) > 0`.

### 4. Human Interaction Pattern

This is where the two platforms differ most. Durable Functions uses `context.task_any([wait_for_external_event("ManagerDecision"), create_timer(deadline)])` - whichever fires first wins, in a single expression, durably checkpointed. Logic Apps uses `ApiConnectionWebhook` with a callback URL and a scope timeout. Callback URLs expire when the run completes, so users clicking old emails get a "workflow not in Running state" error. Clicking the wrong email is a UX failure that Durable Functions avoids by design - events correlate by instance ID, not by URL.

### 5. Observability

Logic Apps wins for the demo: visual workflow diagram with green checkmarks, inputs and outputs per action, and one-click App Insights integration. Durable Functions requires more setup but gives richer data - queryable orchestration state, replay from any checkpoint, and structured history. For the empty-array bug specifically, Logic Apps observability obscured the root cause. The red X showed on `Check_Valid`, not where the actual error occurred.

### 6. Cost

**Assumptions:** 1 validation call + 1 manager email + 1 topic publish + 1 notification per expense. About 75% auto-approved, 25% require manager approval.

| Scenario | Durable Functions | Logic Apps + Service Bus |
|----------|-------------------|--------------------------|
| 100 expenses/day | ~$2/month | ~$8-12/month |
| 10,000 expenses/day | ~$40/month | ~$600-900/month |

Logic Apps bills per action. One expense run uses 10-15 actions. Durable Functions bills per execution plus GB-seconds, and idle waits cost nothing because the orchestrator is dehydrated while waiting.

---

## Recommendation

**For production: Durable Functions.** Manager approval is the core of this workflow, and Durable Functions models it natively. This eliminates three classes of bugs I hit in Version B: expired callbacks, empty-array expressions on timeout, and polling concurrency issues. The cost curve also punishes Logic Apps past a few hundred executions per day.

**Logic Apps is the better choice when:** the team is non-developer, the workflow is low volume (under 50 per day), or heavy integration with SaaS systems like Salesforce, ServiceNow, or SAP matters more than programmability. The visual designer and managed connectors are real advantages in those scenarios.

If I were building this for a production team with developers, I would use Durable Functions. If I were building it for a business team that needs to modify the workflow themselves without touching code, I would use Logic Apps.

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
- **How used:** Debugging Logic Apps JSON errors, fixing curl quoting issues, generating test payloads, editing workflow JSON, explaining error messages
- **What was NOT AI-generated:** Architecture decisions, technical observations in the comparison, the recommendation, and the hands-on testing experience

All AI-suggested code and writing was reviewed and understood before inclusion. All external references are cited above.
