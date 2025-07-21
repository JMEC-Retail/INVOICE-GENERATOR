import os
import json
import uuid
from weasyprint import HTML

RAW_DIR = 'invoice_data/raw'
PDF_DIR = 'invoice_data/final'

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)


def save_invoice_json(invoice_data: dict, invoice_id: str) -> str:
    path = f"{RAW_DIR}/{invoice_id}.json"
    with open(path, 'w') as f:
        json.dump(invoice_data, f, indent=4, default=str)
    return path


def generate_pdf(invoice_data: dict, invoice_id: str) -> str:
    pdf_path = f"{PDF_DIR}/{invoice_id}.pdf"
    html_content = generate_html(invoice_data)
    HTML(string=html_content).write_pdf(pdf_path)
    return pdf_path


def generate_html(invoice: dict) -> str:
    items_html = "".join([
        f"<tr><td>{item['description']}</td><td>{item['quantity']}</td><td>${item['unit_price']:.2f}</td><td>${item['quantity'] * item['unit_price']:.2f}</td></tr>"
        for item in invoice["line_items"]
    ])
    total = sum(item['quantity'] * item['unit_price'] for item in invoice["line_items"])

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Invoice</h1>
        <p><strong>Customer:</strong> {invoice['customer_name']}<br>
        <strong>Address:</strong> {invoice['customer_address']}<br>
        <strong>Invoice Date:</strong> {invoice['invoice_date']}<br>
        <strong>Due Date:</strong> {invoice['due_date']}</p>

        <table>
            <thead>
                <tr><th>Description</th><th>Quantity</th><th>Unit Price</th><th>Total</th></tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
            <tfoot>
                <tr><td colspan="3"><strong>Grand Total</strong></td><td><strong>${total:.2f}</strong></td></tr>
            </tfoot>
        </table>

        <p>{invoice.get('notes', '')}</p>
    </body>
    </html>
    """
    return html


def load_invoice(invoice_id: str) -> dict:
    path = f"{RAW_DIR}/{invoice_id}.json"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def list_invoices() -> list:
    return [f.replace('.json', '') for f in os.listdir(RAW_DIR) if f.endswith('.json')]
