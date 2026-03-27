import os
import requests
import psycopg2
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def fetch_stocks():
    resp = requests.post(
        "https://www.cse.lk/api/tradeSummary",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=b"",
        timeout=30,
    )
    resp.raise_for_status()
    print("Fetched stock data successfully: ", resp.json()["reqTradeSummery"])
    return resp.json()["reqTradeSummery"]


def lambda_handler(event, context):
    prices = fetch_stocks()
    now = datetime.now(timezone.utc)

    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="disable",
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
                    INSERT INTO market."MARKET_PRICES"
                        ("STOCK_ID", "PRICE", "TIME_STAMP", "DATE", "OPEN", "HIGH", "LOW", "CHANGE", "CHANGE_PCT", "VOLUME")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        stock_id,
                        p.get("price"),
                        now,
                        now.date(),
                        p.get("open"),
                        p.get("high"),
                        p.get("low"),
                        p.get("change"),
                        p.get("percentageChange"),
                        p.get("sharevolume"),
                    ),
                )
                count += 1

            conn.commit()
    finally:
        conn.close()

    return {"statusCode": 200, "body": f"Saved {count} price snapshots"}
