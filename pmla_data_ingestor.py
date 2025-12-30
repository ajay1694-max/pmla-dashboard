
import pandas as pd
import json
from datetime import datetime
import re

FILE_PATH = r"c:\Users\HP\Downloads\EDOTS PMLA data\edots excel sheet PMLA.xlsx"

class MasterCase:
    def __init__(self, ecir_no):
        self.ecir_no = ecir_no
        self.ecir_date = None
        self.status = "Unknown"
        self.zonal_office = None
        self.persons_involved = set()
        self.searches = []
        self.arrests = []
        self.paos = []
        self.pcs = []
        self.raw_data = {} # Store raw rows for debugging

    def to_dict(self):
        return {
            "ecir_no": self.ecir_no,
            "ecir_date": self.ecir_date.isoformat() if self.ecir_date else None,
            "status": self.status,
            "zonal_office": self.zonal_office,
            "persons_involved": list(self.persons_involved),
            "searches": self.searches,
            "arrests": self.arrests,
            "paos": self.paos,
            "pcs": self.pcs
        }

    def __repr__(self):
        return f"<ECIR: {self.ecir_no} | Status: {self.status} | Persons: {len(self.persons_involved)}>"

def normalize_ecir(val):
    if pd.isna(val):
        return None
    val = str(val).strip()
    return val

def find_header_row(df):
    """
    Scans the first 15 rows to find a header containing 'ECIR No' or 'Sl. No.'.
    Returns the index of the header row.
    """
    prioritized_idx = -1
    for i, row in df.iterrows():
        # Convert row to string and search for key columns roughly
        row_str = " ".join([str(x) for x in row.values if pd.notna(x)]).lower()
        
        # Strict match for ECIR Number column or Case No
        if "ecir no" in row_str or "ecir_no" in row_str or "case no" in row_str:
            return i
            
        # Fallback for sheets using Sl. No. but having ECIR data
        if "sl. no" in row_str and ("date" in row_str or "name" in row_str):
             prioritized_idx = i
             
    if prioritized_idx != -1:
        return prioritized_idx
    return 0

def clean_column_name(col):
    return str(col).strip().replace("\n", " ").replace("  ", " ")

