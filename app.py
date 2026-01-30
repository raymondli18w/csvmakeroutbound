import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

# =========================
# Column Synonyms Mapping (tailored to your headers)
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
}

# =========================
# Date Parser → MM/DD/YYYY
# =========================
def parse_to_mm_dd_yyyy(date_input, format_hint="auto", custom_format=""):
    if pd.isna(date_input) or str(date_input).strip() == '':
        return None
    date_str = str(date_input).strip()
    if date_str.lower() in ('nan', 'null', 'none', ''):
        return None

    # Auto-detect common formats
    auto_formats = [
        "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d",
        "%d/%m/%Y", "%d-%m-%Y",
        "%m/%d/%y",
        "%d-%b-%Y", "%d-%b-%y",  # e.g., 30-Jan-2026
        "%d %b %Y", "%b %d, %Y"
    ]
    
    if format_hint == "custom":
        try:
            dt = datetime.strptime(date_str, custom_format)
            return dt.strftime("%m/%d/%Y")
        except:
            return None

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
# Main Processing Function
# =========================
def process_tsv(raw_text, date_format_hint="auto", custom_format=""):
    try:
        # 🔑 Use explicit TAB delimiter
        df = pd.read_csv(StringIO(raw_text), sep='\t', engine='python', dtype=str, keep_default_na=False, na_values=[])
    except Exception as e:
        st.error(f"❌ Failed to parse TSV: {e}")
        return None

    # Clean up 'nan' strings
    df = df.replace({'nan': '', 'NaN': '', 'NAN': '', 'null': '', 'None': ''}).fillna('')

    st.write("📋 Detected columns:", list(df.columns))

    # Standardize column names
    df = standardize_headers(df)
    st.write("🔄 Standardized columns:", list(df.columns))

    # Required fields
    required_cols = ['Sales Order No.', 'Item No.', 'Each Qty', 'CLIENT', 'WHSE', 'Pick Date']
    missing_required = [col for col in required_cols if col not in df.columns]
    if missing_required:
        st.error(f"❌ Missing required columns after mapping: {missing_required}")
        return None

    # Ensure optional columns exist
    optional_cols = ['Ship To', 'Street', 'City', 'state', 'Zip Code', 'Country/Region', 'Customer PO', 'Date2']
    for col in optional_cols:
        if col not in df.columns:
            df[col] = ''

    # Parse Pick Date
    df['Pick Date Clean'] = df['Pick Date'].apply(
        lambda x: parse_to_mm_dd_yyyy(x, format_hint=date_format_hint, custom_format=custom_format)
    )

    # Process rows with diagnostics
    output_rows = []
    failed_rows = []

    for idx, row in df.iterrows():
        so = safe_value(row, 'Sales Order No.').strip()
        item = safe_value(row, 'Item No.').strip()
        qty_str = safe_value(row, 'Each Qty').strip()
        client = safe_value(row, 'CLIENT').strip()
        whse = safe_value(row, 'WHSE').strip()
        pick_date = row['Pick Date Clean']

        reasons = []
        if not so: reasons.append("Sales Order No. missing")
        if not item: reasons.append("Item No. missing")
        if not qty_str: reasons.append("Each Qty missing")
        if not client: reasons.append("CLIENT missing")
        if not whse: reasons.append("WHSE missing")
        if pick_date is None: reasons.append("Pick Date invalid/unparsable")

        if reasons:
            failed_rows.append((idx + 2, "; ".join(reasons)))  # +2 for header + 0-index
            continue

        # Validate quantity is numeric
        try:
            qty = int(float(qty_str))
        except (ValueError, TypeError):
            failed_rows.append((idx + 2, f"Each Qty '{qty_str}' is not a number"))
            continue

        # Build output row (A–Z + AA–AZ style)
        out_row = {chr(65 + i): '' for i in range(26)}  # A-Z
        out_row.update({f"A{chr(65+i)}": '' for i in range(26)})  # AA-AZ

        out_row['A'] = 'BC'
        out_row['B'] = trim_text(client, 10)
        out_row['C'] = trim_text(so, 30)
        out_row['D'] = trim_text(safe_value(row, 'Customer PO'), 30)
        out_row['F'] = pick_date
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
        st.error("❌ No valid rows found.")
        if failed_rows:
            st.subheader("🔍 First 10 failures:")
            for row_num, reason in failed_rows[:10]:
                st.text(f"Row {row_num}: {reason}")
        return None
    else:
        st.success(f"✅ Successfully processed {len(output_rows)} rows.")
        return pd.DataFrame(output_rows)

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="TSV to Outbound CSV Converter", layout="wide")
st.title("🚛 TSV to Outbound CSV Converter")
st.markdown("""
Paste your **tab-separated** data below.  
Required columns (case-insensitive):  
`Client`, `WHSE`, `Reference`, `Pick Date`, `name`, `item`, `qty`, `Customer PO`
""")

raw_data = st.text_area(
    "Paste your TSV data here:",
    height=300,
    placeholder="Client\tWHSE\tReference\tPick Date\tname\t...\nKL04\t1587Derwen\t295583-75917\t1/30/2026\tBytown Parts...\n"
)

st.markdown("### 📅 Date Format Handling")
date_option = st.selectbox(
    "How should 'Pick Date' be interpreted?",
    ["Auto-detect (recommended)", "MM/DD/YYYY", "YYYY-MM-DD", "Custom"],
    index=0
)

custom_fmt = ""
if date_option == "Custom":
    custom_fmt = st.text_input("Enter strftime format (e.g., %d/%m/%Y):", value="%m/%d/%Y")

if st.button("🚀 Convert to CSV"):
    if not raw_data.strip():
        st.warning("⚠️ Please paste your data.")
    else:
        fmt_hint = "auto"
        if date_option == "MM/DD/YYYY":
            fmt_hint = "MM/DD/YYYY"
        elif date_option == "YYYY-MM-DD":
            fmt_hint = "YYYY-MM-DD"
        elif date_option == "Custom":
            if not custom_fmt.strip():
                st.error("❌ Please enter a custom date format.")
                st.stop()
            fmt_hint = "custom"

        result_df = process_tsv(
            raw_data,
            date_format_hint=fmt_hint,
            custom_format=custom_fmt
        )

        if result_df is not None:
            csv_output = result_df.to_csv(index=False, header=False, encoding='cp1252').replace('\n', '\r\n')
            st.download_button(
                label="📥 Download CSV",
                data=csv_output,
                file_name="outbound_output.csv",
                mime="text/csv"
            )
