import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io

# --- Page config ---
st.set_page_config(page_title="CSV Maker - Outbound", layout="wide")
st.title("📦 CSV Maker - Outbound")

# --- Helper: Safe value extraction ---
def safe_value(row, col):
    """Safely extract a scalar string from a DataFrame row."""
    if col not in row.index:
        return ''
    val = row[col]
    # Handle case where duplicate columns cause Series return
    if isinstance(val, pd.Series):
        val = val.dropna().iloc[0] if not val.dropna().empty else ''
    if pd.isna(val) or val == '' or val is None:
        return ''
    return str(val).strip()

# --- Address consistency check (updated to use 'Reference') ---
def check_address_consistency(df):
    """Validate and flag inconsistent addresses per Reference (order)."""
    df = df.copy()
    df['Address_Key'] = (
        df['name'].fillna('') + '|' +
        df['Street'].fillna('') + '|' +
        df['City'].fillna('') + '|' +
        df['Zip Code'].fillna('')
    )
    
    # Group by Reference and check for multiple Address_Keys
    ref_groups = df.groupby('Reference')['Address_Key'].nunique()
    inconsistent_refs = ref_groups[ref_groups > 1].index.tolist()
    
    df['Address_Inconsistent'] = df['Reference'].isin(inconsistent_refs)
    return df

# --- Date parsing with smart format detection ---
def parse_date_column(date_series, date_format_hint=None, custom_format=None):
    """Parse dates with fallback formats."""
    if custom_format:
        try:
            return pd.to_datetime(date_series, format=custom_format, errors='coerce')
        except Exception:
            pass
    
    # Try common formats
    formats = [
        '%m/%d/%Y',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m-%d-%Y',
        '%Y/%m/%d'
    ]
    
    if date_format_hint:
        formats = [date_format_hint] + [f for f in formats if f != date_format_hint]
    
    for fmt in formats:
        try:
            parsed = pd.to_datetime(date_series, format=fmt, errors='coerce')
            if parsed.notna().any():
                return parsed
        except Exception:
            continue
    
    # Final fallback: let pandas infer
    return pd.to_datetime(date_series, errors='coerce')

# --- Main processing function ---
def process_tsv(df, date_format_hint=None, custom_format=None):
    """Process raw TSV into clean outbound-ready format."""
    # Ensure column names are clean
    df.columns = df.columns.str.strip()
    
    # Required columns (based on your data)
    required_cols = [
        'Client', 'WHSE', 'Reference', 'Pick Date', 'Ship From',
        'name', 'Street', 'City', 'Zip Code', 'Country',
        'item', 'qty', 'Customer PO'
    ]
    
    # Check for missing columns
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()
    
    # Convert qty to numeric
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
    
    # Parse Pick Date
    df['Pick Date'] = parse_date_column(
        df['Pick Date'],
        date_format_hint=date_format_hint,
        custom_format=custom_format
    )
    
    # Validate mandatory fields
    if df['Pick Date'].isna().any():
        st.warning("Some rows have invalid 'Pick Date' — they will be excluded.")
        df = df.dropna(subset=['Pick Date']).copy()
    
    # Check address consistency
    df = check_address_consistency(df)
    
    # Add warning flags
    if df['Address_Inconsistent'].any():
        st.warning(f"⚠️ {df['Address_Inconsistent'].sum()} rows have inconsistent addresses per Reference.")
    
    return df

# --- File upload ---
uploaded_file = st.file_uploader("Upload Outbound TSV File", type=["tsv", "txt"])

if uploaded_file:
    try:
        # Read TSV correctly
        raw_data = pd.read_csv(
            uploaded_file,
            sep='\t',
            dtype=str,
            encoding='utf-8',
            on_bad_lines='warn'  # Skip malformed lines
        )
        
        st.success(f"✅ Loaded {len(raw_data)} rows with {len(raw_data.columns)} columns.")
        st.write("Detected columns:", list(raw_data.columns))
        
        # --- Date format options ---
        st.subheader("📅 Date Format Settings")
        col1, col2 = st.columns(2)
        with col1:
            actual_format = st.selectbox(
                "Detected/Expected Format",
                options=[
                    "%m/%d/%Y",
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%m-%d-%Y"
                ],
                index=0
            )
        with col2:
            custom_format = st.text_input("Custom Format (e.g., %d.%m.%Y)", value="")
        
        # --- Process data ---
        processed_df = process_tsv(
            raw_data,
            date_format_hint=actual_format,
            custom_format=custom_format if custom_format.strip() else None
        )
        
        # --- Display results ---
        st.subheader("📊 Processed Data Preview")
        st.dataframe(processed_df.head(20))
        
        # --- Download button ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            processed_df.to_excel(writer, index=False, sheet_name='Outbound')
        output.seek(0)
        
        st.download_button(
            label="📥 Download Processed Excel",
            data=output,
            file_name="outbound_processed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)
