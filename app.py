import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

# =========================
# Column Synonyms (unchanged)
# =========================
COLUMN_SYNONYMS = {
    'Sales Order No.': [
        'reference', 'ref', 'hdr', 'po ref', 'order', 'header ref', 'so no', 'ClientOrderNumber',
        'ship reference', 'reference #', 'Reference'
    ],
    'Pick Date': [
        'pick date', 'date picked', 'ORDER_DATE', 'ship date', 'order date', 'date',
        'Pick Date'
    ],
    'Item No.': [
        'item', 'product', 'sku', 'ItemCode', 'item number', 'item no', 'item code', 'item'
    ],
    'Each Qty': [
        'qty', 'quantity', 'Each Qty', 'qty', 'OrderQuantity', 'units'
    ],
    'WHSE': [
        'whse', 'warehouse', 'WHSE', 'WH'
    ],
    'CLIENT': [
        'client', 'Client', 'customer id', 'Customer'
    ],
    'Ship To': ['name', 'Ship To', 'recipient'],
    'Street': ['Street', 'street', 'addr 1'],
    'City': ['City', 'city'],
    'state': ['Province', 'province', 'state'],
    'Zip Code': ['Zip Code', 'zip', 'postal'],
    'Country/Region': ['Country', 'country'],
    'Customer PO': ['Customer PO', 'po', 'PO', 'Customer PO']
}

# =========================
# Address Validation (simplified — not used for validity, but kept)
# =========================
CANADA_PROVINCES = ["AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"]
US_STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
             "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
             "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"]

def validate_address(row):
    return "Valid"  # Not required for row validity in your case — skip strict check

# =========================
# Date Parser
# =========================
def parse_to_mm_dd_yyyy(date_input, format_hint="auto", custom_format=""):
    if pd.isna(date_input) or str(date_input).strip() == '':
        return None
    date_str = str(date_input).strip().lower()
    if date_str in ('nan', 'null', 'none', ''):
        return None

    format_map = {
        "MM/DD/YYYY": "%m/%d/%Y",
        "MM-DD-YYYY": "%m-%d-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
        "DD/MM/YYYY": "%d/%m/%Y",
        "DD-MM-YYYY": "%d-%m-%Y",
        "MM/DD/YY": "%m/%d/%y",
        "YYYYMMDD": "%Y%m%d",
        "DD-MON-YYYY": "%d-%b-%Y",
        "DD-MON-YY": "%d-%b-%y",
        "DDMONYYYY": "%d%b%Y",
        "DDMONYY": "%d%b%y",
        "DD/MON/YYYY": "%d/%b/%Y",
        "DD/MON/YY": "%d/%b/%y",
    }

    if format_hint == "custom":
        try:
            dt = datetime.strptime(date_str, custom_format)
            return dt.strftime("%m/%d/%Y")
        except:
            return None

    if format_hint in format_map:
        fmt = format_map[format_hint]
        try:
            dt = datetime.strptime(date_str, fmt)
            if "%y" in fmt and dt.year < 1900:
                dt = dt.replace(year=dt.year + 100)
            return dt.strftime("%m/%d/%Y")
        except:
            return None

    # Auto-detect
    for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
                "%m/%d/%y", "%Y%m%d", "%d-%b-%Y", "%d-%b-%y", "%d%b%Y", "%d%b%y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            if "%y" in fmt:
                dt = dt.replace(year=dt.year + 100 if dt.year < 100 else dt.year)
            return dt.strftime("%m/%d/%Y")
        except:
            continue
    return None

# =========================
# Helpers
# =========================
def trim_text(val, max_len):
    if pd.isna(val) or val == '' or val is None:
        return ''
    return str(val)[:max_len]

def safe_value(row, col):
    val = row.get(col, '')
    if pd.isna(val) or val == '' or val is None or str(val).lower() in ('nan', 'null'):
        return ''
    return str(val)

def standardize_headers(df):
    mapping = {}
    for std_col, synonyms in COLUMN_SYNONYMS.items():
        for col in df.columns:
            if str(col).strip().lower() in [s.lower() for s in synonyms]:
                mapping[col] = std_col
                break
    df.rename(columns=mapping, inplace=True)
    return df

