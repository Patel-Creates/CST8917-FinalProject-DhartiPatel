# Version B - Logic Apps + Service Bus

## Resources

| Resource | Name |
|----------|------|
| Resource Group | `cst8917-final-rg` |
| Service Bus Namespace | `cst8917-expense-ns` (Canada Central) |
| Queue | `expense-requests` |
| Topic | `expense-outcomes` |
| Subscriptions | `approved`, `rejected`, `escalated` (all SqlFilter on `outcome` property) |
| Function App | `cst8917-validate-fn` |
| Logic App | `cst8917-expense-logic` (Consumption) |

## Files

- `function_app.py` - validation Azure Function called by the Logic App
- `screenshots/` - test evidence (see below)

## Known Issue

`Check_Manager_Decision` uses `@result('Manager_Approval_Scope', 'Succeeded')[0]['status']` which errors on empty array when the scope times out. Fix: `@length(result(...)) > 0`. Escalated-path routing was instead validated by publishing directly to the topic with `outcome=escalated` custom property.

## Screenshots

| File | Evidence |
|------|----------|
| `FINAL-all-3-subscriptions.png` | **Main evidence** - all 3 subscriptions populated |
| `s2-01-sbexplorer-send.png` | Scenario 2: message sent to queue |
| `s2-email-approval-received.png` | Scenario 2: approval email received |
| `s2-04-approve-success.png` | Scenario 2: approve callback succeeded |
| `s2-06-topic-approved-count.png` | Scenario 2: approved subscription +1 |
| `s3-01-email-reject-received.png` | Scenario 3: approval email for $500 travel |
| `s3-03-reject-success-clean.png` | Scenario 3: reject callback succeeded |
| `s4-01-email-approval-received.png` | Scenario 4: approval email for $150 software |
| `s4-03-runhistory-failed.png` | Scenario 4: 2-minute timeout in run history |
| `s4-04-checkvalid-actionfailed.png` | Scenario 4: empty-array bug surfaces |
| `s4-06-topic-send-success.png` | Scenario 4: direct topic publish worked |
| `s5-01-email-missing-fields.png` | Scenario 5: validation rejection - missing fields |
| `s6-01-email-invalid-category.png` | Scenario 6: validation rejection - invalid category |
| `approved-subscription-filter.png` | SqlFilter expression reference |
| `topic-metrics-overview.png` | Topic metrics graph |

## Test Payloads

### S1 - Auto-approve
```json
{"employee_name":"Dharti Patel","employee_email":"pate0323@algonquinlive.com","amount":50,"category":"meals","description":"Team lunch","manager_email":"pate0323@algonquinlive.com"}
```

### S2 - Manager approves
```json
{"employee_name":"Dharti Patel","employee_email":"pate0323@algonquinlive.com","amount":250,"category":"equipment","description":"New laptop dock","manager_email":"pate0323@algonquinlive.com"}
```

### S3 - Manager rejects
```json
{"employee_name":"Dharti Patel","employee_email":"pate0323@algonquinlive.com","amount":500,"category":"travel","description":"Conference travel to Toronto","manager_email":"pate0323@algonquinlive.com"}
```

### S4 - Escalation
```json
{"employee_name":"Dharti Patel","employee_email":"pate0323@algonquinlive.com","amount":150,"category":"software","description":"Software license","manager_email":"pate0323@algonquinlive.com"}
```

### S5 - Missing fields
```json
{"employee_name":"Dharti Patel","employee_email":"pate0323@algonquinlive.com","amount":200,"description":"Missing category and manager"}
```

### S6 - Invalid category
```json
{"employee_name":"Dharti Patel","employee_email":"pate0323@algonquinlive.com","amount":75,"category":"bitcoin","description":"Invalid category","manager_email":"pate0323@algonquinlive.com"}
```
