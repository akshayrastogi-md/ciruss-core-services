"""
GST Tax Calculation Service
"""
from typing import Dict, List, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.product import Product, HSNCode
from app.models.tenant import Tenant


class GSTCalculator:
    """GST Tax Calculation Service"""

    # State codes for GST
    STATE_CODES = {
        'Andhra Pradesh': '37',
        'Arunachal Pradesh': '12',
        'Assam': '18',
        'Bihar': '10',
        'Chhattisgarh': '22',
        'Goa': '30',
        'Gujarat': '24',
        'Haryana': '06',
        'Himachal Pradesh': '02',
        'Jharkhand': '20',
        'Karnataka': '29',
        'Kerala': '32',
        'Madhya Pradesh': '23',
        'Maharashtra': '27',
        'Manipur': '14',
        'Meghalaya': '17',
        'Mizoram': '15',
        'Nagaland': '13',
        'Odisha': '21',
        'Punjab': '03',
        'Rajasthan': '08',
        'Sikkim': '11',
        'Tamil Nadu': '33',
        'Telangana': '36',
        'Tripura': '16',
        'Uttar Pradesh': '09',
        'Uttarakhand': '05',
        'West Bengal': '19',
        'Delhi': '07',
        'Jammu and Kashmir': '01',
        'Ladakh': '38',
        'Puducherry': '34',
        'Chandigarh': '04',
        'Dadra and Nagar Haveli and Daman and Diu': '26',
        'Lakshadweep': '31',
        'Andaman and Nicobar Islands': '35',
    }

    async def calculate_gst(
        self,
        db: AsyncSession,
        tenant_id: int,
        product_id: int,
        quantity: int,
        unit_price: Decimal,
        billing_state: str,
        shipping_state: str,
    ) -> Dict:
        """
        Calculate GST for an order item
        """
        # Get product and HSN code
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            raise ValueError(f"Product not found: {product_id}")

        # Get HSN code
        hsn_code = None
        if product.hsn_code_id:
            result = await db.execute(
                select(HSNCode).where(HSNCode.id == product.hsn_code_id)
            )
            hsn_code = result.scalar_one_or_none()

        # Determine tax rate
        if hsn_code:
            cgst_rate = hsn_code.cgst_rate
            sgst_rate = hsn_code.sgst_rate
            igst_rate = hsn_code.igst_rate
        else:
            # Use product's tax rate
            total_rate = product.tax_rate
            cgst_rate = sgst_rate = total_rate / 2
            igst_rate = total_rate

        # Calculate base amount
        base_amount = unit_price * quantity

        # Determine if inter-state or intra-state
        is_interstate = self._is_interstate(billing_state, shipping_state)

        if is_interstate:
            # IGST applicable
            igst_amount = base_amount * (igst_rate / 100)
            cgst_amount = Decimal('0')
            sgst_amount = Decimal('0')
            total_tax = igst_amount
        else:
            # CGST + SGST applicable
            cgst_amount = base_amount * (cgst_rate / 100)
            sgst_amount = base_amount * (sgst_rate / 100)
            igst_amount = Decimal('0')
            total_tax = cgst_amount + sgst_amount

        return {
            'base_amount': float(base_amount),
            'cgst_rate': float(cgst_rate),
            'sgst_rate': float(sgst_rate),
            'igst_rate': float(igst_rate),
            'cgst_amount': float(cgst_amount),
            'sgst_amount': float(sgst_amount),
            'igst_amount': float(igst_amount),
            'total_tax': float(total_tax),
            'total_amount': float(base_amount + total_tax),
            'is_interstate': is_interstate,
            'hsn_code': hsn_code.code if hsn_code else None,
        }

    async def calculate_tcs(
        self,
        db: AsyncSession,
        tenant_id: int,
        gross_amount: Decimal,
        tcs_rate: Decimal = Decimal('1.0'),
    ) -> Dict:
        """
        Calculate TCS (Tax Collected at Source) for e-commerce
        Standard rate is 1% on gross amount
        """
        tcs_amount = gross_amount * (tcs_rate / 100)

        return {
            'gross_amount': float(gross_amount),
            'tcs_rate': float(tcs_rate),
            'tcs_amount': float(tcs_amount),
            'total_amount': float(gross_amount + tcs_amount),
        }

    def _is_interstate(self, billing_state: str, shipping_state: str) -> bool:
        """
        Determine if transaction is inter-state or intra-state
        """
        return billing_state.lower().strip() != shipping_state.lower().strip()

    def validate_gstin(self, gstin: str) -> Tuple[bool, str]:
        """
        Validate GSTIN format
        Format: 22AAAAA0000A1Z5
        - First 2 digits: State code
        - Next 10 characters: PAN
        - 13th character: Number of registrations in state
        - 14th character: Z (default)
        - 15th character: Checksum
        """
        if not gstin or len(gstin) != 15:
            return False, "GSTIN must be 15 characters"

        # Check state code
        state_code = gstin[:2]
        if not state_code.isdigit():
            return False, "First 2 characters must be state code (numeric)"

        # Check PAN format (next 10 characters)
        pan = gstin[2:12]
        if not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
            return False, "Invalid PAN format in GSTIN"

        # Check 13th character
        if not gstin[12].isalnum():
            return False, "13th character must be alphanumeric"

        # Check 14th character
        if gstin[13] != 'Z':
            return False, "14th character must be 'Z'"

        # Check 15th character (checksum)
        if not gstin[14].isalnum():
            return False, "15th character must be alphanumeric checksum"

        return True, "Valid GSTIN"
