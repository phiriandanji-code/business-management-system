
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from html import escape

from . import models
from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Sales and Receipts"])


# -----------------------------------------
# SALES HISTORY
# -----------------------------------------

@router.get("/businesses/{business_id}/sales")
def get_sales(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    sales = db.query(models.Sale).filter(
        models.Sale.business_id == business_id
    ).order_by(
        models.Sale.created_at.desc()
    ).all()

    results = []

    for sale in sales:
        items = db.query(models.SaleItem).filter(
            models.SaleItem.sale_id == sale.id
        ).all()

        results.append({
            "id": sale.id,
            "business_id": sale.business_id,
            "user_id": sale.user_id,
            "total_amount": sale.total_amount,
            "created_at": sale.created_at,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total
                }
                for item in items
            ]
        })

    return results


# -----------------------------------------
# PRINT SALES RECEIPT
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/sales/{sale_id}/print",
    response_class=HTMLResponse
)
def print_receipt(
    business_id: int,
    sale_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    sale = db.query(models.Sale).filter(
        models.Sale.id == sale_id,
        models.Sale.business_id == business_id
    ).first()

    if sale is None:
        raise HTTPException(
            status_code=404,
            detail="Sales transaction not found."
        )

    business = db.query(models.Business).filter(
        models.Business.id == business_id
    ).first()

    cashier = db.query(models.User).filter(
        models.User.id == sale.user_id
    ).first()

    items = db.query(models.SaleItem).filter(
        models.SaleItem.sale_id == sale.id
    ).all()

    business_name = escape(business.name)
    cashier_name = escape(
        cashier.full_name if cashier else "Unknown"
    )

    receipt_number = f"SALE-{sale.id:06d}"

    receipt_date = escape(str(sale.created_at))

    rows = ""

    for item in items:
        rows += f"""
        <tr>
            <td class="product-name">
                {escape(item.product_name)}
            </td>
            <td class="center">{item.quantity}</td>
            <td class="amount">
                MWK {item.unit_price:,.2f}
            </td>
            <td class="amount">
                MWK {item.line_total:,.2f}
            </td>
        </tr>
        """

    receipt_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>Receipt {receipt_number}</title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                background: #f1f5f9;
                margin: 0;
                padding: 35px 15px;
                color: #334155;
            }}

            .receipt {{
                max-width: 650px;
                margin: auto;
                background: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 30px rgba(15, 23, 42, 0.10);
            }}

            .receipt-header {{
                background: #102a43;
                color: #ffffff;
                padding: 35px 25px;
                text-align: center;
            }}

            .brand {{
                font-size: 32px;
                font-weight: 800;
                letter-spacing: 4px;
                margin-bottom: 10px;
            }}

            .business-name {{
                font-size: 17px;
                font-weight: 600;
                margin-bottom: 18px;
            }}

            .receipt-label {{
                display: inline-block;
                background: #16a085;
                color: #ffffff;
                padding: 8px 20px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 2px;
            }}

            .receipt-body {{
                padding: 30px;
            }}

            .section-title {{
                color: #102a43;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}

            .receipt-info {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                padding-bottom: 25px;
                border-bottom: 1px solid #e2e8f0;
            }}

            .info-label {{
                display: block;
                color: #94a3b8;
                font-size: 11px;
                text-transform: uppercase;
                margin-bottom: 6px;
            }}

            .info-value {{
                color: #102a43;
                font-size: 13px;
                font-weight: 600;
                overflow-wrap: anywhere;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 25px;
                font-size: 12px;
            }}

            th {{
                background: #edf3f8;
                color: #102a43;
                padding: 13px 8px;
                text-align: left;
                font-size: 11px;
                text-transform: uppercase;
            }}

            td {{
                padding: 15px 8px;
                border-bottom: 1px solid #edf1f5;
                vertical-align: middle;
            }}

            .center {{
                text-align: center;
            }}

            .amount {{
                text-align: right;
                white-space: nowrap;
            }}

            .product-name {{
                font-weight: 600;
                color: #334155;
            }}

            .total-panel {{
                background: #f0f8f6;
                border: 1px solid #d5eee7;
                border-radius: 10px;
                padding: 20px;
                margin-top: 25px;
            }}

            .total-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                color: #102a43;
                font-size: 17px;
                font-weight: bold;
            }}

            .total-amount {{
                color: #0f8b72;
                font-size: 21px;
                text-align: right;
            }}

            .receipt-footer {{
                background: #f8fafc;
                border-top: 1px solid #e2e8f0;
                text-align: center;
                padding: 25px;
            }}

            .thank-you {{
                color: #102a43;
                font-size: 17px;
                font-weight: bold;
                margin-bottom: 8px;
            }}

            .footer-note {{
                color: #64748b;
                font-size: 12px;
                line-height: 1.6;
            }}

            .print-button {{
                display: block;
                margin: 25px auto 0;
                background: #16a085;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 13px 30px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
            }}

            .print-button:hover {{
                background: #117a65;
            }}

            @media (max-width: 480px) {{
                .receipt-body {{
                    padding: 18px;
                }}

                .receipt-header {{
                    padding: 28px 15px;
                }}

                table {{
                    font-size: 10px;
                }}

                th, td {{
                    padding: 10px 4px;
                }}

                .total-amount {{
                    font-size: 17px;
                }}
            }}

            @media print {{
                @page {{
                    margin: 10mm;
                }}

                body {{
                    background: white;
                    padding: 0;
                }}

                .receipt {{
                    max-width: 100%;
                    box-shadow: none;
                    border-radius: 0;
                }}

                .print-button {{
                    display: none;
                }}

                .receipt-header,
                .receipt-label,
                .total-panel {{
                    print-color-adjust: exact;
                    -webkit-print-color-adjust: exact;
                }}
            }}
        </style>
    </head>

    <body>

        <div class="receipt">

            <div class="receipt-header">
                <div class="brand">KABOWA</div>

                <div class="business-name">
                    {business_name}
                </div>

                <span class="receipt-label">
                    SALES RECEIPT
                </span>
            </div>

            <div class="receipt-body">

                <div class="section-title">
                    Transaction Information
                </div>

                <div class="receipt-info">

                    <div>
                        <span class="info-label">
                            Receipt Number
                        </span>
                        <span class="info-value">
                            {receipt_number}
                        </span>
                    </div>

                    <div>
                        <span class="info-label">
                            Transaction Date
                        </span>
                        <span class="info-value">
                            {receipt_date}
                        </span>
                    </div>

                    <div>
                        <span class="info-label">
                            Cashier
                        </span>
                        <span class="info-value">
                            {cashier_name}
                        </span>
                    </div>

                    <div>
                        <span class="info-label">
                            Transaction Status
                        </span>
                        <span class="info-value">
                            COMPLETED
                        </span>
                    </div>

                </div>

                <div class="section-title" style="margin-top: 28px;">
                    Purchased Items
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th class="center">Qty</th>
                            <th style="text-align:right;">Price</th>
                            <th style="text-align:right;">Total</th>
                        </tr>
                    </thead>

                    <tbody>
                        {rows}
                    </tbody>
                </table>

                <div class="total-panel">
                    <div class="total-row">
                        <span>GRAND TOTAL</span>
                        <span class="total-amount">
                            MWK {sale.total_amount:,.2f}
                        </span>
                    </div>
                </div>

            </div>

            <div class="receipt-footer">
                <div class="thank-you">
                    Thank You for Shopping With Us!
                </div>

                <div class="footer-note">
                    We appreciate your business.<br>
                    Please keep this receipt for your records.<br>
                    Powered by KABOWA Business Management System
                </div>
            </div>

        </div>

        <button class="print-button" onclick="window.print()">
            Print Receipt
        </button>

    </body>
    </html>
    """

    return HTMLResponse(content=receipt_html)
