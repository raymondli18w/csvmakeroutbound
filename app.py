import streamlit as st
import pandas as pd
from io import StringIO, BytesIO
from datetime import datetime

# =========================
# Column Synonyms Mapping
# =========================
COLUMN_SYNONYMS = {
    'Sales Order No.': ['reference', 'Reference', 'ref', 'Ref', 'Order', 'PO'],
    'Pick Date': ['pick date', 'Pick Date', 'date', 'Date', 'Order Date'],
    'Item No.': ['item', 'Item', 'sku', 'SKU', 'Item No.', 'Item Number'],
    'Each Qty': ['qty', 'Qty', 'quantity', 'Quantity', 'Each Qty'],
    'WHSE': ['whse', 'WHSE', 'warehouse', 'Warehouse'],
    'CLIENT': ['client', 'Client', 'Customer', 'customer id'],
    'Ship To': ['name', 'Name', 'Ship To', 'ship to', 'recipient'],
    'Street': ['street', 'Street', 'Address', 'address'],
    'City': ['city', 'City'],
    'state': ['province', 'Province', 'state', 'State'],
    'Zip Code': ['zip code', 'Zip Code', 'postal', 'Postal', 'ZIP'],
    'Country/Region': ['country', 'Country', 'Country/Region'],
    'Customer PO': ['customer po', 'Customer PO', 'PO', 'po number'],
    'Pro Number': ['pro', 'Pro', 'PRO', 'pro number', 'tracking', 'Tracking', 
                   'tracknumber', 'tracking #', 'tracking number', 'Tracking Number',
                   'track no', 'Track No', 'track_no', 'pro_no'],
    'Ship To Code': ['shiptocode', 'ShipToCode', 'ship to code', 'Ship To Code', 
                     'Ship Code', 'shipping code', 'Shipping Code', 'ship_code',
                     'shipto code', 'ShipTo', 'ship_to_code'],
    'SCAC': ['scac', 'SCAC', 'Scac', 'carrier code', 'Carrier Code', 'carrier_scac'],
}

# =========================
# Date Parser → MM/DD/YYYY
# =========================
def parse_to_mm_dd_yyyy(date_input):
    if pd.isna(date_input) or str(date_input).strip() == '':
        return None
    date_str = str(date_input).strip()
    if date_str.lower() in ('nan', 'null', 'none', ''):
        return None

    auto_formats = [
        "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d",
        "%d/%m/%Y", "%d-%m-%Y",
        "%m/%d/%y",
        "%d-%b-%Y", "%d-%b-%y",
        "%d %b %Y", "%b %d, %Y"
    ]
    
    for fmt in auto_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if "%y" in fmt and dt.year < 1900:
                dt = dt.replace(year=dt.year + 100)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
    return None

# =========================
# Helper Functions
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
# Clean Control Characters for ANSI
# =========================
def clean_ansi_content(csv_bytes):
    """
    Remove all control characters except:
    - CR (0x0D) - Carriage Return
    - LF (0x0A) - Line Feed  
    - TAB (0x09) - Tab
    Keeps only printable characters (0x20 and above) plus the exceptions above
    """
    # Keep: printable chars (>= 0x20) + CR (0x0D) + LF (0x0A) + TAB (0x09)
    cleaned = bytes([b for b in csv_bytes if b >= 0x20 or b in (0x09, 0x0A, 0x0D)])
    
    # Optional: Log if we removed any control characters
    removed_count = len(csv_bytes) - len(cleaned)
    if removed_count > 0:
        st.info(f"🧹 Removed {removed_count} control character(s) to ensure ANSI compatibility")
    
    return cleaned

