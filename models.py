from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class Money(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None


class OrderInfo(BaseModel):
    amazon_order_id: str
    purchase_date: datetime
    order_status: str
    fulfillment_channel: str
    sales_channel: str
    marketplace_id: str


class Buyer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class InvoicePayload(BaseModel):
    invoice_id: str
    currency: str
    order: OrderInfo
    buyer: Buyer
    shipping_address: Dict[str, Any] = {}
    items: List[Dict[str, Any]]              # keep flexible (SP-API varies)
    totals: Dict[str, Money]                 # items_subtotal/tax/shipping/discounts/grand_total
    seller: Dict[str, Any]
    notes: Optional[str] = ""
    generated_at: datetime


class InvoiceResponse(BaseModel):
    status: str = "success"
    invoice_id: str
    json_path: str
    pdf_path: str
    download_link: str
    valid_for_seconds: int
