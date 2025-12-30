
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import io
import ast

# --- Configuration ---
st.set_page_config(page_title="ED Command Center", layout="wide", page_icon="🛡️")

# --- Custom Styling ---
st.markdown("""
    <style>
    /* Force improved contrast for dark/light modes */
    .stApp { color: #e0e0e0; } 
    .stMetric { background-color: #1e2126 !important; border: 1px solid #303339; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .css-10trblm { color: #fff !important; }
    
    /* Chevron Flow - Dark Mode Compatible */
    .chevron-container { 
        display: flex; justify-content: space-between; align-items: center; 
        background: #1e2126; padding: 20px; border-radius: 10px; margin-bottom: 25px; 
        border: 1px solid #303339; 
    }
    .step { 
        position: relative; background: #2b303b; padding: 15px; width: 18%; 
        text-align: center; font-weight: bold; 
        clip-path: polygon(90% 0%, 100% 50%, 90% 100%, 0% 100%, 10% 50%, 0% 0%); 
        color: #a0a0a0; transition: 0.3s; 
    }
    .step-active { background: #004a99 !important; color: white !important; }
    .step-val { display: block; font-size: 1.2em; margin-top: 5px; color: inherit; }
    .step-label { font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; color: inherit; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e2126; border-radius: 4px; padding: 10px 20px; color: #fff; }
    .stTabs [aria-selected="true"] { background-color: #004a99; color: #fff; }
    </style>
""", unsafe_allow_html=True)

# --- Logic: Data Processing ---
@st.cache_data
def process_data(file):
    xls = pd.ExcelFile(file)
    sheets = {sheet: xls.parse(sheet) for sheet in xls.sheet_names}
    
    # 1. Automatic Main Sheet Detection
    main_sheet_name = next((s for s in sheets if 'sheet 1' in s.lower()), None)
    if not main_sheet_name:
         main_sheet_name = list(sheets.keys())[0] # Fallback
         
    df = sheets[main_sheet_name]
    
    # 2. Header Cleanup
    # Scan first 20 rows for "ECIR" to find likely header
    header_idx = -1
    for i, row in df.head(20).iterrows():
        row_str = " ".join([str(x) for x in row if pd.notna(x)])
        if "ECIR No" in row_str or "Case No" in row_str:
            header_idx = i
            break
            
    if header_idx != -1:
        df.columns = df.iloc[header_idx]
        df = df.iloc[header_idx+1:].reset_index(drop=True)

    # Standardize Column Names
    df.columns = [str(c).strip() for c in df.columns]

    # 3. Type Conversion & Enrichment
    # Convert Numeric Columns
    def clean_currency(val):
        if pd.isna(val) or val == '': return 0.0
        try:
            val_str = str(val).replace(',', '')
            return float(val_str)
        except:
            return 0.0
            
    cols_map = {
        'Details of PoC identified (in Rs. Cr.), as per ECIR': 'PoC_Value',
        'Total value of PAOs issued': 'PAO_Value',
        'No. of arrest': 'Arrest_Count',
        'No. of searches conducted': 'Search_Count'
    }
    
    for target_key, target_internal in cols_map.items():
        # strict or fuzzy match
        details_col = next((c for c in df.columns if target_key.lower() in c.lower()), None)
        # fallback for PoC
        if not details_col and 'PoC' in target_key:
             details_col = next((c for c in df.columns if 'poc' in c.lower() and 'cr' in c.lower()), None)
        
        if details_col:
            df[target_internal] = df[details_col].apply(clean_currency)
        else:
            df[target_internal] = 0.0

    # Extract Year from Date
    # Find Date Column
    date_col = next((c for c in df.columns if 'date' in c.lower() and ('ecir' in c.lower() or 'case' in c.lower())), None)
    if date_col:
        df['ECIR_Date_Clean'] = pd.to_datetime(df[date_col], errors='coerce')
        df['Year'] = df['ECIR_Date_Clean'].dt.year.fillna(0).astype(int)
    else:
        df['Year'] = 0
        
    # Helper for Dropdown Label
    # Find Name column
    name_col = next((c for c in df.columns if 'name' in c.lower() and 'case' in c.lower()), None)
    ecir_col = next((c for c in df.columns if "ECIR" in c and "No" in c), None)

    if ecir_col and name_col:
         df['Dropdown_Label'] = df[ecir_col].astype(str) + " - " + df[name_col].astype(str).str[:40] + "..."
    elif ecir_col:
         df['Dropdown_Label'] = df[ecir_col].astype(str)

    return df, sheets

