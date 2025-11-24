import streamlit as st
import pandas as pd
from io import StringIO

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
    'Lot': ['lot', 'lot no', 'lot number', 'lot#', 'LOTNUMBER', 'keytrol', 'Batch No']
}

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
                break  # avoid multiple renames
    df.rename(columns=mapping, inplace=True)
    return df

# Note: fill_blank_rows is disabled — address is optional; avoid unintended propagation
# def fill_blank_rows(df): ... [REMOVED]

# =========================
# Address Consistency Check (address optional)
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

        # Only proceed if at least one row in the group has Country/Region (i.e., address is intended)
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
# Main TSV/CSV Processing
# =========================
def process_tsv(raw_text):
    try:
        # Auto-detect delimiter
        df = pd.read_csv(StringIO(raw_text), sep=None, engine='python', dtype=str, keep_default_na=False, na_values=[])
    except Exception as e:
        st.error(f"Error parsing data: {e}")
        return None

    df = standardize_headers(df)

    # Ensure all expected columns exist
    expected_cols = [
        'Sales Order No.', 'Item No.', 'Each Qty', 'Pick Date', 'CLIENT', 'WHSE',
        'Ship To', 'Ship To 2', 'Ship To Code', 'Street', 'City', 'state',
        'Zip Code', 'Country/Region', 'Customer PO', 'Ref 1', 'Ref 2', 'Ref 3',
        'Pro Number', 'Carrier Code', 'Carrier Name', 'Desc 2', 'Lot'
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''

    # Parse and format Pick Date
    if 'Pick Date' in df.columns and not df['Pick Date'].isnull().all():
        # Treat empty strings as NaT
        temp_dates = pd.to_datetime(df['Pick Date'].replace('', pd.NaT), errors='coerce')
        valid_mask = (
            temp_dates.notna() &
            (temp_dates.dt.year >= 1900) &
            (temp_dates.dt.year <= 2030)
        )
        df['Pick Date'] = ''
        df.loc[valid_mask, 'Pick Date'] = temp_dates[valid_mask].dt.strftime('%m/%d/%Y')
        invalid_count = (~valid_mask).sum()
        if invalid_count > 0:
            st.warning(f"⚠️ {invalid_count} Pick Date(s) were invalid or outside 1900–2030 and were cleared.")
    else:
        df['Pick Date'] = ''

    # Consistency check (now safe for optional address)
    df = check_address_consistency(df)
    if df['Address_Mismatch'].any():
        st.error("⚠️ Address mismatch detected! Some Sales Order Numbers have conflicting addresses.")
        st.dataframe(
            df[df['Address_Mismatch']][
                ['Sales Order No.', 'Ship To', 'Ship To 2', 'Street', 'City', 'state', 'Zip Code', 'Country/Region']
            ]
        )
        return None

    # Build output
    all_cols = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + [f"A{chr(i)}" for i in range(ord('A'), ord('Z') + 1)]
    output_rows = []

    for _, row in df.iterrows():
        so_val = safe_value(row, 'Sales Order No.').strip()
        item_val = safe_value(row, 'Item No.').strip()
        if so_val and item_val:
            out_row = {col: '' for col in all_cols}
            out_row['A'] = 'BC'
            out_row['B'] = trim_text(safe_value(row, 'CLIENT'), 10)
            out_row['C'] = trim_text(so_val, 30)
            out_row['D'] = trim_text(safe_value(row, 'Customer PO'), 30)
            out_row['F'] = safe_value(row, 'Pick Date')  # Note: E is skipped (was for Qty in older formats)
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
            out_row['V'] = trim_text(safe_value(row, 'Ref 2'), 30)
            out_row['W'] = trim_text(safe_value(row, 'Ref 3'), 30)
            out_row['X'] = trim_text(item_val, 20)
            qty_raw = safe_value(row, 'Each Qty')
            try:
                qty = int(float(qty_raw)) if qty_raw.strip() else 0
            except (ValueError, TypeError):
                qty = 0
            out_row['Y'] = qty
            out_row['AC'] = trim_text(safe_value(row, 'Desc 2'), 50)
            out_row['AD'] = trim_text(safe_value(row, 'Lot'), 20)
            out_row['AJ'] = trim_text(safe_value(row, 'WHSE'), 10)
            output_rows.append(out_row)

    if not output_rows:
        st.warning("No valid rows found to process. Ensure 'Sales Order No.' and 'Item No.' are present.")
        return None

    return pd.DataFrame(output_rows)

# =========================
# Streamlit UI
# =========================
st.title("TSV/CSV Converter (Extended & Robust)")
st.markdown("""
Paste your TSV or CSV data below.  
✅ **Only `Sales Order No.` and `Item No.` are required**  
✅ All other fields (address, carrier, date, lot, etc.) are **optional**  
✅ Automatically handles mixed formats and common column names
""")

raw_data = st.text_area("Paste your data here:", height=300)

if st.button("Generate CSV"):
    if not raw_data.strip():
        st.warning("Please paste your data.")
    else:
        processed_df = process_tsv(raw_data)
        if processed_df is not None:
            csv_data = processed_df.to_csv(index=False, header=False, encoding='cp1252').replace('\n', '\r\n')
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="s_output_csv.csv",
                mime="text/csv"
            )
            st.success("✅ CSV generated successfully!")
