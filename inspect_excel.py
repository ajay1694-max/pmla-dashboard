
import pandas as pd

file_path = r"c:\Users\HP\Downloads\EDOTS PMLA data\edots excel sheet PMLA.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheet names ({len(xl.sheet_names)}):")
    for name in xl.sheet_names:
        print(f"- {name}")
    
    # Inspect first few sheets for structure
    for name in xl.sheet_names[:3]:
        print(f"\n--- Sheet: {name} ---")
        df = pd.read_excel(file_path, sheet_name=name, nrows=5)
        print(df.columns.tolist())
        print(df.head(2))

except Exception as e:
    print(e)
