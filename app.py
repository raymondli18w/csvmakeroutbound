import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

# =========================
# Extended Column Synonyms Mapping
# =========================
COLUMN_SYNONYMS = {
    'Sales Order No.': [
        'sales order number', 'CUSTOMERNO', 'hdr', 'hdr ref', 'po ref', 'order',
        'header ref', 'po number', 'header reference', 'ref', 'reference', 'reference #', 'so no', 'ClientOrderNumber',
        'ship reference', 'ship to reference', 'po', 'order no', 'sales order', 'SO', 'SalesOrder'
    ],
    'Pick Date': [
        'pick date', 'date picked', 'ORDER_DATE', 'Sales Order Due Date', 'ship date', 'date ship', 'order date', 'date',
        'receipt date', 'date to ship', 'date shipped', 'ExpectedShipDate', 'pickdate', 'sales order date', 'Sales Order Date'
    ],
    'Item No.': [
        'item number', 'product', 'sku', 'ItemCode', 'item', 'product code', 'Item', 'product name', 'product id'
    ],
    'Each Qty': [
        'each qty', 'quantity', 'qty', 'OrderQuantity', 'Case Quantity', 'units', 'Case Quantity', 'Pallet Quantity', 'Qty', 'Order Qty'
    ],
    'WHSE': [
        'whse', 'warehouse', 'warehouse code', 'Warehouse', 'WH', 'Location'
    ],
    'Ship To': [
        'ship to', 'recipient', 'ship from', 'Shipping Addressee', 'SHIP_TO_NAME', 'ship to name', 'ShipToName',
        'consign', 'consign name', 'name', 'to', 'from', 'customer name', 'Shipping Address 1', 'Address Line 1', 'Addr1'
    ],
    'Ship To 2': [
        'ship to 2', 'recipient 2', 'ship from 2', 'SHIP_TO_NAME 2', 'ShipToCompany',
        'ship to name 2', 'consign 2', 'consign name 2', 'name 2', 'to 2', 'from 2', 'customer name 2', 'Shipping Address 2', 'Address Line 2', 'Addr2'
    ],
    'Ship To Code': [
        'ship to code', 'ship code', 'ship from code', 'congo ssd', 'consign code', 'shipto code', 'Customer Code'
    ],
    'Street': [
        'street', 'address', 'addr 1', 'Street Address', 'SHIP_TO_ADDR1', 'ShipToaddress1',
        'ShipToaddress2', 'address 1', 'ship to address 1', 'from address', 'ship from address',
        'ship to address', 'consign address', 'address line 1', 'Address'
    ],
    'City': [
        'city', 'town', 'county', 'SHIP_TO_CITY', 'Shipping City', 'ShipToCity', 'municipality', 'City Name'
    ],
    'state': [
        'state', 'province', 'SHIP_TO_STATE', 'Shipping State/Province', 'ShipToState', 'region', 'State', 'Prov'
    ],
    'Zip Code': [
        'zip code', 'zip', 'postal', 'Shipping Zip', 'ShipTodPostalCode', 'SHIP_TO_ZIP', 'postal code', 'postcode', 'Zip'
    ],
    'Country/Region': [
        'country/region', 'country', 'nation', 'Shipping Country', 'Country'
    ],
    'Customer PO': [
        'customer po', 'purchase order', 'Customer PO #', 'CustomerPO', 'po number', 'PO', 'PO#'
    ],
    'Ref 1': ['ref 1', 'reference 1', 'header ref 1', 'PICKTICKET', 'header reference 1', '3PL Reference ID'],
    'Ref 2': ['ref 2', 'reference 2', 'header ref 2', 'header reference 2', 'Pick ID'],
    'Ref 3': ['ref 3', 'reference 3', 'header ref 3', 'header reference 3'],
    'Pro Number': ['pro number', 'pro', 'tracking no', 'tracking', 'Tracking Number', 'PRO #'],
    'Carrier Code': ['carrier code', 'scac', 'CarrierSCAC', 'scac code', 'Carrier ID'],
    'Carrier Name': ['carrier', 'carrier name', 'scac name', 'truck', 'truck name', 'Shipping Carrier'],
    'CLIENT': ['client', 'customer id', 'depositor', 'agent', 'client code', 'Customer', 'Customer Name'],
    'Desc 2': ['desc 2', 'description 2', 'item name 2', 'item desc 2', 'Product Description', 'Description'],
    'Lot': ['lot', 'lot no', 'lot number', 'lot#', 'LOTNUMBER', 'keytrol', 'Batch No'],
    'Date2': [
        'date2', 'date 2', 'ship date 2', 'delivery date', 'delivery date 2',
        'expected delivery', 'delivery', 'date delivered', 'actual ship date'
    ]
}

