
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent


def inspect_excel(file_path):
    print("\n" + "=" * 70)
    print("FILE:", file_path.name)
    print("=" * 70)

    try:
        excel = pd.ExcelFile(file_path)
        print("Sheets:", excel.sheet_names)

        for sheet in excel.sheet_names[:2]:
            df = pd.read_excel(
                file_path,
                sheet_name=sheet,
                header=None,
                nrows=12
            )

            print(f"\nSheet: {sheet}")
            print(df.to_string(index=False, header=False))

    except Exception as e:
        print("ERROR:", e)


# Inspect one newer RBI workbook
rbi_files = sorted((BASE_DIR / "raw_rbi").rglob("*.XLSX"))

if rbi_files:
    inspect_excel(rbi_files[-1])
else:
    print("No .XLSX RBI files found.")

# Inspect one older RBI workbook
old_rbi_files = sorted((BASE_DIR / "raw_rbi").rglob("*.XLS"))

if old_rbi_files:
    inspect_excel(old_rbi_files[0])
else:
    print("No .XLS RBI files found.")

# Inspect one UPI workbook
upi_files = sorted((BASE_DIR / "raw_upi_monthly").glob("*.xlsx"))

if upi_files:
    inspect_excel(upi_files[0])
else:
    print("No UPI .xlsx files found.")
