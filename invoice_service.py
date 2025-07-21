import os
import json
import time
import uuid
from weasyprint import HTML

from fastapi.responses import FileResponse, Response

RAW_DIR = 'invoice_data/raw'
PDF_DIR = 'invoice_data/final'
TEMPLATE_PATH = 'invoice_template/modern_invoice.html'

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# In-memory download token store: {token: (invoice_id, expiry_time)}
download_tokens = {}


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
    with open(TEMPLATE_PATH) as file:
        template = file.read()

    items_html = "".join([
        f"<tr><td>{item['description']}</td><td>{item['quantity']}</td><td>${item['unit_price']:.2f}</td><td>${item['quantity'] * item['unit_price']:.2f}</td></tr>"
        for item in invoice["line_items"]
    ])
    total = sum(item['quantity'] * item['unit_price'] for item in invoice["line_items"])

    html = template.format(
        company_info=invoice["company_info"],
        customer_name=invoice["customer_name"],
        customer_address=invoice["customer_address"],
        invoice_date=invoice["invoice_date"],
        due_date=invoice["due_date"],
        line_items=items_html,
        total=f"${total:.2f}",
        notes=invoice.get("notes", "")
    )
    return html

def create_download_token(invoice_id: str) -> str:
    token = str(uuid.uuid4())
    expiry = time.time() + (48 * 60 * 60)  # 48 hours from now
    download_tokens[token] = (invoice_id, expiry)
    return token

def validate_download_token(token: str) -> str:
    token_data = download_tokens.get(token)
    if not token_data:
        return None
    invoice_id, expiry = token_data
    if time.time() > expiry:
        # Token expired, cleanup
        download_tokens.pop(token, None)
        return None
    return invoice_id

def get_pdf_response(invoice_id: str):
    pdf_path = f"{PDF_DIR}/{invoice_id}.pdf"
    if not os.path.exists(pdf_path):
        return None
    
    headers = {
        "Content-Disposition": f'inline; filename="invoice_{invoice_id}.pdf"'
    }
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"invoice_{invoice_id}.pdf",
        headers=headers
    )

def load_invoice(invoice_id: str) -> dict:
    path = f"{RAW_DIR}/{invoice_id}.json"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def list_invoices() -> list:
    return [f.replace('.json', '') for f in os.listdir(RAW_DIR) if f.endswith('.json')]
