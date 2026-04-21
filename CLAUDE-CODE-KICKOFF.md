# Claude Code Kickoff

Use this file as a reference when prompting Claude Code. Delete or ignore after submission.

## Project Context

CST8917 Final Assignment — dual implementation of an Expense Approval Workflow.
- Version A: Azure Durable Functions (Python v2 model)
- Version B: Azure Logic Apps + Service Bus (with an Azure Function for validation)

See `/README.md` in the repo root for the full spec and deliverables.

## First prompt to paste into Claude Code

> I'm working on my CST8917 final assignment — an Expense Approval Workflow implemented twice (Durable Functions vs Logic Apps + Service Bus). The repo is already scaffolded. I want to start with Version A.
>
> Please:
> 1. Read `version-a-durable-functions/function_app.py` and confirm the orchestrator logic matches the six test scenarios in `test-durable.http`.
> 2. Help me set up a local run: Python venv, install deps, start Azurite, then `func start`.
> 3. Walk me through running scenario 1 (auto-approved under $100) end-to-end and show me what logs to look for.
> 4. Don't change the architecture without asking — the Human Interaction pattern (durable timer + `wait_for_external_event`) is a grading requirement.

## Once Version A works, next prompt

> Version A is running locally and all 6 scenarios pass. Now help me:
> 1. Swap the `send_notification` activity from a log-only stub to actually sending email via Azure Communication Services (or SendGrid if easier).
> 2. Deploy Version A to Azure (Function App + Storage Account).
> 3. Re-run the 6 scenarios against the deployed version and capture the outputs.

## For Version B

> Starting Version B now. I've got `version-b-logic-apps/function_app.py` for validation. Help me:
> 1. Provision the Service Bus namespace, queue (`expense-requests`), and topic (`expense-outcomes`) with 3 filtered subscriptions via Azure CLI or bicep.
> 2. Scaffold the Logic App definition JSON so I can import it into the portal.
> 3. Decide and document the manager-approval approach (Office 365 approval email is probably easiest).

## Ground rules for Claude Code

- Don't commit `local.settings.json`, keys, or connection strings.
- Ask before changing architecture decisions already documented in the README.
- When stuck, suggest Azure CLI commands I can run rather than clicking through the portal, so the steps are reproducible.
