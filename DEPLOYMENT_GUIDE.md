# Stock Price Collector - Deployment Guide

## 1. Create the GitHub Repo

```bash
gh repo create stock-price-collector --private
git checkout -b develop
```

## 2. Add GitHub Secrets

Go to **repo → Settings → Secrets and variables → Actions** and add:

| Secret                  | Value                    |
|-------------------------|--------------------------|
| `AWS_ACCESS_KEY_ID`     | Your IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM user secret key |
| `AWS_REGION`            | e.g. `ap-southeast-1`   |

## 3. Create the Lambda Function

```bash
aws lambda create-function \
  --function-name stock-price-collector \
  --runtime python3.12 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::<ACCOUNT_ID>:role/<LAMBDA_ROLE> \
  --timeout 60
```

## 4. IAM Role Permissions

The Lambda execution role needs:

- `AWSLambdaBasicExecutionRole` (CloudWatch logs)
- `secretsmanager:GetSecretValue` for `stock-collector/db-credentials`
- VPC access if your PostgreSQL is in a VPC

## 5. Create the Secret in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name stock-collector/db-credentials \
  --secret-string '{"host":"<DB_HOST>","port":5432,"dbname":"<DB_NAME>","username":"<DB_USER>","password":"<DB_PASS>"}'
```

## 6. Create the STOCK_PRICE Table

```sql
CREATE TABLE market."STOCK_PRICE" (
    "ID" int8 GENERATED ALWAYS AS IDENTITY NOT NULL,
    "STOCK_ID" int8 NOT NULL REFERENCES market."STOCK"("ID"),
    "PRICE" decimal(12,2),
    "OPEN" decimal(12,2),
    "HIGH" decimal(12,2),
    "LOW" decimal(12,2),
    "CHANGE" decimal(12,2),
    "CHANGE_PCT" decimal(8,2),
    "VOLUME" bigint,
    "COLLECTED_AT" timestamp NOT NULL
);
```

## 7. Create EventBridge Rule (Every 1 Minute)

```bash
aws events put-rule \
  --name stock-price-every-minute \
  --schedule-expression "rate(1 minute)"

aws lambda add-permission \
  --function-name stock-price-collector \
  --statement-id eventbridge-invoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<REGION>:<ACCOUNT_ID>:rule/stock-price-every-minute

aws events put-targets \
  --rule stock-price-every-minute \
  --targets "Id"="1","Arn"="arn:aws:lambda:<REGION>:<ACCOUNT_ID>:function:stock-price-collector"
```

## 8. Push Code to Deploy

```bash
git add lambda_function.py requirements.txt .gitignore .github/
git commit -m "Initial stock price collector lambda"
git push -u origin develop
```

This triggers the GitHub Action which packages and deploys to Lambda automatically.
Every subsequent push to `develop` will redeploy.
