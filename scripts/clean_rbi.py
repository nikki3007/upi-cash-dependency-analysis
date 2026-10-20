from pathlib import Path
import re
import calendar

import pandas as pd

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw_rbi"
OUT_DIR = BASE_DIR / "data" / "cleaned"
OUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = (2019, 2023)

# Fallback column positions, used ONLY if header detection fails for a file.
FALLBACK = {
    2019: {"bank_col": 2, "volume_col": 13, "value_col": 15},
    2023: {"bank_col": 2, "volume_col": 25, "value_col": 26},
}

# Conversion of the unit printed in the header into Rs. million.
UNIT_TO_MILLION = {
    "MILLION": 1.0,
    "LAKH": 0.1,
    "THOUSAND": 0.001,
    "'000": 0.001,      # e.g. "Value (in Rs'000)"
    "CRORE": 10.0,
}

# ============================================================
# BANK NAMES
# All sets use the normalised key produced by bank_key().
# ============================================================


def bank_key(name):
    """Normalise a raw bank name into a comparison key."""
    if pd.isna(name):
        return None
    s = str(name).upper().strip()
    s = s.replace("&", " AND ")
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(r"\bLIMITED\b", "LTD", s)
    s = re.sub(r"^THE\s+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+LTD$", "", s)
    return s


# Banks that were merged into another bank. Rows are SUMMED into the
# surviving bank for every month so 2019 and 2023 compare like with like
# (pro-forma). Key = old bank, value = surviving bank.
MERGED_INTO = {
    "DENA BANK": "BANK OF BARODA",                 # 1 Apr 2019
    "VIJAYA BANK": "BANK OF BARODA",               # 1 Apr 2019
    "ALLAHABAD BANK": "INDIAN BANK",               # 1 Apr 2020
    "ANDHRA BANK": "UNION BANK OF INDIA",          # 1 Apr 2020
    "CORPORATION BANK": "UNION BANK OF INDIA",     # 1 Apr 2020
    "ORIENTAL BANK OF COMMERCE": "PUNJAB NATIONAL BANK",  # 1 Apr 2020
    "UNITED BANK OF INDIA": "PUNJAB NATIONAL BANK",       # 1 Apr 2020
    "SYNDICATE BANK": "CANARA BANK",               # 1 Apr 2020
}

# Renamed banks (same bank, new name).
RENAMED = {
    "IDBI": "IDBI BANK",
    "CATHOLIC SYRIAN BANK": "CSB BANK",
    "RATNAKAR BANK": "RBL BANK",
    "IDFC BANK": "IDFC FIRST BANK",
    "DHANLAXMI BANK": "DHANALAKSHMI BANK",
    "PUNJAB AND SIND BANK": "PUNJAB AND SIND BANK",
}

PUBLIC_BANKS = {
    "BANK OF BARODA", "BANK OF INDIA", "BANK OF MAHARASHTRA", "CANARA BANK",
    "CENTRAL BANK OF INDIA", "INDIAN BANK", "INDIAN OVERSEAS BANK",
    "PUNJAB AND SIND BANK", "PUNJAB NATIONAL BANK", "STATE BANK OF INDIA",
    "UCO BANK", "UNION BANK OF INDIA",
}

# NOTE: IDBI Bank is a judgement call. RBI re-classified it as a private
# bank in 2019 (LIC stake), but the RBI ATM sheet still lists it in the
# public-sector block. It is kept as Private here, as in the first version;
# change IDBI_TYPE to "Public" or None (exclude) if the team decides otherwise.
IDBI_TYPE = "Private"

PRIVATE_BANKS = {
    "AXIS BANK", "BANDHAN BANK", "CITY UNION BANK", "CSB BANK", "DCB BANK",
    "DHANALAKSHMI BANK", "FEDERAL BANK", "HDFC BANK", "ICICI BANK",
    "IDFC FIRST BANK", "INDUSIND BANK", "JAMMU AND KASHMIR BANK",
    "KARNATAKA BANK", "KARUR VYSYA BANK", "KOTAK MAHINDRA BANK",
    "NAINITAL BANK", "RBL BANK", "SOUTH INDIAN BANK",
    "TAMILNAD MERCANTILE BANK", "YES BANK",
}
if IDBI_TYPE == "Private":
    PRIVATE_BANKS.add("IDBI BANK")
elif IDBI_TYPE == "Public":
    PUBLIC_BANKS.add("IDBI BANK")


