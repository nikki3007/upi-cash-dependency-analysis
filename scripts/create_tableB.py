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

upi["Month_Year"] = pd.to_datetime(upi["Month"], errors="coerce").dt.strftime("%Y-%m")
# Accepts "2019-01", "2019-01-01", "Jan-2019" ... all become "2019-01".
rbi["Month_Year"] = pd.to_datetime(
    rbi["Month"].astype(str).str.strip(), errors="coerce"
).dt.strftime("%Y-%m")
rbi["Bank_Type"] = rbi["Bank_Type"].astype(str).str.strip().str.title()

print("Input check")
print("  UPI rows:", len(upi), "| unreadable months:", int(upi["Month_Year"].isna().sum()))
print("  RBI rows:", len(rbi), "| unreadable months:", int(rbi["Month_Year"].isna().sum()),
      "| months:", rbi["Month_Year"].nunique(), "| Bank_Type counts:", rbi["Bank_Type"].value_counts().to_dict())
print()

rbi = rbi[rbi["Bank_Type"].isin(["Public", "Private"]) & rbi["Month_Year"].notna()].copy()
if rbi.empty:
    raise RuntimeError(
        "No usable RBI rows: check that rbi_cleaned.csv has Month, Bank_Type "
        "('Public'/'Private') and ATM_Withdrawal_Volume columns. Re-run clean_rbi.py first."
    )

# Keep only banks present in every RBI month (consistent bank set).
n_months = rbi["Month_Year"].nunique()
months_per_bank = rbi.groupby("Bank_Name")["Month_Year"].nunique()
partial = months_per_bank[months_per_bank < n_months]
if len(partial):
    print("Banks excluded from sector totals (not in all", n_months, "months):")
    print(partial.to_string())
complete = months_per_bank[months_per_bank == n_months].index
if len(complete) == 0:
    print("WARNING: no bank appears in every month; using all banks instead.")
else:
    rbi = rbi[rbi["Bank_Name"].isin(complete)]

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

# Table B is built on exactly these 24 months (Jan-Dec 2019, Jan-Dec 2023).
# Any other month in the inputs (2020-2022, etc.) is ignored.
YEARS = (2019, 2023)
spine = pd.DataFrame({
    "Month_Year": [f"{y}-{m:02d}" for y in YEARS for m in range(1, 13)]
})
ignored = sorted((set(upi["Month_Year"].dropna()) | set(atm["Month_Year"].dropna())) - set(spine["Month_Year"]))
if ignored:
    print(f"Ignored {len(ignored)} month(s) outside 2019/2023:", ignored[0], "...", ignored[-1])

# Left-merge onto the 24-month spine, so a month with missing data stays visible
# but no month outside the target list can appear.
tableB = (
    spine.merge(upi, on="Month_Year", how="left")
         .merge(atm, on="Month_Year", how="left")
)
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