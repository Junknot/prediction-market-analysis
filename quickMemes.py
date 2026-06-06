
import duckdb
import pandas as pd

pd.set_option("display.max_colwidth", None)

con = duckdb.connect()

df_raw = con.execute(
    f"""
    SELECT
        COUNT(DISTINCT ticker) AS ticker_count
    FROM 'data/kalshi/markets/*.parquet'
    WHERE volume >= 100
    """
).df()


print(df_raw)

