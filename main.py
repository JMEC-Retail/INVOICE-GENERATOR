from fastapi import FastAPI, HTTPException
from models import Invoice, InvoiceResponse
from invoice_service import save_invoice_json, generate_pdf, load_invoice, list_invoices
import uuid

app = FastAPI()

@app.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(invoice: Invoice):
    invoice_id = str(uuid.uuid4())

    json_path = save_invoice_json(invoice.dict(), invoice_id)
    pdf_path = generate_pdf(invoice.dict(), invoice_id)

    return InvoiceResponse(
        invoice_id=invoice_id,
        json_path=json_path,
        pdf_path=pdf_path
    )

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
