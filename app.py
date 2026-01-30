import streamlit as st
import pandas as pd
from io import StringIO

# =========================
# Column Synonyms (only what you need)
# =========================
COLUMN_SYNONYMS = {
    'Client': ['client', 'customer id', 'depositor', 'agent', 'client code', 'Customer'],
    'WHSE': ['whse', 'warehouse', 'warehouse code', 'Warehouse', 'WH', 'Location'],
    'Reference': ['reference', 'ref', 'sales order no.', 'so no', 'order', 'po', 'header ref', 'hdr'],
    'Pick Date': ['pick date', 'date picked', 'ship date', 'order date', 'date', 'receipt date'],
    'Ship From': ['ship from', 'from', 'shipping from'],
    'name': ['name', 'ship to', 'recipient', 'customer name', 'consign'],
    'Street': ['street', 'address', 'addr 1', 'address 1', 'ship to address'],
    'City': ['city', 'town', 'municipality'],
    'Zip Code': ['zip code', 'zip', 'postal', 'postcode'],
    'Country': ['country', 'country/region', 'nation'],
    'item': ['item', 'item no.', 'sku', 'product', 'item number'],
    'qty': ['qty', 'quantity', 'each qty', 'units', 'order qty'],
    'Customer PO': ['customer po', 'po number', 'purchase order', 'po']
}

# =========================
# Helper: Standardize headers
# =========================
def standardize_headers(df):
    col_map = {}
    for std_name, synonyms in COLUMN_SYNONYMS.items():
        for col in df.columns:
            if str(col).strip().lower() in [s.lower() for s in synonyms]:
                col_map[col] = std_name
                break
    df.rename(columns=col_map, inplace=True)
    return df

# =========================
# Streamlit App
# =========================
st.set_page_config(page_title="Paste TSV → Edit → ANSI CSV", layout="wide")
st.title("📦 Paste TSV Data → Edit → Download ANSI CSV")

# === TEXT AREA FOR PASTING DATA ===
raw_data = st.text_area(
    "📋 Paste your tab-separated data below (include header row):",
    height=200,
    value="""Client	WHSE	Reference	Pick Date	Ship From	name	Street	City	Zip Code	Country	item	qty	Customer PO
KL04	1587Derwen	295583-75917	1/30/2026	DEL-18W	Bytown Parts & Inductrial	1027 Chamberlin Avenue	Prince Rupert	V8J 4J5	CA	HF0480	42	16724"""
)

if st.button("✅ Parse and Edit"):
    if not raw_data.strip():
        st.error("Please paste some data.")
    else:
        try:
            # Parse TSV
            df = pd.read_csv(StringIO(raw_data), sep='\t', dtype=str, keep_default_na=False)
            df.columns = df.columns.str.strip()
            
            # Standardize column names
            df = standardize_headers(df)
            
            # Ensure all required columns exist
            required = list(COLUMN_SYNONYMS.keys())
            for col in required:
                if col not in df.columns:
                    df[col] = ''
            
            df = df[required].copy()
            st.success(f"✅ Loaded {len(df)} rows.")

            # === EDITABLE ROWS ===
            edited_rows = []
            for idx in range(len(df)):
                st.markdown(f"**Row {idx + 1}**")
                cols = st.columns(4)
                client = cols[0].text_input("Client", value=df.iloc[idx]['Client'], key=f"c_{idx}")
                whse = cols[1].text_input("WHSE", value=df.iloc[idx]['WHSE'], key=f"w_{idx}")
                ref = cols[2].text_input("Reference", value=df.iloc[idx]['Reference'], key=f"r_{idx}")
                pick_date = cols[3].text_input("Pick Date", value=df.iloc[idx]['Pick Date'], key=f"d_{idx}")

                addr_cols = st.columns(5)
                name = addr_cols[0].text_input("Name", value=df.iloc[idx]['name'], key=f"n_{idx}")
                street = addr_cols[1].text_input("Street", value=df.iloc[idx]['Street'], key=f"s_{idx}")
                city = addr_cols[2].text_input("City", value=df.iloc[idx]['City'], key=f"ci_{idx}")
                zipc = addr_cols[3].text_input("Zip Code", value=df.iloc[idx]['Zip Code'], key=f"z_{idx}")
                country = addr_cols[4].text_input("Country", value=df.iloc[idx]['Country'], key=f"co_{idx}")

                item_cols = st.columns(3)
                item = item_cols[0].text_input("Item", value=df.iloc[idx]['item'], key=f"i_{idx}")
                qty = item_cols[1].text_input("Qty", value=df.iloc[idx]['qty'], key=f"q_{idx}")
                po = item_cols[2].text_input("Customer PO", value=df.iloc[idx]['Customer PO'], key=f"p_{idx}")

                edited_rows.append({
                    'Client': client,
                    'WHSE': whse,
                    'Reference': ref,
                    'Pick Date': pick_date,
                    'Ship From': df.iloc[idx].get('Ship From', ''),  # not editable for brevity
                    'name': name,
                    'Street': street,
                    'City': city,
                    'Zip Code': zipc,
                    'Country': country,
                    'item': item,
                    'qty': qty,
                    'Customer PO': po
                })
                st.divider()

            edited_df = pd.DataFrame(edited_rows)

            # === DOWNLOAD AS ANSI CSV (cp1252) ===
            try:
                # Encode to Windows-1252 (ANSI)
                csv_buffer = StringIO()
                edited_df.to_csv(csv_buffer, index=False, sep=',', encoding='utf-8')
                csv_utf8 = csv_buffer.getvalue()
                csv_ansi = csv_utf8.encode('utf-8').decode('utf-8').encode('cp1252', errors='replace')
                
                st.download_button(
                    label="📥 Download ANSI CSV (cp1252)",
                    data=csv_ansi,
                    file_name="outbound_ansi.csv",
                    mime="text/csv"
                )
                st.success("✅ Ready to download!")
            except UnicodeEncodeError as e:
                st.warning("⚠️ Some characters can't be encoded in ANSI (cp1252). Replaced with '?'")
                # Fallback: use errors='replace'
                csv_utf8 = edited_df.to_csv(index=False, sep=',')
                csv_ansi = csv_utf8.encode('cp1252', errors='replace')
                st.download_button(
                    label="📥 Download ANSI CSV (with replacements)",
                    data=csv_ansi,
                    file_name="outbound_ansi.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)
