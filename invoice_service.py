import os
import json
import time
import uuid
from typing import Any, Dict, Optional

from weasyprint import HTML
from fastapi.responses import FileResponse

RAW_DIR = 'invoice_data/raw'
PDF_DIR = 'invoice_data/final'
TEMPLATE_PATH = 'invoice_template/amazon_invoice.html'

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# In-memory download token store: {token: (invoice_id, expiry_time)}
download_tokens: Dict[str, Any] = {}


def _currency(inv: Dict[str, Any]) -> str:
    return inv.get("currency") or "AUD"


def _fmt_money(amount: Optional[float], currency: Optional[str], fallback_currency: str) -> str:
    try:
        amt = float(amount) if amount is not None else 0.0
    except (ValueError, TypeError):
        amt = 0.0
    cur = currency or fallback_currency
    return f"{cur} {amt:.2f}"


def _get_item_unit_price(item: Dict[str, Any]) -> Optional[float]:
    # Try prices.item_price.amount
    return (
        item.get("prices", {})
            .get("item_price", {})
            .get("amount")
    )


def _get_item_total(item: Dict[str, Any]) -> Optional[float]:
    # Prefer line_totals.subtotal.amount if present
    lt = item.get("line_totals", {})
    subtotal = (lt.get("subtotal") or {}).get("amount")
    if subtotal is not None:
        return subtotal
    # Fallback: qty * unit
    qty = item.get("quantity") or 0
    unit = _get_item_unit_price(item) or 0.0
    return qty * unit


def format_address(addr: Dict[str, Any]) -> str:
    # Accepts Amazon-like flexible dict or your seller address dict
    if not addr:
        return ""
    parts = [
        addr.get("Name") or addr.get("name") or "",
        addr.get("AddressLine1") or addr.get("line1") or "",
        addr.get("AddressLine2") or addr.get("line2") or "",
        addr.get("City") or addr.get("city") or "",
        addr.get("StateOrRegion") or addr.get("state") or "",
        addr.get("PostalCode") or addr.get("postcode") or "",
        addr.get("CountryCode") or addr.get("country") or "",
    ]
    return "<br>".join([p for p in parts if p])


def save_invoice_json(invoice_data: dict, invoice_id: str, download_link: str) -> str:
    invoice_data["download_link"] = download_link
    path = f"{RAW_DIR}/{invoice_id}.json"
    with open(path, 'w') as f:
        json.dump(invoice_data, f, indent=4, default=str)
    return path


def generate_pdf(invoice_data: dict, invoice_id: str) -> str:
    with open(TEMPLATE_PATH, encoding="utf-8") as file:
        template = file.read()

    cur = _currency(invoice_data)

    # Items HTML
    rows = []
    for it in invoice_data.get("items", []):
        title = it.get("title") or it.get("description") or ""
        qty = it.get("quantity") or 0

        unit_amt = _get_item_unit_price(it)
        unit_cur = (it.get("prices", {}).get("item_price", {}) or {}).get("currency")
        unit_disp = _fmt_money(unit_amt, unit_cur, cur)

        total_amt = _get_item_total(it)
        # total currency: try line_totals.subtotal.currency → fallback to top-level
        total_cur = ((it.get("line_totals", {}) or {}).get("subtotal", {}) or {}).get("currency")
        total_disp = _fmt_money(total_amt, total_cur, cur)

        rows.append(
            f"<tr>"
            f"<td>{title}</td>"
            f"<td>{qty}</td>"
            f"<td>{unit_disp}</td>"
            f"<td>{total_disp}</td>"
            f"</tr>"
        )
    items_html = "".join(rows)

    # Totals (use top-level currency when nested currency is null)
    totals = invoice_data.get("totals", {})
    subtotal = totals.get("items_subtotal", {})
    tax = totals.get("tax", {})
    shipping = totals.get("shipping", {})
    discounts = totals.get("discounts", {})
    grand_total = totals.get("grand_total", {})

    subtotal_disp  = _fmt_money(subtotal.get("amount"),  subtotal.get("currency"),  cur)
    tax_disp       = _fmt_money(tax.get("amount"),       tax.get("currency"),       cur)
    shipping_disp  = _fmt_money(shipping.get("amount"),  shipping.get("currency"),  cur)
    discounts_disp = _fmt_money(discounts.get("amount"), discounts.get("currency"), cur)
    grand_disp     = _fmt_money(grand_total.get("amount"), grand_total.get("currency"), cur)

    buyer = invoice_data.get("buyer", {})
    buyer_name = buyer.get("name") or ""
    buyer_email = buyer.get("email") or ""

    html_content = template.format(
        invoice_id=invoice_data.get("invoice_id", invoice_id),
        amazon_order_id=invoice_data.get("order", {}).get("amazon_order_id", ""),
        purchase_date=invoice_data.get("order", {}).get("purchase_date", ""),
        order_status=invoice_data.get("order", {}).get("order_status", ""),
        fulfillment_channel=invoice_data.get("order", {}).get("fulfillment_channel", ""),
        sales_channel=invoice_data.get("order", {}).get("sales_channel", ""),
        marketplace_id=invoice_data.get("order", {}).get("marketplace_id", ""),

        buyer_name=buyer_name,
        buyer_email=buyer_email,

        shipping_address=format_address(invoice_data.get("shipping_address", {})),
        line_items=items_html,

        subtotal=subtotal_disp,
        tax=tax_disp,
        shipping=shipping_disp,
        discounts=discounts_disp,
        grand_total=grand_disp,

        seller_name=invoice_data.get("seller", {}).get("company", "")
                    or invoice_data.get("seller", {}).get("name", ""),
        seller_info="",  # keep placeholder if you want to expand in template
        notes=invoice_data.get("notes", "") or "",
        generated_at=invoice_data.get("generated_at", ""),
        currency=cur,
    )

    pdf_path = f"{PDF_DIR}/{invoice_id}.pdf"
    HTML(string=html_content).write_pdf(pdf_path)
    return pdf_path


def create_download_token(invoice_id: str) -> str:
    token = str(uuid.uuid4())
    expiry = time.time() + (48 * 60 * 60)  # 48 hours
    download_tokens[token] = (invoice_id, expiry)
    return token


def validate_download_token(token: str) -> Optional[str]:
    token_data = download_tokens.get(token)
    if not token_data:
        return None
    invoice_id, expiry = token_data
    if time.time() > expiry:
        download_tokens.pop(token, None)
        return None
    return invoice_id


def get_pdf_response(invoice_id: str):
    pdf_path = f"{PDF_DIR}/{invoice_id}.pdf"
    if not os.path.exists(pdf_path):
        return None
    headers = {"Content-Disposition": f'inline; filename="invoice_{invoice_id}.pdf"'}
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"invoice_{invoice_id}.pdf", headers=headers)


def load_invoice(invoice_id: str) -> Optional[dict]:
    path = f"{RAW_DIR}/{invoice_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_invoices() -> list:
    return [f.replace('.json', '') for f in os.listdir(RAW_DIR) if f.endswith('.json')]