# =========================
# Address Validation (optional if no country)
# =========================
CANADA_PROVINCES = ["AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"]
US_STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
             "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
             "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"]

def validate_address(row):
    country_raw = row.get("Country/Region", "")
    if pd.isna(country_raw) or str(country_raw).strip() == "":
        return "Valid"
    country = str(country_raw).strip().upper()
    province = str(row.get("state", "")).strip()
    postal = str(row.get("Zip Code", "")).strip().replace(" ", "")
    if country not in ["CA", "US"]:
        return "Invalid country"
    if country == "CA":
        if postal and len(postal) != 6:
            return "Invalid Canadian postal code"
        if province.upper() not in CANADA_PROVINCES:
            return "Invalid province"
    elif country == "US":
        if postal and not (len(postal) == 5 or len(postal) == 9):
            return "Invalid US ZIP code"
        if province.upper() not in US_STATES:
            return "Invalid state"
    return "Valid"

# =========================
# Flexible Date Parser → MM/DD/YYYY
# =========================
def parse_to_mm_dd_yyyy(date_input, format_hint="auto", custom_format=""):
    if pd.isna(date_input) or str(date_input).strip() == '':
        return None
    date_str = str(date_input).strip()

    # Extended format map including MON (e.g., DEC, JAN)
    format_map = {
        "MM/DD/YYYY": "%m/%d/%Y",
        "MM-DD-YYYY": "%m-%d-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
        "DD/MM/YYYY": "%d/%m/%Y",
        "DD-MM-YYYY": "%d-%m-%Y",
        "YYYY/MM/DD": "%Y/%m/%d",
        "MM/DD/YY": "%m/%d/%y",
        "YYYYMMDD": "%Y%m%d",
        "DD-MON-YYYY (e.g., 12-DEC-2025)": "%d-%b-%Y",
        "DD-MON-YY (e.g., 12-DEC-25)": "%d-%b-%y",
        "DDMONYYYY (e.g., 12DEC2025)": "%d%b%Y",
        "DDMONYY (e.g., 12DEC25)": "%d%b%y",
        "DD/MON/YYYY (e.g., 12/DEC/2025)": "%d/%b/%Y",
        "DD/MON/YY (e.g., 12/DEC/25)": "%d/%b/%y",
    }

    # Handle custom format
    if format_hint == "custom":
        try:
            dt = datetime.strptime(date_str, custom_format)
            return dt.strftime("%m/%d/%Y")
        except (ValueError, TypeError):
            return None

    # Handle explicit named formats from dropdown
    if format_hint in format_map:
        fmt = format_map[format_hint]
        try:
            dt = datetime.strptime(date_str, fmt)
            # Fix 2-digit year (e.g., 25 → 2025)
            if "%y" in fmt and dt.year < 1900:
                dt = dt.replace(year=dt.year + 100)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            return None

    # Auto-detect: try all common formats (including MON styles)
    if format_hint == "auto":
        auto_formats = [
            "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%m/%d/%y", "%Y%m%d",
            "%d-%b-%Y", "%d-%b-%y",
            "%d%b%Y", "%d%b%y",
            "%d/%b/%Y", "%d/%b/%y",
            "%d %b %Y", "%b %d, %Y",
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
    if pd.isna(val) or val == '' or val is None:
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
# Address Consistency Check
# =========================
def check_address_consistency(df):
    mismatch_flag = []
    addr_cols = ['Ship To', 'Ship To 2', 'Street', 'City', 'state', 'Zip Code', 'Country/Region']
    for _, row in df.iterrows():
        so_no = safe_value(row, 'Sales Order No.')
        if not so_no:
            mismatch_flag.append(False)
            continue
        same_so_rows = df[df['Sales Order No.'] == so_no]
        has_address_in_group = any(
            safe_value(r, 'Country/Region').strip() != ''
            for _, r in same_so_rows.iterrows()
        )
        if not has_address_in_group:
            mismatch_flag.append(False)
            continue
        current_addr = tuple(safe_value(row, col).strip() for col in addr_cols)
        mismatch = False
        for _, r in same_so_rows.iterrows():
            if safe_value(r, 'Country/Region').strip() != '':
                other_addr = tuple(safe_value(r, col).strip() for col in addr_cols)
                if other_addr != current_addr:
                    mismatch = True
                    break
        mismatch_flag.append(mismatch)
    df['Address_Mismatch'] = mismatch_flag
    return df

# =========================
# Main Processing Function
# =========================
def process_tsv(raw_text, date_format_hint="auto", custom_format=""):
    try:
        df = pd.read_csv(StringIO(raw_text), sep=None, engine='python', dtype=str, keep_default_na=False, na_values=[])
    except Exception as e:
        st.error(f"Error parsing data: {e}")
        return None

    df = standardize_headers(df)

    # Enforce required columns
    required_cols = ['Sales Order No.', 'Item No.', 'Each Qty', 'CLIENT', 'WHSE', 'Pick Date']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ''

    # Add optional columns (including Date2)
    optional_cols = [
        'Ship To', 'Ship To 2', 'Ship To Code', 'Street', 'City', 'state',
        'Zip Code', 'Country/Region', 'Customer PO', 'Ref 1', 'Ref 2', 'Ref 3',
        'Pro Number', 'Carrier Code', 'Carrier Name', 'Desc 2', 'Lot', 'Date2'
    ]
    for col in optional_cols:
        if col not in df.columns:
            df[col] = ''

    # Parse Pick Date
    if date_format_hint == "custom":
        df['Pick Date Clean'] = df['Pick Date'].apply(
            lambda x: parse_to_mm_dd_yyyy(x, format_hint="custom", custom_format=custom_format)
        )
    else:
        df['Pick Date Clean'] = df['Pick Date'].apply(
            lambda x: parse_to_mm_dd_yyyy(x, format_hint=date_format_hint)
        )

    # Parse Date2 using same logic
    if date_format_hint == "custom":
        df['Date2 Clean'] = df['Date2'].apply(
            lambda x: parse_to_mm_dd_yyyy(x, format_hint="custom", custom_format=custom_format)
        )
    else:
        df['Date2 Clean'] = df['Date2'].apply(
            lambda x: parse_to_mm_dd_yyyy(x, format_hint=date_format_hint)
        )

    # Warn on invalid Pick Dates
    invalid_dates = df['Pick Date Clean'].isna() & df['Pick Date'].notna()
    if invalid_dates.any():
        st.warning(f"⚠️ {invalid_dates.sum()} Pick Date(s) could not be parsed and will be skipped.")

    # Validate address
    df['Validation Status'] = df.apply(validate_address, axis=1)

    # Address consistency check
    df = check_address_consistency(df)
    if df['Address_Mismatch'].any():
        st.error("⚠️ Address mismatch detected for some Sales Order Numbers!")
        st.dataframe(df[df['Address_Mismatch']][
            ['Sales Order No.', 'Ship To', 'Ship To 2', 'Street', 'City', 'state', 'Zip Code', 'Country/Region']
        ])
        return None

    # Build output rows
    all_cols = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + [f"A{chr(i)}" for i in range(ord('A'), ord('Z') + 1)]
    output_rows = []

    for _, row in df.iterrows():
        so_val      = safe_value(row, 'Sales Order No.').strip()
        item_val    = safe_value(row, 'Item No.').strip()
        qty_val     = safe_value(row, 'Each Qty').strip()
        client_val  = safe_value(row, 'CLIENT').strip()
        whse_val    = safe_value(row, 'WHSE').strip()
        date_val    = row['Pick Date Clean']
        addr_valid  = (row['Validation Status'] == "Valid")

        valid = all([
            so_val != '',
            item_val != '',
            qty_val != '',
            client_val != '',
            whse_val != '',
            date_val is not None,
            addr_valid
        ])

        if valid:
            out_row = {col: '' for col in all_cols}
            out_row['A'] = 'BC'
            out_row['B'] = trim_text(client_val, 10)
            out_row['C'] = trim_text(so_val, 30)                                 # Sales Order No.
            out_row['D'] = trim_text(safe_value(row, 'Customer PO'), 30)         # Customer PO
            out_row['F'] = date_val  # MM/DD/YYYY
            out_row['H'] = trim_text(safe_value(row, 'Ship To Code'), 10)
            out_row['I'] = trim_text(safe_value(row, 'Ship To'), 45)
            out_row['J'] = trim_text(safe_value(row, 'Ship To 2'), 45)
            out_row['K'] = trim_text(safe_value(row, 'Street'), 30)
            out_row['L'] = trim_text(safe_value(row, 'Ship To Address 2'), 30)
            out_row['M'] = trim_text(safe_value(row, 'City'), 10)
            out_row['N'] = trim_text(safe_value(row, 'state'), 10)
            out_row['O'] = trim_text(safe_value(row, 'Zip Code'), 10)
            out_row['P'] = trim_text(safe_value(row, 'Country/Region'), 10)
            out_row['Q'] = trim_text(safe_value(row, 'Carrier Code'), 10)
            out_row['R'] = trim_text(safe_value(row, 'Carrier Name'), 20)
            out_row['T'] = trim_text(safe_value(row, 'Pro Number'), 20)
            out_row['U'] = trim_text(safe_value(row, 'Ref 1'), 30)
            out_row['V'] = trim_text(safe_value(row, 'Customer PO'), 30)         # D → V
            out_row['W'] = trim_text(safe_value(row, 'Ref 3'), 30)
            out_row['X'] = trim_text(item_val, 20)
            try:
                qty = int(float(qty_val)) if qty_val else 0
            except (ValueError, TypeError):
                qty = 0
            out_row['Y'] = qty
            out_row['AC'] = trim_text(safe_value(row, 'Desc 2'), 50)
            out_row['AD'] = trim_text(safe_value(row, 'Lot'), 20)
            out_row['AF'] = trim_text(safe_value(row, 'Customer PO'), 30)        # D → AF
            out_row['AG'] = trim_text(so_val, 30)                                # C → AG
            out_row['AJ'] = trim_text(whse_val, 10)
            # Date2 → AK
            date2_clean = row.get('Date2 Clean', None)
            out_row['AK'] = date2_clean if date2_clean is not None else ''
            output_rows.append(out_row)

    if not output_rows:
        st.warning("No valid rows found. Ensure all required fields are present and valid.")
        return None
    else:
        st.info(f"✅ Processed {len(output_rows)} valid row(s).")

    return pd.DataFrame(output_rows)

# =========================
# Streamlit UI
# =========================
st.title("TSV/CSV Converter (Extended & Robust)")
st.markdown("""
Paste your TSV or CSV data below.  
✅ **Required fields**: `Sales Order No.`, `Item No.`, `Each Qty`, `CLIENT`, `WHSE`, `Pick Date`  
✅ **Output date**: always `MM/DD/YYYY`  
✅ Supports dates like `12DEC2025`, `12-DEC-25`, etc.
""")

raw_data = st.text_area("Paste your data here:", height=300)

# Date format selector with MON support
st.markdown("### 📅 Date Format Handling")
date_format_option = st.selectbox(
    "How should dates in the 'Pick Date' column be interpreted?",
    options=[
        "Auto-detect (recommended)",
        "MM/DD/YYYY",
        "MM-DD-YYYY",
        "YYYY-MM-DD",
        "DD/MM/YYYY",
        "DD-MM-YYYY",
        "YYYY/MM/DD",
        "MM/DD/YY",
        "YYYYMMDD",
        "DD-MON-YYYY (e.g., 12-DEC-2025)",
        "DD-MON-YY (e.g., 12-DEC-25)",
        "DDMONYYYY (e.g., 12DEC2025)",
        "DDMONYY (e.g., 12DEC25)",
        "DD/MON/YYYY (e.g., 12/DEC/2025)",
        "DD/MON/YY (e.g., 12/DEC/25)",
        "Custom format (enter below)"
    ],
    index=0
)

custom_format = ""
if date_format_option == "Custom format (enter below)":
    custom_format = st.text_input("Enter Python strftime format (e.g., %d.%m.%Y):", value="%m/%d/%Y")

# Process button
if st.button("Generate CSV"):
    if not raw_data.strip():
        st.warning("Please paste your data.")
    else:
        if date_format_option == "Custom format (enter below)":
            if not custom_format.strip():
                st.error("Please enter a custom date format.")
                st.stop()
            actual_format = "custom"
        elif date_format_option == "Auto-detect (recommended)":
            actual_format = "auto"
        else:
            actual_format = date_format_option

        processed_df = process_tsv(
            raw_data,
            date_format_hint=actual_format,
            custom_format=custom_format
        )
        if processed_df is not None:
            csv_data = processed_df.to_csv(index=False, header=False, encoding='cp1252').replace('\n', '\r\n')
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="s_output_csv.csv",
                mime="text/csv"
            )
            st.success("✅ CSV generated successfully!")