def canonical_bank(raw_name):
    """Raw sheet name -> surviving canonical bank key (or None)."""
    key = bank_key(raw_name)
    if key is None:
        return None
    key = RENAMED.get(key, key)
    key = MERGED_INTO.get(key, key)
    return key


def bank_type(canonical):
    if canonical in PUBLIC_BANKS:
        return "Public"
    if canonical in PRIVATE_BANKS:
        return "Private"
    return None


# ============================================================
# MONTH / YEAR
# ============================================================

MONTH_NAMES = {m.upper(): i for i, m in enumerate(calendar.month_name) if m}
MONTH_ABBR = {m.upper(): i for i, m in enumerate(calendar.month_abbr) if m}
MONTH_ABBR["SEPT"] = 9

TITLE_RE = re.compile(
    r"(" + "|".join(MONTH_NAMES) + r")\W*(\d{4})", re.IGNORECASE
)


def month_from_title(df):
    """Read 'ATM & Card Statistics for <Month> <Year>' from the sheet."""
    for i in range(min(6, len(df))):
        for cell in df.iloc[i].tolist():
            if isinstance(cell, str):
                m = TITLE_RE.search(cell)
                if m:
                    return MONTH_NAMES[m.group(1).upper()], int(m.group(2))
    return None, None


def month_from_filename(path):
    stem = path.stem.upper()
    for name, num in {**MONTH_NAMES, **MONTH_ABBR}.items():
        if re.search(rf"(?<![A-Z]){name}(?![A-Z])", stem):
            return num
    return None


# ============================================================
# LOCATE COLUMNS, UNIT AND DATA ROWS INSIDE ONE SHEET
# ============================================================


def find_numbered_row(df):
    """Row index of the '1 2 3 ... 14' header row, and {number: column}."""
    for i in range(min(15, len(df))):
        nums = {}
        for j in range(3, df.shape[1]):
            v = pd.to_numeric(df.iat[i, j], errors="coerce")
            if pd.notna(v) and float(v).is_integer():
                nums[int(v)] = j
        if len(nums) >= 10 and set(range(1, 11)).issubset(nums):
            return i, nums
    return None, {}


def find_footnotes(df, after_row):
    notes = {}
    for i in range(after_row + 1, len(df)):
        n = pd.to_numeric(df.iat[i, 1], errors="coerce")
        text = df.iat[i, 2] if df.shape[1] > 2 else None
        if pd.notna(n) and isinstance(text, str) and len(text) > 25:
            notes[int(n)] = text
    return notes


def find_by_header_path(df, max_rows=8):
    """
    Newer sheets (2023): the columns sit under a nested header
    Debit Card > Cash Withdrawal > ATM > Volume / Value.
    Merged header cells only carry their label in the first column, so each
    header row is forward-filled across columns before matching.
    """
    n = min(max_rows, len(df))
    filled = []
    for i in range(n):
        last, row = None, []
        for j in range(df.shape[1]):
            v = df.iat[i, j]
            if isinstance(v, str) and v.strip():
                last = v.strip().upper()
            row.append(last)
        filled.append(row)

    vol = val = None
    for j in range(3, df.shape[1]):
        col = [filled[i][j] for i in range(n) if filled[i][j]]
        if (
            any("DEBIT CARD" in c for c in col)
            and any("CASH WITHDRAWAL" in c for c in col)
            and any(c == "ATM" for c in col)
        ):
            if any(c.startswith("VOLUME") for c in col):
                vol = j
            if any(c.startswith("VALUE") for c in col):
                val = j
    return (vol, val) if vol is not None and val is not None else None


def detect_layout(df, year):
    """Return dict(bank_col, volume_col, value_col, hdr_row, method)."""
    fb = FALLBACK[year]
    hdr_row, number_to_col = find_numbered_row(df)
    method = "header"
    volume_col = value_col = None

    if hdr_row is not None:
        notes = find_footnotes(df, hdr_row)
        vol_n = val_n = None
        for n, text in notes.items():
            t = text.lower()
            if "debit card" in t and "at atms" in t:
                if "number of financial transactions" in t:
                    vol_n = n
                elif "value of financial transactions" in t:
                    val_n = n
        if vol_n in number_to_col and val_n in number_to_col:
            volume_col = number_to_col[vol_n]
            value_col = number_to_col[val_n]

    if volume_col is None or value_col is None:
        pair = find_by_header_path(df)
        if pair:
            volume_col, value_col = pair
            method = "header-path"

    if volume_col is None or value_col is None:
        method = "FALLBACK-INDEX"
        volume_col, value_col = fb["volume_col"], fb["value_col"]
        if hdr_row is None:
            hdr_row = 6

    bank_col = fb["bank_col"]
    for i in range(min(10, len(df))):
        for j in range(df.shape[1]):
            cell = df.iat[i, j]
            if isinstance(cell, str) and cell.strip().upper() == "BANK NAME":
                bank_col = j
    return {
        "bank_col": bank_col,
        "volume_col": volume_col,
        "value_col": value_col,
        "hdr_row": hdr_row,
        "method": method,
    }


