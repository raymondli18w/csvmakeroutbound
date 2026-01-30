import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Paste TSV → Edit → Export", layout="wide")
st.title("📋 Paste TSV Data Below")

# === STEP 1: TEXT AREA TO PASTE RAW TSV ===
tsv_text = st.text_area(
    "Paste your tab-separated data here (include header row):",
    height=200,
    value="""Client	WHSE	Reference	Pick Date	Ship From	name	Street	City	Zip Code	Country	item	qty	Customer PO
KL04	1587Derwen	295583-75917	1/30/2026	DEL-18W	Bytown Parts & Inductrial	1027 Chamberlin Avenue	Prince Rupert	V8J 4J5	CA	HF0480	42	16724
KL04	1587Derwen	295583-75917	1/30/2026	DEL-18W	Bytown Parts & Inductrial	1027 Chamberlin Avenue	Prince Rupert	V8J 4J5	CA	HF0280	6	16724""",
    key="raw_tsv"
)

if st.button("✅ Parse & Edit Data"):
    if not tsv_text.strip():
        st.error("Please paste some TSV data first.")
    else:
        try:
            # Parse from text (using StringIO)
            from io import StringIO
            df = pd.read_csv(StringIO(tsv_text), sep='\t', dtype=str, on_bad_lines='warn')
            df.columns = df.columns.str.strip()
            
            expected_cols = [
                'Client', 'WHSE', 'Reference', 'Pick Date', 'Ship From',
                'name', 'Street', 'City', 'Zip Code', 'Country',
                'item', 'qty', 'Customer PO'
            ]
            
            missing = [c for c in expected_cols if c not in df.columns]
            if missing:
                st.error(f"Missing columns: {missing}")
                st.write("Detected columns:", list(df.columns))
                st.stop()
            
            df = df[expected_cols].copy()
            st.success(f"✅ Parsed {len(df)} rows.")

            # === STEP 2: EDITABLE ROWS ===
            st.subheader("✏️ Edit Rows")
            edited_rows = []

            for idx in range(len(df)):
                st.markdown(f"**Row {idx+1}**")
                cols = st.columns(5)
                client = cols[0].text_input("Client", value=df.iloc[idx]['Client'], key=f"c_{idx}")
                whse = cols[1].text_input("WHSE", value=df.iloc[idx]['WHSE'], key=f"w_{idx}")
                ref = cols[2].text_input("Reference", value=df.iloc[idx]['Reference'], key=f"r_{idx}")
                pick = cols[3].text_input("Pick Date", value=df.iloc[idx]['Pick Date'], key=f"p_{idx}")
                ship = cols[4].text_input("Ship From", value=df.iloc[idx]['Ship From'], key=f"s_{idx}")

                addr = st.columns(5)
                name = addr[0].text_input("Name", value=df.iloc[idx]['name'], key=f"n_{idx}")
                street = addr[1].text_input("Street", value=df.iloc[idx]['Street'], key=f"st_{idx}")
                city = addr[2].text_input("City", value=df.iloc[idx]['City'], key=f"ci_{idx}")
                zipc = addr[3].text_input("Zip Code", value=df.iloc[idx]['Zip Code'], key=f"z_{idx}")
                country = addr[4].text_input("Country", value=df.iloc[idx]['Country'], key=f"co_{idx}")

                item_qty_po = st.columns(3)
                item = item_qty_po[0].text_input("Item", value=df.iloc[idx]['item'], key=f"i_{idx}")
                qty = item_qty_po[1].text_input("Qty", value=df.iloc[idx]['qty'], key=f"q_{idx}")
                po = item_qty_po[2].text_input("Customer PO", value=df.iloc[idx]['Customer PO'], key=f"po_{idx}")

                edited_rows.append({
                    'Client': client,
                    'WHSE': whse,
                    'Reference': ref,
                    'Pick Date': pick,
                    'Ship From': ship,
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

            edited_df = pd.DataFrame(edited_rows, columns=expected_cols)

            # === STEP 3: DOWNLOAD ===
            st.subheader("📥 Download Edited Data")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                edited_df.to_excel(writer, index=False)
            output.seek(0)
            st.download_button(
                "Download Excel",
                data=output,
                file_name="edited_outbound.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Parsing error: {e}")
            st.exception(e)