# --- UI: Sidebar & Auth ---
st.sidebar.title("🛡️ ED Command Center")
api_key = st.sidebar.text_input("Gemini API Key (Optional)", type="password", help="Enter to enable AI insights")
uploaded_file = st.sidebar.file_uploader("Upload PMLA Master Excel", type=["xlsx"])

if uploaded_file:
    with st.spinner('Ingesting and Linking Data...'):
        try:
            df, all_sheets_dict = process_data(uploaded_file)
        except Exception as e:
            st.error(f"Data Processing Error: {e}")
            st.stop()
    
    # --- Sidebar: Global Filters ---
    st.sidebar.divider()
    st.sidebar.subheader("🔎 Global Filters")
    
    # Year Filter
    available_years = sorted([y for y in df['Year'].unique() if y > 0], reverse=True)
    if available_years:
        selected_years = st.sidebar.multiselect("Select Year(s)", available_years, default=available_years[:3])
    else:
        selected_years = []
    
    # IO Filter / IO Name
    # Try to find IO or Investigating Officer Column
    io_col = next((c for c in df.columns if ('io' in c.lower() or 'investigating' in c.lower() or 'officer' in c.lower()) and 'zonal' not in c.lower() and 'type' not in c.lower()), None)
    
    selected_ios = []
    if io_col:
        ios = sorted(df[io_col].dropna().astype(str).unique())
        selected_ios = st.sidebar.multiselect("Investigating Officer (IO)", ios)
    else:
        st.sidebar.warning("Could not automatically detect 'IO' column.")
    
    # Min PoC
    min_poc = st.sidebar.slider("Min PoC (₹ Cr)", 0, 5000, 0, step=10)
    
    # Action Filter
    action_type = st.sidebar.radio("Status Filter", ["All Cases", "Arrests Made", "Attachment Done", "Prosecution Filed"])

    # --- APPLY FILTERS ---
    filtered_df = df.copy()
    
    if selected_years:
        filtered_df = filtered_df[filtered_df['Year'].isin(selected_years)]
        
    if selected_ios and io_col:
        filtered_df = filtered_df[filtered_df[io_col].astype(str).isin(selected_ios)]
        
    filtered_df = filtered_df[filtered_df['PoC_Value'] >= min_poc]
    
    if action_type == "Arrests Made":
        filtered_df = filtered_df[filtered_df['Arrest_Count'] > 0]
    elif action_type == "Attachment Done":
        filtered_df = filtered_df[filtered_df['PAO_Value'] > 0]
    elif action_type == "Prosecution Filed":
        # Find PC column
        pc_col = next((c for c in df.columns if 'pc' in c.lower() and 'filed' in c.lower()), None)
        if pc_col:
             filtered_df = filtered_df[filtered_df[pc_col].astype(str).str.contains('Yes', case=False, na=False)]

    # --- MAIN DASHBOARD ---
    
    tab_global, tab_drill, tab_ai = st.tabs(["📊 Global Analytics", "🔍 Case Drill-down", "🤖 Gemini Intelligence"])
    
    with tab_global:
        st.subheader(f"Snapshot: {len(filtered_df)} Cases Selected")
        
        # KEY METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total PoC Identified", f"₹{filtered_df['PoC_Value'].sum():,.2f} Cr")
        m2.metric("Total Attached (PAO)", f"₹{filtered_df['PAO_Value'].sum():,.2f} Cr")
        m3.metric("Total Arrests", int(filtered_df['Arrest_Count'].sum()))
        m4.metric("Active Year Range", f"{min(selected_years) if selected_years else 'N/A'} - {max(selected_years) if selected_years else 'N/A'}")
        
        # BUBBLE CHART
        st.write("### 📈 PoC vs Attachment Efficacy")
        if not filtered_df.empty:
            fig = px.scatter(
                filtered_df, 
                x='PoC_Value', 
                y='PAO_Value',
                size='Arrest_Count', 
                color='Year',
                hover_data=filtered_df.columns[:5], # Show first few cols on hover
                title="PoC vs Attachment (Size = Arrests)",
                template="plotly_dark",
                height=500
            )
            # Add reference line
            max_val = max(filtered_df['PoC_Value'].max(), 1)
            fig.add_shape(type="line", line=dict(dash="dash", width=1, color="gray"), x0=0, y0=0, x1=max_val, y1=max_val)
            st.plotly_chart(fig, use_container_width=True)
            
            # EXPORT
            st.write("### 📥 Export Data")
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Filtered Report (CSV)", csv, "pmla_filtered_report.csv", "text/csv")
        else:
            st.info("No data matches the current filters.")

    with tab_drill:
        # ECIR Selector from FILTERED list - RESTORED NAME
        if 'Dropdown_Label' in filtered_df.columns:
            case_options = filtered_df['Dropdown_Label'].unique()
            selected_label = st.selectbox("Select Case to Inspect", case_options)
            
            # Find ECIR from label
            if selected_label:
                selected_ecir = selected_label.split(" - ")[0]
                # Find ECIR col again
                ecir_col_drill = next((c for c in filtered_df.columns if "ECIR" in c and "No" in c), None)
                
                case_row = filtered_df[filtered_df[ecir_col_drill].astype(str) == selected_ecir].iloc[0]
                
                # --- CHEVRON FLOW (Reused) ---
                reg_date = str(case_row.get('ECIR_Date_Clean', 'N/A')).split(' ')[0]
                searches = int(case_row['Search_Count'])
                arrests = int(case_row['Arrest_Count'])
                pao_v = float(case_row['PAO_Value'])
               
                # PC Status
                pc_col_drill = next((c for c in filtered_df.columns if 'pc' in c.lower() and 'filed' in c.lower()), None)
                pc_status = "Yes" if pc_col_drill and 'Yes' in str(case_row[pc_col_drill]) else "No"

                st.markdown(f"""
                    <div class="chevron-container">
                        <div class="step step-active"><span class="step-label">Registered</span><span class="step-val">{reg_date}</span></div>
                        <div class="step {'step-active' if searches > 0 else ''}"><span class="step-label">Searches</span><span class="step-val">{searches}</span></div>
                        <div class="step {'step-active' if arrests > 0 else ''}"><span class="step-label">Arrests</span><span class="step-val">{arrests}</span></div>
                        <div class="step {'step-active' if pao_v > 0 else ''}"><span class="step-label">Attached</span><span class="step-val">₹{pao_v:,.2f} Cr</span></div>
                        <div class="step {'step-active' if pc_status == 'Yes' else ''}"><span class="step-label">Prosecution</span><span class="step-val">{pc_status}</span></div>
                    </div>
                """, unsafe_allow_html=True)
                
                # DETAILS
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Case Details:**")
                    # Clean dictionary for display (remove internal helpers)
                    disp_dict = {k:v for k,v in case_row.astype(str).to_dict().items() if k not in ['ECIR_Date_Clean', 'Dropdown_Label']}
                    st.json(disp_dict)
                with c2:
                    st.write("**Financial Gap Analysis:**")
                    poc = case_row['PoC_Value']
                    pao = case_row['PAO_Value']
                    gap = poc - pao
                    
                    fig_gap = go.Figure(data=[
                        go.Bar(name='PoC', x=['Amount'], y=[poc], marker_color='#ffc107'),
                        go.Bar(name='Attached', x=['Amount'], y=[pao], marker_color='#198754')
                    ])
                    # Fix Dark Mode for this Chart
                    fig_gap.update_layout(template="plotly_dark", height=300)
                    st.plotly_chart(fig_gap, key=f"drill_{selected_ecir}", use_container_width=True)
                    
                    if gap > 0:
                        st.error(f"⚠️ Unattached PoC Gap: ₹{gap:,.2f} Cr")
                    else:
                        st.success("✅ Fully Attached / Excess Attachment")
        else:
            st.error("Dropdown labels could not be generated.")

    with tab_ai:
        st.header("🤖 Investigative Assistant (Gemini 2.0)")
        if not api_key:
            st.warning("Please enter your Google Gemini API Key in the sidebar to use this feature.")
        else:
            # Upgrade to 2025 Client Logic
            try:
                # Direct Import for 2025 SDK
                from google import genai
                from google.genai import types
                
                client = genai.Client(api_key=api_key)
                
                # Dynamic Routing Logic
                # "gemini-3-flash" for smart/fast analysis
                # "gemini-3-pro-image-preview" for visually amazing infographics
                # "gemini-2.0-flash-exp" as safe fallback if 3 is not out for this user yet
                
                # Initialize Chat State
                if "messages" not in st.session_state:
                    st.session_state.messages = []
                
                # Reset Button
                if st.button("🗑️ Reset Chat"):
                     st.session_state.messages = []
                     st.rerun()

                # Display Chat
                for message in st.session_state.messages:
                    role_display = "user" if message["role"] == "user" else "assistant"
                    with st.chat_message(role_display):
                        if "[Generated Image]" in message["content"]:
                             st.write("🖼️ [Image Generated]")
                        else:
                             st.markdown(message["content"])

                # Input
                if user_input := st.chat_input("Ask for analysis, infographics, or details..."):
                    st.chat_message("user").markdown(user_input)
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                    with st.spinner("Agent is determining the best tool..."):
                        try:
                            # 1. Determine Intent
                            is_image_intent = any(k in user_input.lower() for k in ['image', 'infographic', 'draw', 'picture', 'visual', 'chart', 'graph'])
                            
                            # 2. Select Model ID & Construct Prompt
                            response = None
                            
                            if is_image_intent:
                                st.caption("🎨 activating **Nano-Banana-Pro** (Visual Engine)...")
                                try:
                                    # IMAGE MODE
                                    # 1. Use the specific model requested by user for images
                                    image_model_id = "gemini-3-pro-image-preview" 
                                    
                                    # 2. SIMPLIFIED PROMPT (Crucial for Image Models)
                                    # Do NOT dump CSV data. Summary only.
                                    # extracting a tiny summary for context
                                    stats_summary = (
                                        f"Total PoC: {filtered_df['PoC_Value'].sum()} Cr, "
                                        f"Cases: {len(filtered_df)}, "
                                        f"Arrests: {filtered_df['Arrest_Count'].sum()}"
                                    )
                                    
                                    img_prompt = (
                                        f"Create a high-quality chart or infographic about: {user_input}. "
                                        f"Key Data Hints: {stats_summary}. "
                                        "Do not generate text explanations. Just generate the image."
                                    )
                                    
                                    response = client.models.generate_content(
                                        model=image_model_id,
                                        contents=img_prompt
                                    )
                                except Exception as e_img:
                                    st.warning(f"Nano-Banana (Image) failed: {e_img}. Trying fallback...")
                                    # Fallback to 2.0 Flash Exp which might handle it or just give text
                                    response = client.models.generate_content(
                                        model='gemini-2.0-flash-exp',
                                        contents=f"Generate an image for {user_input}"
                                    )

                            else:
                                # TEXT/ANALYSIS MODE
                                st.caption("🧠 activating **Gemini-2.0-Flash** (Deep Reasoning)...")
                                analysis_model_id = "gemini-2.0-flash-exp"
                                
                                # Full Context Pattern
                                final_prompt = f"""
                                SYSTEM: You are a Senior PMLA Analyst.
                                DATA CONTEXT:\n{csv_context}\n
                                USER QUERY: {user_input}
                                """
                                
                                response = client.models.generate_content(
                                    model=analysis_model_id,
                                    contents=final_prompt
                                )
                            
                            # 4. Handle Response (Text vs Image)
                            handled_image = False
                            
                            if response.parts:
                                for part in response.parts:
                                    # Check for Inline Data (Image)
                                    # The SDK wrapper might differ slightly, checking attributes safely
                                    if hasattr(part, 'inline_data') and part.inline_data:
                                        from PIL import Image
                                        import io
                                        # Decode bytes
                                        img_data = part.inline_data.data
                                        if isinstance(img_data, str): # Base64 string in some versions
                                            import base64
                                            img_bytes = base64.b64decode(img_data)
                                            img = Image.open(io.BytesIO(img_bytes))
                                        else:
                                            img = Image.open(io.BytesIO(img_data))
                                            
                                        st.image(img, caption="Generated Logic", use_container_width=True)
                                        st.session_state.messages.append({"role": "assistant", "content": "[Generated Image]"})
                                        handled_image = True
                                        
                                    elif hasattr(part, 'text') and part.text:
                                         st.markdown(part.text)
                                         st.session_state.messages.append({"role": "assistant", "content": part.text})

                            # Fallback if no parts found (rare)
                            if not response.parts and response.text:
                                st.markdown(response.text)

                        except Exception as e:
                            st.error(f"Analysis Error: {e}")
                            st.error("Tip: This feature requires a Gemini 2.0+ capable API key.")
                            
            except Exception as import_err:
                 st.error(f"Critical SDK Error: {import_err}")
                 st.error("Please ensure `google-genai` is installed.")
else:
    st.image("https://upload.wikimedia.org/wikipedia/en/c/cf/Enforcement_Directorate.svg", width=100)
    st.title("PMLA Command Center")
    st.markdown("### Secure Intelligence Portal")
    st.info("Please upload the Master PMLA Excel File to begin.")
