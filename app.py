import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Editable Outbound TSV Processor", layout="wide")
st.title("📦 Editable Outbound TSV Processor")

# --- Upload ---
uploaded_file = st.file_uploader("Upload your TSV file", type=["tsv", "txt"])

if uploaded_file:
    try:
        # Read TSV
        df = pd.read_csv(uploaded_file, sep='\t', dtype=str, on_bad_lines='warn')
        df.columns = df.columns.str.strip()
        
        # Define expected columns (in order)
        expected_cols = [
            'Client', 'WHSE', 'Reference', 'Pick Date', 'Ship From',
            'name', 'Street', 'City', 'Zip Code', 'Country',
            'item', 'qty', 'Customer PO'
        ]
        
        # Validate columns
        missing = [col for col in expected_cols if col not in df.columns]
        if missing:
            st.error(f"❌ Missing columns: {missing}")
            st.write("Detected columns:", list(df.columns))
            st.stop()
        
        # Reorder and keep only needed columns
        df = df[expected_cols].copy()
        st.success(f"✅ Loaded {len(df)} rows.")

        # --- Date format options ---
        st.subheader("📅 Pick Date Format")
        col1, col2 = st.columns(2)
        with col1:
            actual_format = st.selectbox(
                "Expected Format",
                ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"],
                index=0,
                help="Used to parse and normalize dates"
            )
        with col2:
            custom_format = st.text_input("Custom Format (e.g., %d.%m.%Y)", "")

        # Parse and normalize Pick Date
        if 'Pick Date' in df.columns:
            date_series = df['Pick Date'].copy()
            formats_to_try = []
            if custom_format.strip():
                formats_to_try.append(custom_format.strip())
            formats_to_try.extend(["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"])
            
            parsed = None
            for fmt in formats_to_try:
                try:
                    temp = pd.to_datetime(date_series, format=fmt, errors='coerce')
                    if temp.notna().any():
                        parsed = temp
                        break
                except:
                    continue
            
            if parsed is not None:
                # Normalize to MM/DD/YYYY
                df['Pick Date'] = parsed.dt.strftime('%m/%d/%Y')
            else:
                st.warning("⚠️ Could not parse 'Pick Date' — keeping as-is.")

        # --- Editable table: one row at a time ---
        st.subheader("✏️ Edit Rows")
        edited_rows = []

        for idx in range(len(df)):
            st.markdown(f"**Row {idx + 1}**")
            cols = st.columns(5)  # Group logically
            
            # Row 1: Client, WHSE, Reference, Pick Date, Ship From
            client_val = cols[0].text_input("Client", value=str(df.iloc[idx]['Client']), key=f"client_{idx}")
            whse_val = cols[1].text_input("WHSE", value=str(df.iloc[idx]['WHSE']), key=f"whse_{idx}")
            ref_val = cols[2].text_input("Reference", value=str(df.iloc[idx]['Reference']), key=f"ref_{idx}")
            pick_date_val = cols[3].text_input("Pick Date", value=str(df.iloc[idx]['Pick Date']), key=f"pick_{idx}")
            ship_from_val = cols[4].text_input("Ship From", value=str(df.iloc[idx]['Ship From']), key=f"ship_{idx}")
            
            # Row 2: Name, Street, City, Zip, Country
            addr_cols = st.columns(5)
            name_val = addr_cols[0].text_input("Name", value=str(df.iloc[idx]['name']), key=f"name_{idx}")
            street_val = addr_cols[1].text_input("Street", value=str(df.iloc[idx]['Street']), key=f"street_{idx}")
            city_val = addr_cols[2].text_input("City", value=str(df.iloc[idx]['City']), key=f"city_{idx}")
            zip_val = addr_cols[3].text_input("Zip Code", value=str(df.iloc[idx]['Zip Code']), key=f"zip_{idx}")
            country_val = addr_cols[4].text_input("Country", value=str(df.iloc[idx]['Country']), key=f"country_{idx}")
            
            # Row 3: Item, Qty, Customer PO
            item_cols = st.columns(3)
            item_val = item_cols[0].text_input("Item", value=str(df.iloc[idx]['item']), key=f"item_{idx}")
            qty_val = item_cols[1].text_input("Qty", value=str(df.iloc[idx]['qty']), key=f"qty_{idx}")
            po_val = item_cols[2].text_input("Customer PO", value=str(df.iloc[idx]['Customer PO']), key=f"po_{idx}")
            
            # Build edited row
            edited_row = {
                'Client': client_val,
                'WHSE': whse_val,
                'Reference': ref_val,
                'Pick Date': pick_date_val,
                'Ship From': ship_from_val,
                'name': name_val,
                'Street': street_val,
                'City': city_val,
                'Zip Code': zip_val,
                'Country': country_val,
                'item': item_val,
                'qty': qty_val,
                'Customer PO': po_val
            }
            edited_rows.append(edited_row)
            st.divider()

        # Convert to DataFrame
        edited_df = pd.DataFrame(edited_rows, columns=expected_cols)

        # --- Download ---
        st.subheader("📥 Download Edited Data")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Outbound')
        output.seek(0)
        
        st.download_button(
            label="Download Excel File",
            data=output,
            file_name="outbound_edited.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)