def detect_unit(df, value_col):
    """Read the unit of the debit-card ATM amount column from the header."""
    best = None
    for i in range(min(10, len(df))):
        for j in range(min(value_col + 1, df.shape[1])):
            cell = df.iat[i, j]
            if isinstance(cell, str):
                low = re.sub(r"\s+", " ", cell.lower())   # FEB-2023 has padded spaces
                if "amount of transactions" in low or low.strip().startswith("value (in"):
                    if best is None or j >= best[0]:
                        best = (j, cell)
    if best is None:
        return None, None
    label = best[1].upper().replace("’", "'")
    for word, factor in UNIT_TO_MILLION.items():
        if word in label:
            return factor, best[1].replace("\n", " ").strip()
    return None, best[1]


# ============================================================
# READ MONTHLY FILES
# ============================================================

records = []
skipped = []
file_log = []
unmatched = {}      # (year, raw name) -> total volume
recon = []          # reconciliation against each file's Total row

for year in YEARS:
    year_dir = RAW_DIR / str(year)
    if not year_dir.exists():
        print(f"WARNING: folder not found: {year_dir}")
        continue

    files = sorted(
        f for f in year_dir.iterdir()
        if f.is_file() and f.suffix.lower() in (".xls", ".xlsx")
        and not f.name.startswith("~$")
    )

    for path in files:
        try:
            df = pd.read_excel(path, header=None)
        except Exception as err:
            skipped.append((path.name, f"cannot read: {err}"))
            continue

        t_month, t_year = month_from_title(df)
        f_month = month_from_filename(path)
        month = t_month or f_month
        if month is None:
            skipped.append((path.name, "could not identify month"))
            continue
        if t_month and f_month and t_month != f_month:
            print(f"WARNING {path.name}: title says month {t_month}, filename says {f_month}; using title")
        if t_year and t_year != year:
            skipped.append((path.name, f"title year {t_year} != folder year {year}"))
            continue

        lay = detect_layout(df, year)
        factor, unit_label = detect_unit(df, lay["value_col"])
        if factor is None:
            skipped.append((path.name, f"unrecognised value unit: {unit_label!r}"))
            continue

        need = max(lay["bank_col"], lay["volume_col"], lay["value_col"])
        if df.shape[1] <= need:
            skipped.append((path.name, f"only {df.shape[1]} columns, need index {need}"))
            continue

        file_log.append((year, month, path.name, lay["method"], lay["volume_col"],
                         lay["value_col"], unit_label))

        body = df.iloc[lay["hdr_row"] + 1:]
        file_total_vol = None
        bank_vol_sum = 0.0

        section = None   # sheet's own "Public Sector Banks" / "Private ..." header

        for _, row in body.iterrows():
            raw = row.iloc[lay["bank_col"]]
            left = row.iloc[lay["bank_col"] - 1]

            # "Total" sits in the bank column (2019) or the Sr. No. column (2023)
            if any(isinstance(c, str) and c.strip().upper() == "TOTAL" for c in (raw, left)):
                file_total_vol = pd.to_numeric(row.iloc[lay["volume_col"]], errors="coerce")
                break

            if pd.isna(raw):
                if isinstance(left, str) and "BANKS" in left.upper():
                    section = left.strip().upper()
                continue
            raw = str(raw).strip()
            sr = pd.to_numeric(left, errors="coerce")
            if pd.isna(sr):
                continue

            vol = pd.to_numeric(row.iloc[lay["volume_col"]], errors="coerce")
            val_raw = pd.to_numeric(
                str(row.iloc[lay["value_col"]]).replace(",", ""), errors="coerce"
            )
            val = val_raw * factor if pd.notna(val_raw) else float("nan")
            bank_vol_sum += 0 if pd.isna(vol) else vol

            canon = canonical_bank(raw)
            btype = bank_type(canon)
            if btype is None:
                unmatched[(year, raw)] = unmatched.get((year, raw), 0) + (0 if pd.isna(vol) else vol)
                continue

            records.append({
                "Year": year,
                "Month": f"{year}-{month:02d}",
                "Bank_Name": canon,
                "Bank_Type": btype,
                "Source_Name": raw,
                "Sheet_Type": (
                    "Public" if section and section.startswith("PUBLIC")
                    else "Private" if section and section.startswith("PRIVATE")
                    else None
                ),
                "ATM_Withdrawal_Volume": vol,
                "ATM_Withdrawal_Value_Million_Rs": val,
                "Source_File": path.name,
            })

        recon.append((path.name, bank_vol_sum, file_total_vol))

