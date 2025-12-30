
import pandas as pd

FILE_PATH = r"c:\Users\HP\Downloads\EDOTS PMLA data\edots excel sheet PMLA.xlsx"

sheet_name = 'list of pmla cases'
header_row = 2

try:
    df = pd.read_excel(FILE_PATH, sheet_name=sheet_name, header=header_row)
    print(f"Columns: {df.columns.tolist()}")
    print("\nFirst 3 rows of data:")
    print(df.head(3).to_string())
except Exception as e:
    print(e)
