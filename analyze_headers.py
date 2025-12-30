
import pandas as pd

file_path = r"c:\Users\HP\Downloads\EDOTS PMLA data\edots excel sheet PMLA.xlsx"

def finding_header(df):
    for i, row in df.iterrows():
        # Convert row to string and search for key columns roughly
        row_str = " ".join([str(x) for x in row.values if pd.notna(x)]).lower()
        if "ecir" in row_str or "sl. no." in row_str or "name of" in row_str:
            return i
    return 0

try:
    xl = pd.ExcelFile(file_path)
    print(f"Total Sheets: {len(xl.sheet_names)}")
    
    for name in xl.sheet_names:
        # Read first 10 rows to look for header
        df_preview = pd.read_excel(file_path, sheet_name=name, nrows=10, header=None)
        header_row = finding_header(df_preview)
        
        # Read again with correct header
        df = pd.read_excel(file_path, sheet_name=name, header=header_row, nrows=1)
        print(f"Sheet: '{name}' | Header Row: {header_row} | Columns: {df.columns.tolist()[:5]}...")

except Exception as e:
    print(e)