if not records:
    raise RuntimeError("No records extracted. Check raw_rbi/<year>/ folders.")

raw_rows = pd.DataFrame(records)

# ============================================================
# SUM COMPONENT BANKS INTO THE SURVIVING BANK (per month)
# ============================================================

monthly = (
    raw_rows.groupby(["Year", "Month", "Bank_Name", "Bank_Type"], as_index=False)
    .agg(
        ATM_Withdrawal_Volume=("ATM_Withdrawal_Volume", lambda s: s.sum(min_count=1)),
        ATM_Withdrawal_Value_Million_Rs=("ATM_Withdrawal_Value_Million_Rs", lambda s: s.sum(min_count=1)),
        Source_Rows=("Source_Name", "nunique"),
        Sheet_Type=("Sheet_Type", "first"),
        Source_File=("Source_File", "first"),
    )
    .sort_values(["Month", "Bank_Name"])
    .reset_index(drop=True)
)

monthly_path = OUT_DIR / "rbi_cleaned.csv"
monthly[
    ["Month", "Bank_Name", "Bank_Type", "ATM_Withdrawal_Volume",
     "ATM_Withdrawal_Value_Million_Rs", "Source_Rows", "Source_File"]
].to_csv(monthly_path, index=False)

# ============================================================
# TABLE A  (needs both years)
# ============================================================

table_a_path = OUT_DIR / "tableA_bankwise_2019_vs_2023.csv"
table_a = None

if set(monthly["Year"].unique()) >= set(YEARS):
    agg = (
        monthly.groupby(["Bank_Name", "Bank_Type", "Year"])
        .agg(
            Avg_Vol=("ATM_Withdrawal_Volume", "mean"),
            Avg_Val=("ATM_Withdrawal_Value_Million_Rs", "mean"),
            Months=("Month", "nunique"),
        )
        .unstack("Year")
    )
    table_a = pd.DataFrame(index=agg.index)
    for y in YEARS:
        table_a[f"Avg_Vol_{y}"] = agg[("Avg_Vol", y)]
    table_a["Vol_Pct_Change"] = (
        (table_a["Avg_Vol_2023"] - table_a["Avg_Vol_2019"])
        / table_a["Avg_Vol_2019"].where(table_a["Avg_Vol_2019"] > 0) * 100
    )
    for y in YEARS:
        table_a[f"Avg_Val_{y}"] = agg[("Avg_Val", y)]
    table_a["Val_Pct_Change"] = (
        (table_a["Avg_Val_2023"] - table_a["Avg_Val_2019"])
        / table_a["Avg_Val_2019"].where(table_a["Avg_Val_2019"] > 0) * 100
    )
    for y in YEARS:
        table_a[f"Months_{y}"] = agg[("Months", y)]
    table_a = table_a.reset_index()

    incomplete = table_a[
        table_a[["Avg_Vol_2019", "Avg_Vol_2023"]].isna().any(axis=1)
        | (table_a["Months_2019"] != 12) | (table_a["Months_2023"] != 12)
    ]
    table_a.to_csv(table_a_path, index=False)

# ============================================================
# VALIDATION REPORT
# ============================================================

print("\n" + "=" * 70)
print("RBI CLEANING REPORT")
print("=" * 70)

print("\nFiles read (layout method / columns / unit read from header):")
for y, m, name, method, vc, ac, unit in sorted(file_log):
    flag = "   <-- CHECK: fixed column index used" if method == "FALLBACK-INDEX" else ""
    unit = re.sub(r"\s+", " ", unit)
    print(f"  {y}-{m:02d} {name:18s} {method:15s} vol_col={vc:<3d} val_col={ac:<3d} unit={unit}{flag}")

