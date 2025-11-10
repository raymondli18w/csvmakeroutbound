import streamlit as st
from PIL import Image
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import pytesseract
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import barcode
from barcode.writer import ImageWriter

# --- Tesseract path ---
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\RaymondLi\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

st.set_page_config(page_title="Template Label Sheet Generator", layout="wide")
st.title("📦 Template Label Sheet Generator")

# --- Upload template image ---
uploaded_file = st.file_uploader("Upload label template image", type=["jpg","jpeg","png"])
if uploaded_file:
    template_img = Image.open(uploaded_file).convert("RGB")
    st.image(template_img, caption="Template Image", use_column_width=True)
    
    # Convert to OpenCV for detection
    img_cv = np.array(template_img)
    img_gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    
    # --- Detect barcode ---
    barcodes = decode(img_gray)
    detected_elements = []
    for barcode_obj in barcodes:
        x, y, w, h = barcode_obj.rect
        detected_elements.append(("Barcode", barcode_obj.data.decode("utf-8"), (x, y, w, h)))
    
    # --- Detect text ---
    ocr_data = pytesseract.image_to_data(img_gray, output_type=pytesseract.Output.DATAFRAME)
    ocr_data = ocr_data[ocr_data.conf > 50]
    for idx, row in ocr_data.iterrows():
        x, y, w, h, text = row['left'], row['top'], row['width'], row['height'], row['text']
        for _, _, (bx, by, bw, bh) in detected_elements:
            if y + h < by:
                detected_elements.append(("Item Number", text, (x, y, w, h)))
            elif y > by + bh:
                detected_elements.append(("Description", text, (x, y, w, h)))
    
    # --- Input fields ---
    st.subheader("Edit Label Fields")
    field_dict = {}
    for field_type in ["Item Number", "Barcode", "Description"]:
        texts = [t for t_type, t, _ in detected_elements if t_type==field_type]
        field_text = "\n".join(texts) if texts else ""
        user_input = st.text_area(f"{field_type}:", value=field_text)
        field_dict[field_type] = user_input.split("\n")
    
    # --- Align rows ---
    rows = list(zip(*field_dict.values()))
    st.subheader("Aligned Label Data")
    for row in rows:
        st.write(" | ".join(row))
    
    # --- Grid layout settings ---
    st.subheader("Label Sheet Settings")
    labels_per_row = st.number_input("Labels per row", min_value=1, max_value=10, value=2)
    labels_per_column = st.number_input("Labels per column", min_value=1, max_value=10, value=4)
    spacing = st.number_input("Spacing between labels (px)", min_value=0, max_value=100, value=10)

    # --- Generate PDF ---
    buffer = BytesIO()
    template_width, template_height = template_img.size
    page_width = labels_per_row * template_width + (labels_per_row-1)*spacing
    page_height = labels_per_column * template_height + (labels_per_column-1)*spacing
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    x_offsets = [i*(template_width + spacing) for i in range(labels_per_row)]
    y_offsets = [page_height - (i+1)*(template_height + spacing) + spacing for i in range(labels_per_column)]

    label_index = 0
    total_labels = len(rows)

    # --- Loop through grid positions without extra labels ---
    for y in y_offsets:
        for x in x_offsets:
            if label_index >= total_labels:
                break  # Stop generating extra labels
            row = rows[label_index]

            # Draw template image as background
            c.drawImage(ImageReader(template_img), x, y, width=template_width, height=template_height)

            # Overlay each element
            for field_type, _, (ex, ey, ew, eh) in detected_elements:
                if field_type == "Barcode":
                    if row[1].strip():  # Only generate barcode if non-empty
                        CODE128 = barcode.get_barcode_class('code128')
                        barcode_obj = CODE128(row[1], writer=ImageWriter())
                        barcode_buffer = BytesIO()
                        barcode_obj.write(barcode_buffer)
                        barcode_buffer.seek(0)
                        c.drawImage(ImageReader(barcode_buffer), x + ex, y + template_height - ey - eh, width=ew, height=eh)
                    else:
                        # Draw placeholder rectangle if barcode is missing
                        c.rect(x + ex, y + template_height - ey - eh, ew, eh, stroke=1, fill=0)
                elif field_type == "Item Number" and row[0].strip():
                    # Whiten old text area
                    c.setFillColorRGB(1,1,1)
                    c.rect(x + ex, y + template_height - ey - eh, ew, eh, fill=1, stroke=0)
                    # Draw new text
                    c.setFillColorRGB(0,0,0)
                    c.drawString(x + ex, y + template_height - ey - 10, row[0])
                elif field_type == "Description" and row[2].strip():
                    # Whiten old text area
                    c.setFillColorRGB(1,1,1)
                    c.rect(x + ex, y + template_height - ey - eh, ew, eh, fill=1, stroke=0)
                    # Draw new text
                    c.setFillColorRGB(0,0,0)
                    c.drawString(x + ex, y + template_height - ey - 10, row[2])

            label_index += 1

        if label_index >= total_labels:
            break  # Stop extra rows if finished

    c.showPage()
    c.save()
    buffer.seek(0)
    st.download_button("📄 Download Label Sheet PDF", data=buffer, file_name="label_sheet.pdf", mime="application/pdf")
