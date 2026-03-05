import gradio as gr
import pdfplumber
import pandas as pd
import re


def extract_invoices(file):

    text = ""

    with pdfplumber.open(file.name) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    invoice_pattern = r'(?:Invoice\s*No|Invoice\s*Number|InvoiceNo|Inv\.?\s*No|Invoice\s*#|Bill\s*No|Bill\s*Number|Bill\s*of\s*Supply\s*No|Bill\s*of\s*Supply\s*Number)\s*[:#\-]?\s*([A-Za-z0-9\-\/]+)'

    invoice_matches = list(re.finditer(invoice_pattern, text, re.IGNORECASE))

    rows = []
    processed_invoices = set()

    for i, match in enumerate(invoice_matches):

        invoice_number = match.group(1)

        if not re.search(r'\d', invoice_number) or len(invoice_number) < 4:
            continue

        if invoice_number in processed_invoices:
            continue

        processed_invoices.add(invoice_number)

        start = match.start()

        if i + 1 < len(invoice_matches):
            end = invoice_matches[i + 1].start()
        else:
            end = len(text)

        block = text[start:end]

        # ---------------- DATE EXTRACTION ---------------- #

        date_pattern = r'(?:\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}|\d{4}[\/\-.]\d{1,2}[\/\-.]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{2,4})'

        # First try keyword-based extraction
        date_match = re.search(
            r'(Invoice\s*Date|Bill\s*Date|Date\s*of\s*Invoice)\s*[:\-]?\s*\n?\s*(' + date_pattern + ')',
            block,
            re.IGNORECASE
        )

        if date_match:
            invoice_date = date_match.group(2)

        else:
            # Fallback: first date found in the invoice block
            fallback_date = re.search(date_pattern, block, re.IGNORECASE)

            if fallback_date:
                invoice_date = fallback_date.group(0)
            else:
                invoice_date = ""

        # ---------------- FLOAT DETECTION ---------------- #

        float_pattern = r'(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})+(?:,\d{3}))\.\d{2}|\d+\.\d{2}'

        float_numbers = re.findall(float_pattern, block)

        float_numbers = [float(x.replace(",", "")) for x in float_numbers]

        total_amount = max(float_numbers) if float_numbers else ""

        row = {
            "Invoice Number": invoice_number,
            "Invoice Date": invoice_date,
            "Narration": "Invoice processed",
            "Debit Account": "Expense",
            "Credit Account": "Vendor",
            "Total Amount": total_amount
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    excel_file = "invoice_output.xlsx"
    df.to_excel(excel_file, index=False)

    return df, excel_file


with gr.Blocks() as demo:

    gr.Markdown("# Multiple Invoice PDF → Excel Extractor")

    file_input = gr.File(label="Upload Invoice PDF")

    extract_btn = gr.Button("Extract Invoices")

    output_table = gr.Dataframe(label="Extracted Invoice Data")

    download_file = gr.File(label="Download Excel")

    extract_btn.click(
        extract_invoices,
        inputs=file_input,
        outputs=[output_table, download_file]
    )

demo.launch(share=True)
