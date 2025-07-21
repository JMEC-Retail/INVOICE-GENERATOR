import os
import json
import uuid
from json2pdf import convert

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
    convert(
        data=invoice_data,
        output=pdf_path,
        options={
            "title": f"Invoice {invoice_id}",
            "font_size": 12,
            "page_size": "A4"
        }
    )
    return pdf_path


def load_invoice(invoice_id: str) -> dict:
    path = f"{RAW_DIR}/{invoice_id}.json"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def list_invoices() -> list:
    return [f.replace('.json', '') for f in os.listdir(RAW_DIR) if f.endswith('.json')]
