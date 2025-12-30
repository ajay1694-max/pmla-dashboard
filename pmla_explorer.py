
import json
import argparse
import sys
from datetime import datetime

DATA_PATH = r"c:\Users\HP\Downloads\EDOTS PMLA data\master_cases.json"

class PMLAExplorer:
    def __init__(self):
        self.cases = {}
        self.load_data()

    def load_data(self):
        try:
            with open(DATA_PATH, "r") as f:
                self.cases = json.load(f)
            print(f"Loaded {len(self.cases)} cases.")
        except FileNotFoundError:
            print("Error: master_cases.json not found. Run pmla_data_ingestor.py first.")
            sys.exit(1)

    def search(self, query):
        query = query.lower()
        results = []
        for ecir, data in self.cases.items():
            match = False
            # Search logic
            if query in ecir.lower(): match = True
            
            # Search persons
            for p in data.get("persons_involved", []):
                if query in str(p).lower(): match = True
                
            # Search searches/arrests
            # (Can expand this)
            
            if match:
                results.append(data)
        return results

    def print_case(self, case_data):
        print(f"\n{'='*60}")
        print(f"ECIR NO: {case_data['ecir_no']}")
        print(f"DATE   : {case_data.get('ecir_date', 'N/A')}")
        print(f"STATUS : {case_data.get('status', 'Unknown')}")
        print(f"{'='*60}")
        
        print("\n--- PERSONS INVOLVED ---")
        if case_data['persons_involved']:
            for p in case_data['persons_involved']:
                print(f"  - {p}")
        else:
            print("  (None recorded)")

        print("\n--- SEARCHES ---")
        if case_data['searches']:
            for s in case_data['searches']:
                print(f"  [{s.get('date', '?')}] @ {s.get('location', '?')} (Sheet: {s.get('sheet')})")
        else:
            print("  (None recorded)")

        print("\n--- ARRESTS ---")
        if case_data['arrests']:
            for a in case_data['arrests']:
                print(f"  [{a.get('date', '?')}] {a.get('name')} (Sheet: {a.get('sheet')})")
        else:
            print("  (None recorded)")

        print("\n--- PAO (Attachments) ---")
        if case_data['paos']:
             print(f"  {len(case_data['paos'])} records found.")
             # print first one as sample?
             # print(case_data['paos'][0])
        else:
            print("  (None recorded)")

        print("\n--- PROSECUTION COMPLAINTS (PC) ---")
        if case_data['pcs']:
             print(f"  {len(case_data['pcs'])} records found.")
        else:
            print("  (None recorded)")
        print(f"{'='*60}\n")

    def run(self):
        while True:
            try:
                q = input("\nEnter ECIR, Name, or 'exit': ").strip()
                if q.lower() in ['exit', 'quit']:
                    break
                if not q: continue
                
                results = self.search(q)
                print(f"Found {len(results)} matches.")
                
                if len(results) == 1:
                    self.print_case(results[0])
                elif len(results) > 1:
                    print("Matches:")
                    for i, r in enumerate(results[:10]):
                        print(f" {i+1}. {r['ecir_no']} (Persons: {len(r['persons_involved'])})")
                    if len(results) > 10: print(" ... and more")
                    
                    sel = input("Select # to view (or Enter to skip): ")
                    if sel.isdigit() and 1 <= int(sel) <= len(results):
                        self.print_case(results[int(sel)-1])
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    app = PMLAExplorer()
    app.run()
