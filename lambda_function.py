import json
import os
import urllib.request
import psycopg2
from datetime import datetime, timezone


def fetch_stocks():
    req = urllib.request.Request(
        "https://www.cse.lk/api/tradeSummary",
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=b"",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["reqOutput"]


def lambda_handler(event, context):
    prices = fetch_stocks()
    now = datetime.now(timezone.utc)

    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )

    try:
        with conn.cursor() as cur:
            # Load all stocks keyed by symbol
            cur.execute('SELECT "ID", "SYMBOL" FROM market."STOCK"')
            stock_map = {row[1]: row[0] for row in cur.fetchall()}

            count = 0
            for p in prices:
                stock_id = stock_map.get(p.get("symbol"))
                if not stock_id:
                    continue

                cur.execute(
                    """
                    INSERT INTO market."STOCK_PRICE"
                        ("STOCK_ID", "PRICE", "OPEN", "HIGH", "LOW", "CHANGE", "CHANGE_PCT", "VOLUME", "COLLECTED_AT")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        stock_id,
                        p.get("price"),
                        p.get("open"),
                        p.get("high"),
                        p.get("low"),
                        p.get("change"),
                        p.get("percentageChange"),
                        p.get("sharevolume"),
                        now,
                    ),
                )
                count += 1

            conn.commit()
    finally:
        conn.close()

    return {"statusCode": 200, "body": f"Saved {count} price snapshots"}
