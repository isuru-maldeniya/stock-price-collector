---
name: Secrets via Lambda env vars
description: DB credentials stored in Lambda environment variables instead of AWS Secrets Manager
type: project
---

DB credentials (host, port, dbname, user, password) are stored as Lambda environment variables, not AWS Secrets Manager.

**Why:** User decided Secrets Manager is unnecessary for this project; env vars are simpler.

**How to apply:** Never introduce Secrets Manager references. DB config comes from `os.environ` in the Lambda code.
