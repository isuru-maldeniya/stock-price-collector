import json
import os
import ssl
import urllib.request
import pg8000.native
from datetime import datetime, timezone


def fetch_stocks():
    req = urllib.request.Request(
        "https://www.cse.lk/api/tradeSummary",
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=b"",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        print("API response keys:", data["reqTradeSummery"])
        return data["reqTradeSummery"]


def lambda_handler(event, context):
    prices = fetch_stocks()
    now = datetime.now(timezone.utc)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = pg8000.native.Connection(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        ssl_context=ssl_context,
    )

    try:
        # Load all stocks keyed by symbol
        rows = conn.run('SELECT "ID", "SYMBOL" FROM market."STOCK"')
        stock_map = {row[1]: row[0] for row in rows}

        count = 0
        for p in prices:
            stock_id = stock_map.get(p.get("symbol"))
            if not stock_id:
                continue

            conn.run(
                """
                INSERT INTO market."STOCK_PRICE"
                    ("STOCK_ID", "PRICE", "OPEN", "HIGH", "LOW", "CHANGE", "CHANGE_PCT", "VOLUME", "COLLECTED_AT")
                VALUES (:sid, :price, :open, :high, :low, :change, :pct, :vol, :ts)
                """,
                sid=stock_id,
                price=p.get("price"),
                open=p.get("open"),
                high=p.get("high"),
                low=p.get("low"),
                change=p.get("change"),
                pct=p.get("percentageChange"),
                vol=p.get("sharevolume"),
                ts=now,
            )
            count += 1

        conn.run("COMMIT")
    finally:
        conn.close()

    return {"statusCode": 200, "body": f"Saved {count} price snapshots"}