# =========================
# Main Processing Function
# =========================
def process_tsv(raw_text):
    try:
        df = pd.read_csv(StringIO(raw_text), sep='\t', engine='python', dtype=str, keep_default_na=False, na_values=[])
    except Exception as e:
        st.error(f"❌ Failed to parse TSV: {e}")
        return None

    df = df.replace({'nan': '', 'NaN': '', 'NAN': '', 'null': '', 'None': ''}).fillna('')
    df = standardize_headers(df)

    required_cols = ['Sales Order No.', 'Item No.', 'Each Qty', 'CLIENT', 'WHSE', 'Pick Date']
    missing_required = [col for col in required_cols if col not in df.columns]
    if missing_required:
        st.error(f"❌ Missing required columns after mapping: {missing_required}")
        return None

    optional_cols = ['Ship To', 'Street', 'City', 'state', 'Zip Code', 'Country/Region', 'Customer PO', 'Pro Number', 'Ship To Code', 'SCAC']
    for col in optional_cols:
        if col not in df.columns:
            df[col] = ''

    df['Pick Date Clean'] = df['Pick Date'].apply(parse_to_mm_dd_yyyy)

    output_rows = []
    failed_rows = []

    for idx, row in df.iterrows():
        so = safe_value(row, 'Sales Order No.').strip()
        item = safe_value(row, 'Item No.').strip()
        qty_str = safe_value(row, 'Each Qty').strip()
        client = safe_value(row, 'CLIENT').strip()
        whse = safe_value(row, 'WHSE').strip()
        pick_date = row['Pick Date Clean']
        pro_number = safe_value(row, 'Pro Number').strip()
        ship_to_code = safe_value(row, 'Ship To Code').strip()
        scac = safe_value(row, 'SCAC').strip()

        reasons = []
        if not so: reasons.append("Sales Order No. missing")
        if not item: reasons.append("Item No. missing")
        if not qty_str: reasons.append("Each Qty missing")
        if not client: reasons.append("CLIENT missing")
        if not whse: reasons.append("WHSE missing")
        if pick_date is None: reasons.append("Pick Date invalid")

        if reasons:
            failed_rows.append((idx + 2, "; ".join(reasons)))
            continue

        try:
            qty = int(float(qty_str))
        except (ValueError, TypeError):
            failed_rows.append((idx + 2, f"Each Qty '{qty_str}' is not a number"))
            continue

        # Build output row A–Z + AA–AZ
        out_row = {chr(65 + i): '' for i in range(26)}
        out_row.update({f"A{chr(65+i)}": '' for i in range(26)})

        # Populate columns
        out_row['A'] = 'BC'
        out_row['B'] = trim_text(client, 10)
        out_row['C'] = trim_text(so, 30)
        out_row['D'] = trim_text(safe_value(row, 'Customer PO'), 30)
        out_row['F'] = pick_date
        out_row['H'] = trim_text(ship_to_code, 20)  # Ship To Code - column H
        out_row['I'] = trim_text(safe_value(row, 'Ship To'), 45)
        out_row['K'] = trim_text(safe_value(row, 'Street'), 30)
        out_row['M'] = trim_text(safe_value(row, 'City'), 10)
        out_row['N'] = trim_text(safe_value(row, 'state'), 10)
        out_row['O'] = trim_text(safe_value(row, 'Zip Code'), 10)
        out_row['P'] = trim_text(safe_value(row, 'Country/Region'), 10)
        out_row['Q'] = trim_text(scac, 10)  # SCAC - column Q
        out_row['T'] = trim_text(pro_number, 50)  # Pro Number - column T
        out_row['X'] = trim_text(item, 20)
        out_row['Y'] = qty
        out_row['AJ'] = trim_text(whse, 10)

        output_rows.append(out_row)

    if not output_rows:
        st.error("❌ No valid rows found.")
        if failed_rows:
            st.subheader("🔍 First 10 failures:")
            for rnum, reason in failed_rows[:10]:
                st.text(f"Row {rnum}: {reason}")
        return None
    else:
        return pd.DataFrame(output_rows)

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="TSV to ANSI CSV Converter", layout="wide")
st.title("🚛 TSV to Outbound ANSI CSV Converter")
st.markdown("""
Paste your **tab-separated** data below.  

**Required columns:** `Client`, `WHSE`, `Reference`, `Pick Date`, `name`, `item`, `qty`, `Customer PO`  

**Optional columns:**  
- `Pro Number` (pro, PRO, tracking, Tracking, tracknumber, tracking #, tracking number, pro_no) → Maps to **Column T**  
- `Ship To Code` (shiptocode, ShipToCode, ship to code, Ship Code, shipping code, ShipTo) → Maps to **Column H**  
- `SCAC` (scac, SCAC, carrier code, Carrier Code, carrier_scac) → Maps to **Column Q**  

**✅ ANSI Safe Mode:** Control characters (like 0x14) will be automatically removed for compatibility.
""")

raw_data = st.text_area("Paste your TSV data:", height=300)

if st.button("✅ Process & Download CSV"):
    if not raw_data.strip():
        st.warning("⚠️ Please paste your data.")
    else:
        df_out = process_tsv(raw_data)
        if df_out is not None:
            # Generate CSV as bytes
            csv_bytes = df_out.to_csv(index=False, header=False, sep=',', encoding='cp1252', errors='replace')
            
            # Clean control characters for ANSI compatibility
            cleaned_csv_bytes = clean_ansi_content(csv_bytes.encode('cp1252', errors='replace'))
            
            # Auto-trigger download
            st.download_button(
                label="⬇️ Your ANSI-safe file is ready — click to download",
                data=cleaned_csv_bytes,
                file_name="s_output.csv",
                mime="text/csv"
            )
            
            # Show success message
            st.success("✅ File processed successfully! Download ready.")
            st.caption(f"📄 Output size: {len(cleaned_csv_bytes):,} bytes (ANSI/Windows-1252 encoded)")
            
            # Show preview of first few rows
            if st.checkbox("Show preview of first 5 rows"):
                preview_df = df_out.head(5)
                st.dataframe(preview_df)
