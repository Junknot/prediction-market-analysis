
import sys

import duckdb
import pandas as pd
import datetime as dt 
import json

from src.indexers.kalshi.client import KalshiClient 


pd.set_option("display.max_colwidth", None)
pd.set_option('display.max_rows', 1000)


def jsonFrmt(_json):
    return json.dumps(_json, indent=4)

con = duckdb.connect()

# df_raw = con.execute(
#     f"""
#     SELECT event_category,
#             COUNT(*) AS n_markets
#     FROM 'data/kalshi/markets/markets_*.parquet' m
#     WHERE 1=1
#     AND status = 'finalized'
#     AND result IN ('yes', 'no')
#     GROUP BY event_category
#     """
# ).df()


# print(df_raw)

# sys.exit(0)

kClient = KalshiClient()

# newMarkets = [market for markets, cursor in kClient.iter_event_nested_markets(max_close_ts=1784510100) for market in markets ] #if market["close_time"] > "2026-07-19 21:15:00-04:00"]


# print(df_raw)

# # result = duckdb.sql(f"SELECT DISTINCT ticker FROM 'data/kalshi/markets/markets_*.parquet'").fetchall()

# # print(f"Found {len(result)} distinct tickers in markets parquet files")

# sys.exit(0)


print(f"Now:{dt.datetime.now()}")


df_markets_min_max = con.execute(
    f"""
        WITH resolved_markets as(
                SELECT close_time as date
                FROM 'data/kalshi/historical/markets/markets_*.parquet' m
                WHERE 1=1
                AND status = 'finalized'
                AND volume >= 100
                --GROUP BY DATE(close_time)
                --HAVING count(*) >= 100
                ORDER BY date ASC
            )
            SELECT MIN(date) as min,
                    MAX(date) as max
            FROM resolved_markets
    """
).df()

print(df_markets_min_max)

markets_min = df_markets_min_max["min"][0]
markets_max = df_markets_min_max["max"][0]

print(markets_min.timestamp())
print(markets_max.timestamp())
print(markets_max)


newMarkets = []

for markets, cursor in kClient.iter_event_nested_markets(min_close_ts=int(markets_max.timestamp())):
    for market in markets:
        if (market.close_time > markets_max
            and market.status == 'finalized'): newMarkets.append(market)

print(len(newMarkets))

df_tradeless_markets = con.execute(
    f"""
        WITH tradeless_markets AS (
            SELECT 
                DISTINCT m.ticker
                --m.ticker
            FROM 'data/kalshi/markets/markets_*.parquet' m
            LEFT JOIN 'data/kalshi/trades/trades_*.parquet' t ON t.ticker = m.ticker
            WHERE 1=1 
            AND m.volume > 100
        AND m.status = 'finalized'
        AND m.result IN ('yes', 'no')
        AND t.ticker IS NULL
    )
    SELECT * 
    FROM tradeless_markets
    """
).df()

print(df_tradeless_markets)
print(len(df_tradeless_markets))

# df_trades = con.execute(
#     f"""
#         WITH tradeless_markets AS (
#             SELECT 
#                 m.ticker
#             FROM 'data/kalshi/markets/markets_*.parquet' m
#             LEFT JOIN 'data/kalshi/trades/trades_*.parquet' t ON t.ticker = m.ticker
#             WHERE 1=1 
#             AND m.volume > 100
#         AND m.status = 'finalized'
#         AND m.result IN ('yes', 'no')
#         AND t.ticker IS NULL
#     )
#     SELECT * 
#     FROM 'data/kalshi/trades/trades_*.parquet' t
#     INNER JOIN tradeless_markets tm ON t.ticker = tm.ticker 
#     """
# ).df()

# print(df_trades)


sys.exit(0)

