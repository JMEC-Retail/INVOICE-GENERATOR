from pydantic import BaseModel, Field
from typing import List
from datetime import date


class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float


class Invoice(BaseModel):
    customer_name: str
    customer_address: str
    invoice_date: date
    due_date: date
    line_items: List[LineItem]
    notes: str = ""


class InvoiceResponse(BaseModel):
    status: str = "success"
    invoice_id: str
    json_path: str
    pdf_path: str