# =========================
# Main Processor with DIAGNOSTICS
# =========================
def process_tsv(raw_text, date_format_hint="auto", custom_format=""):
    try:
        # 🔑 KEY FIX: Use explicit tab delimiter
        df = pd.read_csv(StringIO(raw_text), sep='\t', engine='python', dtype=str, keep_default_na=False, na_values=[])
    except Exception as e:
        st.error(f"❌ CSV parse error: {e}")
        return None

    # Clean 'nan' strings
    df = df.replace({'nan': '', 'NaN': '', 'NAN': '', 'null': '', 'None': ''}).fillna('')

    st.write("📋 Raw columns:", list(df.columns))

    df = standardize_headers(df)
    st.write("🔄 After standardization:", list(df.columns))

    # Check required columns
    required = ['Sales Order No.', 'Item No.', 'Each Qty', 'CLIENT', 'WHSE', 'Pick Date']
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"❌ Required columns missing after mapping: {missing}")
        st.warning("💡 Tip: Your headers must include variants like 'Reference' → 'Sales Order No.', 'item' → 'Item No.', etc.")
        return None

    # Add missing optional cols as empty
    for col in ['Ship To', 'Street', 'City', 'state', 'Zip Code', 'Country/Region', 'Customer PO', 'Date2']:
        if col not: 
            df[col] = ''

    # Parse dates
    df['Pick Date Clean'] = df['Pick Date'].apply(lambda x: parse_to_mm_dd_yyyy(x, format_hint=date_format_hint))
    invalid_dates = df['Pick Date Clean'].isna() & df['Pick Date'].notna()
    if invalid_dates.any():
        st.warning(f"⚠️ {invalid_dates.sum()} rows have unparsable Pick Dates")

    # Process rows with diagnostics
    output_rows = []
    failed_reasons = []

    for i, row in df.iterrows():
        so = safe_value(row, 'Sales Order No.').strip()
        item = safe_value(row, 'Item No.').strip()
        qty_str = safe_value(row, 'Each Qty').strip()
        client = safe_value(row, 'CLIENT').strip()
        whse = safe_value(row, 'WHSE').strip()
        pick_date_clean = row['Pick Date Clean']

        reasons = []
        if not so: reasons.append("Sales Order No. empty")
        if not item: reasons.append("Item No. empty")
        if not qty_str: reasons.append("Each Qty empty")
        if not client: reasons.append("CLIENT empty")
        if not whse: reasons.append("WHSE empty")
        if pick_date_clean is None: reasons.append("Pick Date invalid/unparsable")

        if reasons:
            failed_reasons.append((i+1, reasons))
            continue

        # Try to convert qty
        try:
            qty = int(float(qty_str))
        except:
            failed_reasons.append((i+1, [f"Each Qty '{qty_str}' not numeric"]))
            continue

        # Build output
        out_row = {chr(65 + j): '' for j in range(26)}  # A-Z
        out_row.update({f"A{chr(65+j)}": '' for j in range(26)})  # AA-AZ etc.
        out_row['A'] = 'BC'
        out_row['B'] = trim_text(client, 10)
        out_row['C'] = trim_text(so, 30)
        out_row['D'] = trim_text(safe_value(row, 'Customer PO'), 30)
        out_row['F'] = pick_date_clean
        out_row['I'] = trim_text(safe_value(row, 'Ship To'), 45)
        out_row['K'] = trim_text(safe_value(row, 'Street'), 30)
        out_row['M'] = trim_text(safe_value(row, 'City'), 10)
        out_row['N'] = trim_text(safe_value(row, 'state'), 10)
        out_row['O'] = trim_text(safe_value(row, 'Zip Code'), 10)
        out_row['P'] = trim_text(safe_value(row, 'Country/Region'), 10)
        out_row['X'] = trim_text(item, 20)
        out_row['Y'] = qty
        output_rows.append(out_row)

    if not output_rows:
        st.error("❌ No valid rows processed.")
        if failed_reasons:
            st.subheader("🔍 Failure details (first 10 rows):")
            for idx, reasons in failed_reasons[:10]:
                st.text(f"Row {idx}: {'; '.join(reasons)}")
        return None
    else:
        st.success(f"✅ Processed {len(output_rows)} valid rows.")
        return pd.DataFrame(output_rows)

# =========================
# Streamlit UI
# =========================
st.title("TSV Validator & Converter")
st.markdown("""
Paste your **tab-separated** data below.  
Required headers (case-insensitive):  
`Client`, `WHSE`, `Reference`, `Pick Date`, `name`, `item`, `qty`, `Customer PO`  
→ Maps to: `CLIENT`, `WHSE`, `Sales Order No.`, `Pick Date`, `Ship To`, `Item No.`, `Each Qty`, `Customer PO`
""")

raw_data = st.text_area("Paste TSV data (use real tabs!):", height=300, value="""Client	WHSE	Reference	Pick Date	name	Street	City	Zip Code	Country	item	qty	Customer PO
KL04	1587Derwen	295583-75917	1/30/2026	Bytown Parts & Inductrial	1027 Chamberlin Avenue	Prince Rupert	V8J 4J5	CA	HF0480	42	16724""")

st.markdown("### 📅 Date Format")
date_opt = st.selectbox("Pick Date format:", ["Auto-detect", "MM/DD/YYYY"], index=0)
fmt = "auto" if date_opt == "Auto-detect" else "MM/DD/YYYY"

if st.button("🔍 Validate & Convert"):
    if not raw_data.strip():
        st.warning("Paste data first.")
    else:
        df_out = process_tsv(raw_data, date_format_hint=fmt)
        if df_out is not None:
            csv = df_out.to_csv(index=False, header=False, encoding='cp1252').replace('\n', '\r\n')
            st.download_button("📥 Download CSV", csv, "output.csv", "text/csv")