df = con.execute(
    f"""
    WITH resolved_markets AS (
        SELECT ticker, result
        FROM 'data/kalshi/markets/markets_*.parquet'
        WHERE status = 'finalized'
        AND result IN ('yes', 'no')
        AND event_category = 'Mentions'
        AND close_time >= '2026-04-24'
        AND close_time < '2026-04-25'
    ),
    maker_yes_positions AS (
        -- Maker bought YES (taker sold YES = taker bought NO)
        SELECT
            t.yes_price AS price,
            CASE WHEN m.result = 'yes' THEN 1.0 ELSE 0.0 END AS won,
            t.count AS contracts,
            'YES' AS maker_side
        FROM 'data/kalshi/trades/trades_*.parquet' t
        INNER JOIN resolved_markets m ON t.ticker = m.ticker
        WHERE t.taker_side = 'no'
    ),
    maker_no_positions AS (
        -- Maker bought NO (taker sold NO = taker bought YES)
        SELECT
            t.no_price AS price,
            CASE WHEN m.result = 'no' THEN 1.0 ELSE 0.0 END AS won,
            t.count AS contracts,
            'NO' AS maker_side
        FROM 'data/kalshi/trades/trades_*.parquet' t
        INNER JOIN resolved_markets m ON t.ticker = m.ticker
        WHERE t.taker_side = 'yes'
    ),
    all_maker_positions AS (
        SELECT * FROM maker_yes_positions
        UNION ALL
        SELECT * FROM maker_no_positions
    )
    SELECT
        maker_side,
        price,
        AVG(won) AS win_rate,
        price / 100.0 AS expected_win_rate,
        AVG(won) - price / 100.0 AS excess_return,
        VAR_POP(won - price / 100.0) AS var_excess,
        COUNT(*) AS n_trades,
        SUM(contracts) AS contracts,
        SUM(contracts * price / 100.0) AS volume_usd
    FROM all_maker_positions
    WHERE price BETWEEN 1 AND 99
    GROUP BY maker_side, price
    ORDER BY maker_side, price
    """
).df()


df_no = df[df["maker_side"] == "NO"].copy()

print(df_no)

sys.exit(0)

df_trades = con.execute(
    f"""
    SELECT MIN(created_time) as min,
            MAX(created_time) as max 
    FROM 'data/kalshi/trades/trades_*.parquet' m
    WHERE 1=1
    """
).df()

trades_min = df_trades["min"][0]
trades_max = df_trades["max"][0]

print(trades_min)
print(trades_max)

trades_delta = trades_max - trades_min

trades_weeks = trades_delta.days / 7


print(f"days: {trades_delta.days}")
print(f"weeks: {trades_weeks}")

trades_weekly_range = pd.date_range(start=trades_min, end=trades_max, freq="W")

trades_daily_range = pd.date_range(start=trades_min, end=trades_max, freq="D")

print(trades_daily_range)


#### Markets


df_markets = con.execute(
    f"""
    WITH resolved_markets as(
        SELECT DATE(close_time) as date, count(*) as n_markets
        FROM 'data/kalshi/markets/markets_*.parquet' m
        WHERE 1=1
        AND status = 'finalized'
        AND volume >= 100
        GROUP BY DATE(close_time)
        HAVING count(*) >= 100
        ORDER BY date ASC
    )
    SELECT MIN(date) as min,
            MAX(date) as max
    FROM resolved_markets
    """
).df()

print(df_markets)

sys.exit(0)

markets_min = df_markets["min"][0]
markets_max = df_markets["max"][0]

print(markets_min)
print(markets_max)

markets_delta = markets_max - markets_min

markets_weeks = markets_delta.days / 7


print(f"days: {markets_delta.days}")
print(f"weeks: {markets_weeks}")

markets_weekly_range = pd.date_range(start=markets_min, end=markets_max, freq="W")

markets_daily_range = pd.date_range(start=markets_min, end=markets_max, freq="D")

print(markets_daily_range)



# df_raw.to_csv("kalshi_companies_markets.csv", index=False)