if skipped:
    print("\nSKIPPED FILES:")
    for n, why in skipped:
        print(f"  {n}: {why}")

print("\nMonths per year:", monthly.groupby("Year")["Month"].nunique().to_dict())
for y in YEARS:
    have = set(monthly.loc[monthly.Year == y, "Month"])
    want = {f"{y}-{m:02d}" for m in range(1, 13)}
    if have and have != want:
        print(f"  MISSING MONTHS {y}:", sorted(want - have))

print("\nBanks kept:", monthly["Bank_Name"].nunique(),
      "| by type:", monthly.groupby("Bank_Type")["Bank_Name"].nunique().to_dict())

print("\nReconciliation: sum of all bank rows vs the file's own Total row (volume)")
bad = [(n, s, t) for n, s, t in recon if pd.isna(t) or abs(s - t) > 1e-4 * abs(t)]
print("  all files reconcile" if not bad else "  MISMATCH:", *bad)

clash = monthly[monthly["Sheet_Type"].notna() & (monthly["Sheet_Type"] != monthly["Bank_Type"])]
print("\nBank_Type vs the sheet's own sector heading (where the sheet has one):")
print("  all agree" if clash.empty else
      clash.groupby(["Bank_Name", "Bank_Type", "Sheet_Type"]).size().to_string())

src_rows = monthly.groupby(["Bank_Name", "Year"])["Source_Rows"].agg(["min", "max"])
multi = src_rows[src_rows["max"] > 1]
if not multi.empty:
    print("\nBanks built by summing several source rows (min/max rows per month):")
    print(multi.to_string())
    varying = src_rows[src_rows["min"] != src_rows["max"]]
    if not varying.empty:
        print("  (rows per month change inside the year, e.g. Dena/Vijaya vanish after Apr 2019;"
              " summing keeps the series pro-forma)")

monthly["Implied_Avg_Rs_Per_Txn"] = (
    monthly["ATM_Withdrawal_Value_Million_Rs"] * 1e6 / monthly["ATM_Withdrawal_Volume"]
)
odd = monthly[(monthly["Implied_Avg_Rs_Per_Txn"] < 500) | (monthly["Implied_Avg_Rs_Per_Txn"] > 20000)]
print("\nUnit sanity (implied average Rs per ATM transaction should be ~1,500-6,000):")
print(f"  range {monthly['Implied_Avg_Rs_Per_Txn'].min():.0f} - {monthly['Implied_Avg_Rs_Per_Txn'].max():.0f};"
      f" rows outside 500-20,000: {len(odd)}")
if len(odd):
    print(odd[["Month", "Bank_Name", "Implied_Avg_Rs_Per_Txn"]].head(15).to_string(index=False))

sector = (
    monthly.groupby(["Month", "Bank_Type"])[["ATM_Withdrawal_Volume", "ATM_Withdrawal_Value_Million_Rs"]]
    .sum().unstack("Bank_Type")
)
jump = sector["ATM_Withdrawal_Volume"].pct_change().abs()
big = jump[(jump > 0.15).any(axis=1)] if not jump.empty else jump
if len(big):
    print("\nSector volume moves of more than 15 % month-on-month (check against RBI source):")
    print((sector["ATM_Withdrawal_Volume"].pct_change().loc[big.index] * 100).round(1).to_string())

um = (
    pd.Series(unmatched).rename("Total_Volume").sort_values(ascending=False)
    .rename_axis(["Year", "Bank_Name_In_File"]).reset_index()
)
um.to_csv(OUT_DIR / "rbi_unmatched_banks.csv", index=False)
print("\nTop unmatched names (excluded: foreign, payments, small-finance banks are expected here;"
      "\nany Indian commercial bank in this list is a name mismatch to fix):")
print(um.head(20).to_string(index=False))

if table_a is not None:
    print("\nTable A rows:", len(table_a), "| by type:", table_a["Bank_Type"].value_counts().to_dict())
    if len(incomplete):
        print("Banks missing a year or with < 12 months (review before the t-tests):")
        print(incomplete[["Bank_Name", "Bank_Type", "Months_2019", "Months_2023"]].to_string(index=False))
    print("Saved Table A:", table_a_path)
else:
    print("\nTable A not built: need both 2019 and 2023 data in raw_rbi/.")

print("Saved monthly data:", monthly_path)
