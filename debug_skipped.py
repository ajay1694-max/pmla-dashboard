
import pandas as pd

FILE_PATH = r"c:\Users\HP\Downloads\EDOTS PMLA data\edots excel sheet PMLA.xlsx"
sheet_name = 'list of T1 cases pmla'

try:
    # Read without header first to see structure
    df_raw = pd.read_excel(FILE_PATH, sheet_name=sheet_name, nrows=10, header=None)
    print(f"--- Raw Data from {sheet_name} ---")
    print(df_raw.to_string())
    
    # Try my heuristic
    from pmla_data_ingestor import find_header_row
    header_idx = find_header_row(df_raw)
    print(f"\nDetected Header Row: {header_idx}")
    
    if header_idx is not None:
        df = pd.read_excel(FILE_PATH, sheet_name=sheet_name, header=header_idx)
        print(f"Columns at {header_idx}: {df.columns.tolist()}")

except Exception as e:
    print(e)
