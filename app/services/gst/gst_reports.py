"""
GST Reports Generation Service
"""
from datetime import datetime, date
from typing import Dict, List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from io import BytesIO
import boto3

from app.models.order import Order, OrderItem
from app.models.tenant import Tenant
from app.core.config import settings


class GSTReportService:
    """GST Reports Generation Service"""

    async def generate_monthly_gst_report(
        self,
        db: AsyncSession,
        tenant_id: int,
        month: int,
        year: int,
        format: str = 'excel',
    ) -> str:
        """
        Generate monthly GST report
        Returns S3 URL of the generated report
        """
        # Get tenant
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        # Get orders for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        result = await db.execute(
            select(Order).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.order_date >= start_date,
                    Order.order_date < end_date,
                )
            )
        )
        orders = result.scalars().all()

        if format == 'excel':
            file_url = await self._generate_excel_report(
                tenant, orders, month, year
            )
        else:
            raise ValueError(f"Unsupported format: {format}")

        return file_url

    async def _generate_excel_report(
        self,
        tenant: Tenant,
        orders: List[Order],
        month: int,
        year: int,
    ) -> str:
        """Generate Excel format GST report"""
        wb = Workbook()

        # Remove default sheet
        wb.remove(wb.active)

        # Create sheets
        self._create_summary_sheet(wb, tenant, orders, month, year)
        self._create_order_wise_sheet(wb, orders)
        self._create_state_wise_sheet(wb, orders)
        self._create_hsn_wise_sheet(wb, orders)

        # Save to buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Upload to S3
        month_name = datetime(year, month, 1).strftime('%B')
        file_url = await self._upload_to_s3(
            buffer,
            f"gst_reports/tenant_{tenant.id}/GST_Report_{month_name}_{year}.xlsx"
        )

        return file_url

    def _create_summary_sheet(
        self,
        wb: Workbook,
        tenant: Tenant,
        orders: List[Order],
        month: int,
        year: int,
    ):
        """Create summary sheet"""
        ws = wb.create_sheet("Summary")

        # Header
        ws['A1'] = f"GST Summary Report - {datetime(year, month, 1).strftime('%B %Y')}"
        ws['A1'].font = Font(size=16, bold=True)
        ws.merge_cells('A1:D1')

        # Tenant info
        ws['A3'] = "Business Name:"
        ws['B3'] = tenant.name
        ws['A4'] = "GSTIN:"
        ws['B4'] = tenant.gstin or "N/A"

        # Calculate totals
        total_sales = sum(float(o.total_amount) for o in orders)
        total_cgst = sum(float(o.cgst_amount) for o in orders)
        total_sgst = sum(float(o.sgst_amount) for o in orders)
        total_igst = sum(float(o.igst_amount) for o in orders)
        total_tcs = sum(float(o.tcs_amount) for o in orders)

        # Summary data
        summary_data = [
            ["Metric", "Amount (₹)"],
            ["Total Sales", f"{total_sales:.2f}"],
            ["CGST", f"{total_cgst:.2f}"],
            ["SGST", f"{total_sgst:.2f}"],
            ["IGST", f"{total_igst:.2f}"],
            ["TCS (1%)", f"{total_tcs:.2f}"],
            ["Total Tax", f"{(total_cgst + total_sgst + total_igst):.2f}"],
        ]

        start_row = 6
        for idx, row in enumerate(summary_data):
            ws[f'A{start_row + idx}'] = row[0]
            ws[f'B{start_row + idx}'] = row[1]

        # Style header row
        for cell in ['A6', 'B6']:
            ws[cell].font = Font(bold=True)
            ws[cell].fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20

    def _create_order_wise_sheet(self, wb: Workbook, orders: List[Order]):
        """Create order-wise breakdown sheet"""
        ws = wb.create_sheet("Order-wise")

        # Headers
        headers = [
            "Order Date",
            "Order Number",
            "Customer Name",
            "State",
            "Subtotal",
            "CGST",
            "SGST",
            "IGST",
            "TCS",
            "Total",
        ]

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Data
        for row_idx, order in enumerate(orders, 2):
            ws.cell(row=row_idx, column=1, value=order.order_date.strftime('%d-%m-%Y'))
            ws.cell(row=row_idx, column=2, value=order.order_number)
            ws.cell(row=row_idx, column=3, value=order.customer_name)
            ws.cell(row=row_idx, column=4, value=order.shipping_state)
            ws.cell(row=row_idx, column=5, value=float(order.subtotal))
            ws.cell(row=row_idx, column=6, value=float(order.cgst_amount))
            ws.cell(row=row_idx, column=7, value=float(order.sgst_amount))
            ws.cell(row=row_idx, column=8, value=float(order.igst_amount))
            ws.cell(row=row_idx, column=9, value=float(order.tcs_amount))
            ws.cell(row=row_idx, column=10, value=float(order.total_amount))

        # Auto-fit columns
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 15

    def _create_state_wise_sheet(self, wb: Workbook, orders: List[Order]):
        """Create state-wise summary sheet"""
        ws = wb.create_sheet("State-wise")

        # Aggregate by state
        state_data = {}
        for order in orders:
            state = order.shipping_state
            if state not in state_data:
                state_data[state] = {
                    'orders': 0,
                    'subtotal': 0,
                    'cgst': 0,
                    'sgst': 0,
                    'igst': 0,
                    'total': 0,
                }

            state_data[state]['orders'] += 1
            state_data[state]['subtotal'] += float(order.subtotal)
            state_data[state]['cgst'] += float(order.cgst_amount)
            state_data[state]['sgst'] += float(order.sgst_amount)
            state_data[state]['igst'] += float(order.igst_amount)
            state_data[state]['total'] += float(order.total_amount)

        # Headers
        headers = ["State", "Orders", "Subtotal", "CGST", "SGST", "IGST", "Total"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Data
        for row_idx, (state, data) in enumerate(sorted(state_data.items()), 2):
            ws.cell(row=row_idx, column=1, value=state)
            ws.cell(row=row_idx, column=2, value=data['orders'])
            ws.cell(row=row_idx, column=3, value=data['subtotal'])
            ws.cell(row=row_idx, column=4, value=data['cgst'])
            ws.cell(row=row_idx, column=5, value=data['sgst'])
            ws.cell(row=row_idx, column=6, value=data['igst'])
            ws.cell(row=row_idx, column=7, value=data['total'])

        # Auto-fit columns
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 15

    def _create_hsn_wise_sheet(self, wb: Workbook, orders: List[Order]):
        """Create HSN-wise summary sheet"""
        ws = wb.create_sheet("HSN-wise")

        # Aggregate by HSN code
        hsn_data = {}
        for order in orders:
            for item in order.items:
                hsn = item.hsn_code or "N/A"
                if hsn not in hsn_data:
                    hsn_data[hsn] = {
                        'quantity': 0,
                        'taxable_value': 0,
                        'cgst': 0,
                        'sgst': 0,
                        'igst': 0,
                        'total': 0,
                    }

                taxable_value = float(item.unit_price) * item.quantity
                hsn_data[hsn]['quantity'] += item.quantity
                hsn_data[hsn]['taxable_value'] += taxable_value
                hsn_data[hsn]['cgst'] += float(item.cgst_amount)
                hsn_data[hsn]['sgst'] += float(item.sgst_amount)
                hsn_data[hsn]['igst'] += float(item.igst_amount)
                hsn_data[hsn]['total'] += float(item.total_amount)

        # Headers
        headers = ["HSN Code", "Quantity", "Taxable Value", "CGST", "SGST", "IGST", "Total"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Data
        for row_idx, (hsn, data) in enumerate(sorted(hsn_data.items()), 2):
            ws.cell(row=row_idx, column=1, value=hsn)
            ws.cell(row=row_idx, column=2, value=data['quantity'])
            ws.cell(row=row_idx, column=3, value=data['taxable_value'])
            ws.cell(row=row_idx, column=4, value=data['cgst'])
            ws.cell(row=row_idx, column=5, value=data['sgst'])
            ws.cell(row=row_idx, column=6, value=data['igst'])
            ws.cell(row=row_idx, column=7, value=data['total'])

        # Auto-fit columns
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 15

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
            ExtraArgs={'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
        )

        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
