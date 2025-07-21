from fastapi import FastAPI, HTTPException
from models import Invoice, InvoiceResponse
from invoice_service import (
    save_invoice_json, generate_pdf, load_invoice, list_invoices,
    create_download_token, validate_download_token, get_pdf_response
)
import uuid

app = FastAPI()

@app.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(invoice: Invoice):
    invoice_id = str(uuid.uuid4())

    json_path = save_invoice_json(invoice.dict(), invoice_id)
    pdf_path = generate_pdf(invoice.dict(), invoice_id)

    # Generate download link (token)
    token = create_download_token(invoice_id)
    download_link = f"/download/{token}"

    return {
        "status": "success",
        "invoice_id": invoice_id,
        "json_path": json_path,
        "pdf_path": pdf_path,
        "download_link": download_link,
        "valid_for_seconds": 48 * 60 * 60
    }

@app.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str):
    data = load_invoice(invoice_id)
    if not data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        "status": "success",
        "invoice_id": invoice_id,
        "data": data
    }

@app.get("/invoices")
async def get_all_invoices():
    ids = list_invoices()
    return {
        "status": "success",
        "count": len(ids),
        "invoice_ids": ids
    }

@app.get("/download/{token}")
async def download_invoice(token: str):
    invoice_id = validate_download_token(token)
    if not invoice_id:
        raise HTTPException(status_code=403, detail="Invalid or expired download link")
    pdf_response = get_pdf_response(invoice_id)
    if not pdf_response:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")
    return pdf_response
