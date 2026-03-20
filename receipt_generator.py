import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from currency import get_symbol, CURRENCIES

OUTPUT_DIR = "receipts"


def generate_receipt(bill_no, customer_name, items, tax_rate=0.0, currency="USD"):
    """
    Generate a PDF receipt.

    Args:
        bill_no       (str)   : Unique bill number
        customer_name (str)   : Customer's name
        items         (list)  : List of dicts {name, qty, price}
        tax_rate      (float) : Tax percentage (e.g., 0.1 for 10%)
        currency      (str)   : Currency code (e.g., 'USD', 'EUR')

    Returns:
        tuple: (file_path, grand_total, items_with_subtotals)
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = os.path.join(OUTPUT_DIR, f"receipt_{bill_no}.pdf")
    
    symbol = get_symbol(currency)
    currency_name = CURRENCIES.get(currency, CURRENCIES["USD"])["name"]

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # ── Header ──────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=colors.HexColor("#2C3E50"),
        alignment=TA_CENTER, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=10, textColor=colors.grey,
        alignment=TA_CENTER
    )

    elements.append(Paragraph("🧾 BILL RECEIPT", title_style))
    elements.append(Paragraph("Your Company Name | contact@company.com | +1 234 567 890", sub_style))
    elements.append(Spacer(1, 0.5 * cm))

    # ── Bill Info ────────────────────────────────────────────
    info_data = [
        ["Bill No:", bill_no,      "Date:",     date_str],
        ["Customer:", customer_name, "Currency:", f"{currency} ({symbol})"],
        ["Status:", "✅ PAID", "", ""],
    ]
    info_table = Table(info_data, colWidths=[3 * cm, 6 * cm, 3 * cm, 5 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#2C3E50")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * cm))

    # ── Items Table ──────────────────────────────────────────
    table_data = [["#", "Item Name", "Qty", f"Unit Price ({symbol})", f"Subtotal ({symbol})"]]
    subtotal_total = 0.0

    for i, item in enumerate(items, start=1):
        subtotal = item["qty"] * item["price"]
        subtotal_total += subtotal
        item["subtotal"] = subtotal
        table_data.append([
            str(i),
            item["name"],
            str(item["qty"]),
            f"{symbol}{item['price']:.2f}",
            f"{symbol}{subtotal:.2f}"
        ])

    tax_amount = subtotal_total * tax_rate
    grand_total = subtotal_total + tax_amount

    # Totals rows
    table_data.append(["", "", "", "Subtotal:", f"{symbol}{subtotal_total:.2f}"])
    if tax_rate > 0:
        table_data.append(["", "", "", f"Tax ({tax_rate*100:.0f}%):", f"{symbol}{tax_amount:.2f}"])
    table_data.append(["", "", "", "TOTAL:", f"{symbol}{grand_total:.2f}"])

    item_table = Table(
        table_data,
        colWidths=[1 * cm, 8 * cm, 2 * cm, 3.5 * cm, 3.5 * cm]
    )
    item_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 11),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",        (1, 1), (1, -1), "LEFT"),
        # Data rows
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -4), [colors.whitesmoke, colors.white]),
        ("GRID",         (0, 0), (-1, -4), 0.5, colors.lightgrey),
        # Totals
        ("FONTNAME",     (3, -3), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE",    (3, -3), (-1, -3), 1, colors.HexColor("#2C3E50")),
        ("TEXTCOLOR",    (3, -1), (-1, -1), colors.HexColor("#E74C3C")),
        ("FONTSIZE",     (3, -1), (-1, -1), 12),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 1 * cm))

    # ── Footer ───────────────────────────────────────────────
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=9, textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("Thank you for your business! 🎉", footer_style))
    elements.append(Paragraph("This is a computer-generated receipt. No signature required.", footer_style))

    doc.build(elements)
    print(f"✅ Receipt saved: {file_path}")
    return file_path, grand_total, items