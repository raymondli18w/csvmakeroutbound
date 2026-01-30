import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="CSV Maker - Outbound", layout="wide")
st.title("📦 CSV Maker - Outbound")

# --- Helper: safe scalar extraction (defensive) ---
def safe_value(val):
    if pd.isna(val) or val == '' or val is None:
        return ''
    return str(val).strip()

# --- Load and process TSV ---
uploaded_file = st.file_uploader("Upload Outbound TSV File", type=["tsv", "txt"])

if uploaded_file:
    try:
        # Read TSV
        df = pd.read_csv(uploaded_file, sep='\t', dtype=str, on_bad_lines='warn')
        df.columns = df.columns.str.strip()
        
        # Validate required columns
        required = ['Reference', 'item', 'qty']
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"Missing columns: {missing}")
            st.stop()
        
        st.success(f"Loaded {len(df)} rows.")
        
        # --- Date format settings ---
        st.subheader("📅 Date Format (for 'Pick Date')")
        col1, col2 = st.columns(2)
        with col1:
            actual_format = st.selectbox(
                "Expected Format",
                ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"],
                index=0
            )
        with col2:
            custom_format = st.text_input("Custom Format (optional)", "")

        # Parse date if column exists
        if 'Pick Date' in df.columns:
            formats_to_try = [custom_format] if custom_format else []
            formats_to_try += ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]
            parsed = None
            for fmt in formats_to_try:
                try:
                    parsed = pd.to_datetime(df['Pick Date'], format=fmt, errors='coerce')
                    if parsed.notna().any():
                        break
                except:
                    continue
            if parsed is not None:
                df['Pick Date'] = parsed.dt.strftime('%m/%d/%Y')  # Normalize output

        # --- Make editable table ---
        st.subheader("✏️ Edit Rows (Reference | Item | Qty)")
        edited_rows = []
        for idx, row in df.iterrows():
            col_ref, col_item, col_qty = st.columns(3)
            ref_val = safe_value(row.get('Reference', ''))
            item_val = safe_value(row.get('item', ''))
            qty_val = safe_value(row.get('qty', ''))
            
            new_ref = col_ref.text_input(f"Ref {idx}", value=ref_val, key=f"ref_{idx}")
            new_item = col_item.text_input(f"Item {idx}", value=item_val, key=f"item_{idx}")
            new_qty = col_qty.text_input(f"Qty {idx}", value=qty_val, key=f"qty_{idx}")
            
            # Preserve other columns
            new_row = row.copy()
            new_row['Reference'] = new_ref
            new_row['item'] = new_item
            new_row['qty'] = new_qty
            edited_rows.append(new_row)

        edited_df = pd.DataFrame(edited_rows)

        # --- Final output ---
        st.subheader("📤 Download Processed Data")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Outbound')
        output.seek(0)
        
        st.download_button(
            "📥 Download Excel",
            data=output,
            file_name="outbound_edited.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)