def ingest_data():
    xl = pd.ExcelFile(FILE_PATH)
    cases = {} # Map ECIR No -> MasterCase object
    
    # 1. First Pass: Identify the "Master" sheet (usually 'list of pmla cases') to initialize cases
    print("--- Phase 1: Initializing Cases ---")
    master_sheet = 'list of pmla cases' 
    
    if master_sheet in xl.sheet_names:
        df_preview = pd.read_excel(FILE_PATH, sheet_name=master_sheet, nrows=15, header=None)
        header_idx = find_header_row(df_preview)
        df = pd.read_excel(FILE_PATH, sheet_name=master_sheet, header=header_idx)
        df.columns = [clean_column_name(c) for c in df.columns]
        
        # Identify key columns (Case Insensitive Search)
        ecir_col = next((c for c in df.columns if ("ECIR" in c or "Case" in c) and "No" in c), None)
        date_col = next((c for c in df.columns if "Date" in c and ("ECIR" in c or "Case" in c)), None)
        
        if ecir_col:
            print(f"Processing Master Sheet '{master_sheet}' with Key col: '{ecir_col}'")
            for _, row in df.iterrows():
                ecir = normalize_ecir(row[ecir_col])
                if ecir:
                    if ecir not in cases:
                        cases[ecir] = MasterCase(ecir)
                    
                    # Populate Basic Info
                    if date_col and pd.notna(row[date_col]):
                        cases[ecir].ecir_date = row[date_col]
        else:
            print(f"CRITICAL: Could not find ECIR column in {master_sheet}")

    # 2. Second Pass: Process ALL sheets to enrich data
    print("\n--- Phase 2: Enriching Cases from All Sheets ---")
    for sheet_name in xl.sheet_names:
        if sheet_name == master_sheet: continue # Already processed raw init, but can process for extra cols
        
        print(f"Processing '{sheet_name}'...")
        try:
            # Detect Header
            df_preview = pd.read_excel(FILE_PATH, sheet_name=sheet_name, nrows=15, header=None)
            header_idx = find_header_row(df_preview)
            df = pd.read_excel(FILE_PATH, sheet_name=sheet_name, header=header_idx)
            df.columns = [clean_column_name(c) for c in df.columns]
            
            # Find ECIR Column
            ecir_col = next((c for c in df.columns if ("ECIR" in c or "Case" in c) and "No" in c), None)
            if not ecir_col:
                 # Fallback: Check for 'File No' or just 'No' if it helps, but 'Case No' covers T1
                 print(f"  > Skipping {sheet_name}: No ECIR/Case No column found. Columns: {df.columns.tolist()[:3]}...")
                 continue
            
            # Determine Sheet Type based on Name
            sheet_lower = sheet_name.lower()
            category = "other"
            if "search" in sheet_lower: category = "search"
            elif "arrest" in sheet_lower: category = "arrest"
            elif "pao" in sheet_lower or "attach" in sheet_lower: category = "pao"
            elif "pc" in sheet_lower or "complaint" in sheet_lower: category = "pc"
            
            # Iterate Rows
            for _, row in df.iterrows():
                ecir = normalize_ecir(row[ecir_col])
                if not ecir: continue
                
                # Create if missing (some cases might originate in secondary sheets?)
                if ecir not in cases:
                    cases[ecir] = MasterCase(ecir)
                
                case = cases[ecir]
                
                # Extract interesting data based on category
                # This is heuristic; we grab all non-empty columns as "details"
                data_row = {k: v for k, v in row.items() if pd.notna(v) and k != ecir_col}
                
                if category == "search":
                    # Look for date/location
                    date_key = next((k for k in data_row if "date" in k.lower()), "Unknown Date")
                    loc_key = next((k for k in data_row if "address" in k.lower() or "place" in k.lower()), "Unknown Loc")
                    case.searches.append({
                        "date": data_row.get(date_key),
                        "location": data_row.get(loc_key),
                        "sheet": sheet_name,
                        "raw": str(data_row)
                    })
                
                elif category == "arrest":
                   # Look for name/date
                    name_key = next((k for k in data_row if "name" in k.lower()), "Unknown Name")
                    date_key = next((k for k in data_row if "date" in k.lower()), None)
                    arrest_entry = {
                        "name": data_row.get(name_key),
                        "date": data_row.get(date_key),
                        "sheet": sheet_name
                    }
                    case.arrests.append(arrest_entry)
                    if name_key in data_row:
                        case.persons_involved.add(data_row[name_key])

                elif category == "pao":
                    case.paos.append({"data": str(data_row), "sheet": sheet_name})
                    
                elif category == "pc":
                    case.pcs.append({"data": str(data_row), "sheet": sheet_name})
                
                # Always add names if found
                for k, v in data_row.items():
                    if "name" in k.lower() and "officer" not in k.lower():
                         case.persons_involved.add(str(v))

        except Exception as e:
            print(f"  > Error processing {sheet_name}: {e}")

    return cases

if __name__ == "__main__":
    all_cases = ingest_data()
    print(f"\nTotal Master Cases Created: {len(all_cases)}")
    
    # Save a sample to verify
    sample_ecirs = list(all_cases.keys())[:5]
    print("Sample Cases:")
    for ecir in sample_ecirs:
        print(all_cases[ecir])
        
    # JSON Dump for persistence/UI
    output_path = r"c:\Users\HP\Downloads\EDOTS PMLA data\master_cases.json"
    with open(output_path, "w") as f:
        # custom converter for sets/dates
        def default_serializer(obj):
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            if isinstance(obj, set):
                return list(obj)
            return str(obj)
            
        json.dump({k: v.to_dict() for k, v in all_cases.items()}, f, default=default_serializer, indent=2)
    print(f"Saved master object to {output_path}")
