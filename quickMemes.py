
import duckdb
import pandas as pd

pd.set_option("display.max_colwidth", None)

con = duckdb.connect()

df_raw = con.execute(
    f"""
    SELECT event_category,
            COUNT(*) AS n_markets
    FROM 'data/kalshi/markets/markets_*.parquet' m
    WHERE 1=1
    GROUP BY event_category
    """
).df()


# df_raw = con.execute(
#     f"""
#     SELECT close_time,
#               event_category,
#               title,
#               status,
#               result
#     FROM 'data/kalshi/markets/markets_*.parquet' m
#     WHERE 1=1
#     LIMIT 5
#     """
# ).df()


print(df_raw)

# df_raw.to_csv("kalshi_companies_markets.csv", index=False)
