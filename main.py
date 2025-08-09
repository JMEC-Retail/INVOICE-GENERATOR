from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from models import InvoicePayload, InvoiceResponse
from invoice_service import (
    save_invoice_json, generate_pdf, load_invoice, list_invoices,
    create_download_token, validate_download_token, get_pdf_response
)
import uuid

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(body: dict = Body(...)):
    # Accept either { ...payload fields... } or { "payload": { ... } }
    invoice_dict = body.get("payload", body)

    # Validate/normalize with Pydantic (handles nullables now)
    invoice = InvoicePayload(**invoice_dict)

    # Honor incoming invoice_id, else generate
    invoice_id = invoice.invoice_id or str(uuid.uuid4())

    # Create signed token + link (48h)
    token = create_download_token(invoice_id)
    download_link = f"/download/{token}"

    # Generate PDF + save JSON (JSON will also include the download link)
    pdf_path = generate_pdf(invoice.dict(), invoice_id)
    json_path = save_invoice_json(invoice.dict(), invoice_id, download_link)

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
    return {"status": "success", "invoice_id": invoice_id, "data": data}


@app.get("/invoices")
async def get_all_invoices():
    ids = list_invoices()
    return {"status": "success", "count": len(ids), "invoice_ids": ids}


@app.get("/download/{token}")
async def download_invoice(token: str):
    invoice_id = validate_download_token(token)
    if not invoice_id:
        raise HTTPException(status_code=403, detail="Invalid or expired download link")
    pdf_response = get_pdf_response(invoice_id)
    if not pdf_response:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")
    return pdf_response
