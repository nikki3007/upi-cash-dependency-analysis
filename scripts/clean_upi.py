from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

UPI_FILE = ROOT / "data" / "cleaned" / "upi_cleaned.csv"
RBI_FILE = ROOT / "data" / "cleaned" / "rbi_cleaned.csv"
OUTPUT_FILE = ROOT / "data" / "cleaned" / "tableB_upi_vs_atm.csv"

upi = pd.read_csv(UPI_FILE)
rbi = pd.read_csv(RBI_FILE)
upi.columns = upi.columns.str.strip()
rbi.columns = rbi.columns.str.strip()

upi["Month_Year"] = pd.to_datetime(upi["Month"]).dt.strftime("%Y-%m")
rbi["Month_Year"] = rbi["Month"].astype(str).str.strip()

rbi = rbi[rbi["Bank_Type"].isin(["Public", "Private"])].copy()

# Keep only banks present in every RBI month (consistent bank set).
n_months = rbi["Month_Year"].nunique()
months_per_bank = rbi.groupby("Bank_Name")["Month_Year"].nunique()
partial = months_per_bank[months_per_bank < n_months]
if len(partial):
    print("Banks excluded from sector totals (not in all", n_months, "months):")
    print(partial.to_string())
rbi = rbi[rbi["Bank_Name"].isin(months_per_bank[months_per_bank == n_months].index)]

atm = (
    rbi.groupby(["Month_Year", "Bank_Type"])["ATM_Withdrawal_Volume"]
    .sum()
    .div(1_000_000)
    .unstack("Bank_Type")
    .rename(columns={
        "Public": "Total_Public_ATM_Vol",
        "Private": "Total_Private_ATM_Vol",
    })
    .reset_index()
)
for col in ["Total_Public_ATM_Vol", "Total_Private_ATM_Vol"]:
    if col not in atm.columns:
        atm[col] = pd.NA

upi = upi[["Month_Year", "Volume (In Mn.)"]].rename(
    columns={"Volume (In Mn.)": "National_UPI_Volume"}
)

# Outer merge so a month missing on either side shows up instead of vanishing.
tableB = pd.merge(upi, atm, on="Month_Year", how="outer").sort_values("Month_Year")
tableB = tableB[
    ["Month_Year", "National_UPI_Volume", "Total_Public_ATM_Vol", "Total_Private_ATM_Vol"]
].reset_index(drop=True)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
tableB.to_csv(OUTPUT_FILE, index=False)

print("Table B saved to:", OUTPUT_FILE)
print("Rows:", len(tableB), "| months:", tableB["Month_Year"].min(), "to", tableB["Month_Year"].max())
incomplete = tableB[tableB.isna().any(axis=1)]
if len(incomplete):
    print("\nMONTHS WITH A MISSING SIDE (fix the source data before analysis):")
    print(incomplete.to_string(index=False))
else:
    print("No missing values.")
print()
print(tableB.round(2).to_string(index=False))