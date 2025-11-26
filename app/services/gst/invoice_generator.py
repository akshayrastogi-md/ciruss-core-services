"""
GST Invoice Generation Service
"""
from datetime import datetime
from typing import Dict, Optional
from decimal import Decimal
from io import BytesIO
import boto3
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.order import Order
from app.models.tenant import Tenant
from app.core.config import settings


class InvoiceGenerator:
    """GST-compliant Invoice Generation Service"""

    async def generate_invoice(
        self,
        db: AsyncSession,
        order_id: int,
    ) -> str:
        """
        Generate GST-compliant invoice PDF for an order
        Returns S3 URL of the generated invoice
        """
        # Get order with all related data
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise ValueError(f"Order not found: {order_id}")

        # Get tenant
        result = await db.execute(
            select(Tenant).where(Tenant.id == order.tenant_id)
        )
        tenant = result.scalar_one_or_none()

        # Generate invoice number if not exists
        invoice_number = await self._generate_invoice_number(db, order)

        # Create PDF
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        # Title
        elements.append(Paragraph("TAX INVOICE", title_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Seller Details
        seller_data = [
            ["Sold By:", tenant.name],
            ["Address:", f"{tenant.address_line1}, {tenant.city}, {tenant.state} - {tenant.pincode}"],
            ["GSTIN:", tenant.gstin or "N/A"],
            ["PAN:", tenant.pan or "N/A"],
        ]
        seller_table = Table(seller_data, colWidths=[2 * inch, 4 * inch])
        seller_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(seller_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Invoice Details
        invoice_data = [
            ["Invoice Number:", invoice_number, "Invoice Date:", order.order_date.strftime('%d-%m-%Y')],
            ["Order Number:", order.order_number, "Order Date:", order.order_date.strftime('%d-%m-%Y')],
        ]
        invoice_table = Table(invoice_data, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 1.5 * inch])
        invoice_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('FONT', (2, 0), (2, -1), 'Helvetica-Bold', 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ]))
        elements.append(invoice_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Billing and Shipping Address
        address_data = [
            ["Billing Address", "Shipping Address"],
            [
                f"{order.customer_name}\n{order.billing_address_line1}\n{order.billing_city}, {order.billing_state}\n{order.billing_pincode}\nPhone: {order.customer_phone}",
                f"{order.customer_name}\n{order.shipping_address_line1}\n{order.shipping_city}, {order.shipping_state}\n{order.shipping_pincode}\nPhone: {order.customer_phone}"
            ],
        ]
        address_table = Table(address_data, colWidths=[3.5 * inch, 3.5 * inch])
        address_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(address_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Order Items
        items_header = [["#", "Item", "HSN", "Qty", "Price", "Tax", "Total"]]
        items_data = []

        for idx, item in enumerate(order.items, 1):
            items_data.append([
                str(idx),
                item.product_name,
                item.hsn_code or "-",
                str(item.quantity),
                f"₹{item.unit_price:.2f}",
                f"₹{item.tax_amount:.2f}",
                f"₹{item.total_amount:.2f}",
            ])

        items_table = Table(items_header + items_data, colWidths=[0.4*inch, 2.5*inch, 0.8*inch, 0.6*inch, 1*inch, 1*inch, 1.2*inch])
        items_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Tax Summary
        is_interstate = order.billing_state != order.shipping_state

        tax_summary = [
            ["Subtotal:", f"₹{order.subtotal:.2f}"],
            ["Discount:", f"₹{order.discount_amount:.2f}"],
        ]

        if is_interstate:
            tax_summary.append(["IGST:", f"₹{order.igst_amount:.2f}"])
        else:
            tax_summary.append(["CGST:", f"₹{order.cgst_amount:.2f}"])
            tax_summary.append(["SGST:", f"₹{order.sgst_amount:.2f}"])

        if order.tcs_amount > 0:
            tax_summary.append(["TCS (1%):", f"₹{order.tcs_amount:.2f}"])

        tax_summary.append(["Shipping:", f"₹{order.shipping_charges:.2f}"])
        tax_summary.append(["Total Amount:", f"₹{order.total_amount:.2f}"])

        tax_table = Table(tax_summary, colWidths=[5 * inch, 2 * inch])
        tax_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -2), 'Helvetica', 10),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 12),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(tax_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Payment Method
        payment_info = Paragraph(
            f"<b>Payment Method:</b> {order.payment_method.value.upper()}<br/>"
            f"<b>Payment Status:</b> {order.payment_status.upper()}",
            styles['Normal']
        )
        elements.append(payment_info)
        elements.append(Spacer(1, 0.3 * inch))

        # Footer
        footer_text = """
        <para align="center">
        <b>Declaration:</b><br/>
        We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.<br/>
        <br/>
        <b>Terms and Conditions:</b><br/>
        1. Goods once sold will not be taken back or exchanged<br/>
        2. All disputes are subject to jurisdiction only<br/>
        <br/>
        This is a computer-generated invoice and does not require a signature.
        </para>
        """
        footer = Paragraph(footer_text, styles['Normal'])
        elements.append(footer)

        # Build PDF
        doc.build(elements)

        # Upload to S3
        pdf_buffer.seek(0)
        invoice_url = await self._upload_to_s3(
            pdf_buffer,
            f"invoices/tenant_{order.tenant_id}/invoice_{invoice_number}.pdf"
        )

        return invoice_url

    async def _generate_invoice_number(self, db: AsyncSession, order: Order) -> str:
        """
        Generate unique invoice number
        Format: INV/YYYY-YY/NNNN
        """
        fiscal_year = self._get_fiscal_year(order.order_date)

        # Count invoices for this fiscal year
        result = await db.execute(
            select(func.count(Order.id))
            .where(
                and_(
                    Order.tenant_id == order.tenant_id,
                    Order.order_date >= datetime(fiscal_year, 4, 1),
                    Order.order_date < datetime(fiscal_year + 1, 4, 1),
                )
            )
        )
        count = result.scalar() + 1

        invoice_number = f"INV/{fiscal_year}-{str(fiscal_year + 1)[-2:]}/{count:04d}"
        return invoice_number

    def _get_fiscal_year(self, date: datetime) -> int:
        """Get fiscal year for a date (April to March)"""
        if date.month >= 4:
            return date.year
        else:
            return date.year - 1

    async def _upload_to_s3(self, file_buffer: BytesIO, key: str) -> str:
        """Upload file to S3 and return URL"""
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        s3_client.upload_fileobj(
            file_buffer,
            settings.AWS_S3_BUCKET,
            key,
            ExtraArgs={'ContentType': 'application/pdf'}
        )

        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
