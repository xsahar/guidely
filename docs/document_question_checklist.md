# Document Search Question Checklist

Use these questions to test retrieval and answers. Upload each document in **Manage Documents** first; a successful upload indexes it immediately. Each question should show the listed source filename when the answer is supported by that document.

## `pto_policy.txt`

- How many paid vacation days do employees receive each year?  
  Expected: 20 paid leave days annually, accrued monthly.
- How many unused PTO days can roll over into the next year?  
  Expected: Up to 5 days.
- How many paid sick days are provided each year?  
  Expected: 10 paid sick days.
- When is a doctor's note not required for sick leave?  
  Expected: For absences under 3 consecutive business days.
- How much parental leave do primary and secondary caregivers receive?  
  Expected: 12 weeks for primary caregivers and 6 weeks for secondary caregivers.

## `it_policy.txt`

- What equipment does each employee receive?  
  Expected: A corporate laptop.
- How do employees request new software?  
  Expected: Submit a request through the IT Helpdesk; only pre-approved software may be installed.
- How quickly must operating system and security patches be installed?  
  Expected: Within 48 hours of the prompt.

## `remote_work_policy.txt`

- During what hours should full-time employees be reachable?  
  Expected: 10:00 AM to 4:00 PM local time, via Slack and email.
- What remote-work costs are reimbursed?  
  Expected: A one-time home-office setup allowance upon hire and a monthly internet reimbursement.
- How often are company-wide offsites held, and who covers travel and lodging?  
  Expected: Twice a year; Guidely covers travel and lodging.

## `security_policy.txt`

- What authentication method is required for employee accounts?  
  Expected: 2FA using an authenticator app.
- Can employees request hardware security keys?  
  Expected: Yes, hardware security keys are provided upon request.
- What security setting must be enabled on company laptops?  
  Expected: Full Disk Encryption, using BitLocker or FileVault.
- What must developers do before using an open-source library in production?  
  Expected: Register it in the security portal.

## `code_of_conduct.txt`

- What does the company promise about the workplace?  
  Expected: An inclusive environment free from harassment or discrimination.
- How must non-public business information and user data be handled?  
  Expected: They must remain strictly confidential.
- How can employees report ethical concerns?  
  Expected: Directly to HR or through the anonymous ethics channel.

## `wsl_api_test.txt`

- What networking mode does WSL2 use?  
  Expected: `mirrored`.
- What value is configured for DNS tunneling?  
  Expected: `true`.
- What does API stand for in the notes?  
  Expected: Application Programming Interface.
- Which port does the internal test API use?  
  Expected: `8123`.
- What is the health-check endpoint?  
  Expected: `/health`.

## Interpreting results

- Check that each answer is supported by the listed document and that the source filename is displayed.
- A question asking for information absent from the documents should get a no-answer response with no source.
- `api-key (cursor).txt` is not included: its filename suggests it may contain a credential. Do not upload or share API keys or other secrets as searchable documents.
