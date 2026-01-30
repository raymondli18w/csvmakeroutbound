import streamlit as st
import pandas as pd
from io import StringIO

# Exact column order from your data
COLUMNS = [
    'Client', 'WHSE', 'Reference', 'Pick Date', 'Ship From',
    'name', 'Street', 'City', 'Zip Code', 'Country',
    'item', 'qty', 'Customer PO'
]

st.set_page_config(page_title="Edit TSV → Export CSV", layout="wide")
st.title("📦 Paste & Edit Outbound Data")

# === TEXT AREA TO PASTE RAW TSV ===
raw_input = st.text_area(
    "📋 Paste your tab-separated data below (include header row):",
    height=250,
    value="""Client	WHSE	Reference	Pick Date	Ship From	name	Street	City	Zip Code	Country	item	qty	Customer PO
KL04	1587Derwen	295583-75917	1/30/2026	DEL-18W	Bytown Parts & Inductrial	1027 Chamberlin Avenue	Prince Rupert	V8J 4J5	CA	HF0480	42	16724
KL04	1587Derwen	295583-75917	1/30/2026	DEL-18W	Bytown Parts & Inductrial	1027 Chamberlin Avenue	Prince Rupert	V8J 4J5	CA	HF0280	6	16724"""
)

if st.button("✅ Parse and Edit"):
    if not raw_input.strip():
        st.warning("Please paste your data.")
    else:
        try:
            # Parse as TSV (auto-detect separator)
            df = pd.read_csv(StringIO(raw_input), sep='\t', dtype=str)
            df.columns = df.columns.str.strip()

            # Keep only known columns, add missing ones as empty
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            
            df = df[COLUMNS].fillna('').copy()
            st.success(f"✅ Loaded {len(df)} rows.")

            # === EDIT EACH ROW ===
            edited_rows = []
            for idx in range(len(df)):
                st.markdown(f"**Row {idx + 1}**")
                cols = st.columns(5)
                client = cols[0].text_input("Client", value=df.iloc[idx]['Client'], key=f"c_{idx}")
                whse = cols[1].text_input("WHSE", value=df.iloc[idx]['WHSE'], key=f"w_{idx}")
                ref = cols[2].text_input("Reference", value=df.iloc[idx]['Reference'], key=f"r_{idx}")
                pick_date = cols[3].text_input("Pick Date", value=df.iloc[idx]['Pick Date'], key=f"d_{idx}")
                ship_from = cols[4].text_input("Ship From", value=df.iloc[idx]['Ship From'], key=f"s_{idx}")

                addr_cols = st.columns(5)
                name = addr_cols[0].text_input("Name", value=df.iloc[idx]['name'], key=f"n_{idx}")
                street = addr_cols[1].text_input("Street", value=df.iloc[idx]['Street'], key=f"st_{idx}")
                city = addr_cols[2].text_input("City", value=df.iloc[idx]['City'], key=f"ci_{idx}")
                zipc = addr_cols[3].text_input("Zip Code", value=df.iloc[idx]['Zip Code'], key=f"z_{idx}")
                country = addr_cols[4].text_input("Country", value=df.iloc[idx]['Country'], key=f"co_{idx}")

                item_cols = st.columns(3)
                item = item_cols[0].text_input("Item", value=df.iloc[idx]['item'], key=f"i_{idx}")
                qty = item_cols[1].text_input("Qty", value=df.iloc[idx]['qty'], key=f"q_{idx}")
                po = item_cols[2].text_input("Customer PO", value=df.iloc[idx]['Customer PO'], key=f"po_{idx}")

                edited_rows.append({
                    'Client': client,
                    'WHSE': whse,
                    'Reference': ref,
                    'Pick Date': pick_date,
                    'Ship From': ship_from,
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

            # Convert to DataFrame
            edited_df = pd.DataFrame(edited_rows, columns=COLUMNS)

            # === DOWNLOAD AS STANDARD CSV (UTF-8, comma-separated) ===
            csv_buffer = StringIO()
            edited_df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_data = csv_buffer.getvalue()

            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="outbound_edited.csv",
                mime="text/csv"
            )
            st.success("✅ Ready to download!")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)
