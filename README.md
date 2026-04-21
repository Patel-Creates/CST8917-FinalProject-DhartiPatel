# CST8917 Final Project — Dual Implementation of an Expense Approval Workflow

**Name:** Dharti Patel
**Student Number:** [ADD YOUR STUDENT NUMBER]
**Course:** CST8917 — Serverless Applications
**Term:** Winter 2026
**Submission Date:** [ADD DATE]

---

## Project Overview

This project implements the same expense approval business workflow using two different Azure serverless orchestration approaches, then compares them based on hands-on experience.

- **Version A:** Azure Durable Functions (Python v2 programming model) — code-first orchestration
- **Version B:** Azure Logic Apps + Azure Service Bus — visual/declarative orchestration

Business rules implemented in both versions:
- Expense validation (required fields + valid category)
- Auto-approval for expenses under $100
- Manager approval workflow for expenses >= $100
- Timeout-based escalation if the manager doesn't respond
- Email notification to the employee with the final outcome

---

## Version A Summary — Durable Functions

**Architecture:** [fill in after building — e.g. client function, orchestrator, activity functions, HTTP endpoint for manager decision]

**Key design decisions:**
- [decision 1 — e.g. why you chose `wait_for_external_event` vs polling]
- [decision 2]
- [decision 3]

**Challenges:**
- [what got you stuck, what you learned]

---

## Version B Summary — Logic Apps + Service Bus

**Architecture:** [fill in — Service Bus queue, Logic App, validation Azure Function, topic with filtered subscriptions]

**Approach for manager approval:**
[Logic Apps does not natively support the Human Interaction pattern. Document your approach here — e.g. approval email with action links, a callback HTTP trigger, or a polling loop against a database.]

**Key design decisions:**
- [decision 1]
- [decision 2]

**Challenges:**
- [what got you stuck]

---

## Comparison Analysis

*Target: 800–1200 words. Address ALL six dimensions with specific, experience-based observations.*

### 1. Development Experience

[Which was faster to build? Easier to debug? Which gave you more confidence the logic was correct?]

### 2. Testability

[Which was easier to test locally? Could you write automated tests for either?]

### 3. Error Handling

[How does each handle failures? Which gives more control over retries and recovery?]

### 4. Human Interaction Pattern

[How did each handle "wait for manager approval"? Which was more natural?]

### 5. Observability

[Which made it easier to monitor runs and diagnose problems?]

### 6. Cost

[Estimate cost at ~100 expenses/day and ~10,000 expenses/day. Use the Azure Pricing Calculator. State your assumptions.]

**Cost Assumptions:**
- [e.g. average execution time, memory, number of activities per run, email service, etc.]

| Scenario | Durable Functions | Logic Apps + Service Bus |
|----------|-------------------|--------------------------|
| 100 expenses/day | $ | $ |
| 10,000 expenses/day | $ | $ |

---

## Recommendation

*Target: 200–300 words.*

[Which approach would you choose for production and why? When would you choose the other instead?]

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

### Version A — Durable Functions

```bash
cd version-a-durable-functions
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp local.settings.example.json local.settings.json
# Fill in real values in local.settings.json
func start
```

Submit an expense:
```bash
# see test-durable.http for all scenarios
```

### Version B — Logic Apps + Service Bus

See `version-b-logic-apps/README.md` for deployment steps and screenshots folder for Azure Portal evidence.

---

## References

- [Azure Durable Functions docs](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Durable Functions Human Interaction pattern](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview#human)
- [Azure Logic Apps docs](https://learn.microsoft.com/en-us/azure/logic-apps/)
- [Azure Service Bus docs](https://learn.microsoft.com/en-us/azure/service-bus-messaging/)
- [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)
- [add the rest as you go]

---

## AI Disclosure

*Required by CST8917 AI Policy. Be honest and specific.*

AI tools were used during this project as follows:
- **Tool(s):** [e.g. Claude, GitHub Copilot, ChatGPT]
- **How used:** [e.g. scaffolding initial function signatures, debugging error messages, drafting comparison analysis outline, generating test payloads]
- **What was NOT AI-generated:** [e.g. architecture decisions, comparison observations based on personal experience, final recommendation]

All AI-suggested code and writing was reviewed, understood, and modified before inclusion. All external references are cited above.
