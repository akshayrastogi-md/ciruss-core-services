"""
Email Service for notifications
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict
from jinja2 import Template
from app.core.config import settings


class EmailService:
    """Email Service for sending transactional emails"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[Dict]] = None,
        is_html: bool = True,
    ) -> bool:
        """
        Send email via SMTP
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(attachment['content'])
                    part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=attachment['filename']
                    )
                    msg.attach(part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    async def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """Send email verification"""
        verification_url = f"https://app.d2canalytics.com/verify-email?token={verification_token}"

        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px 20px; background: #f9f9f9; }
                .button { display: inline-block; padding: 12px 30px; background: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to D2C Analytics!</h1>
                </div>
                <div class="content">
                    <p>Thank you for signing up. Please verify your email address to get started.</p>
                    <p style="text-align: center;">
                        <a href="{{ verification_url }}" class="button">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #666;">{{ verification_url }}</p>
                    <p>This link will expire in 24 hours.</p>
                </div>
                <div class="footer">
                    <p>If you didn't create an account, please ignore this email.</p>
                    <p>&copy; 2024 D2C Analytics. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html = Template(template).render(verification_url=verification_url)

        return await self.send_email(
            to_email=to_email,
            subject="Verify your email address",
            body=html,
            is_html=True,
        )

    async def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email"""
        reset_url = f"https://app.d2canalytics.com/reset-password?token={reset_token}"

        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px 20px; background: #f9f9f9; }
                .button { display: inline-block; padding: 12px 30px; background: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reset Your Password</h1>
                </div>
                <div class="content">
                    <p>We received a request to reset your password. Click the button below to reset it:</p>
                    <p style="text-align: center;">
                        <a href="{{ reset_url }}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #666;">{{ reset_url }}</p>
                    <p>This link will expire in 1 hour.</p>
                </div>
                <div class="footer">
                    <p>If you didn't request a password reset, please ignore this email.</p>
                    <p>&copy; 2024 D2C Analytics. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html = Template(template).render(reset_url=reset_url)

        return await self.send_email(
            to_email=to_email,
            subject="Reset your password",
            body=html,
            is_html=True,
        )

    async def send_invoice_email(
        self,
        to_email: str,
        customer_name: str,
        order_number: str,
        invoice_pdf: bytes,
        invoice_number: str,
    ) -> bool:
        """Send invoice via email"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px 20px; background: #f9f9f9; }
                .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Your Invoice</h1>
                </div>
                <div class="content">
                    <p>Dear {{ customer_name }},</p>
                    <p>Thank you for your order! Please find your invoice attached for order #{{ order_number }}.</p>
                    <p><strong>Invoice Number:</strong> {{ invoice_number }}</p>
                    <p>If you have any questions, please don't hesitate to contact us.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 D2C Analytics. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html = Template(template).render(
            customer_name=customer_name,
            order_number=order_number,
            invoice_number=invoice_number,
        )

        attachments = [
            {
                'content': invoice_pdf,
                'filename': f'Invoice_{invoice_number}.pdf',
            }
        ]

        return await self.send_email(
            to_email=to_email,
            subject=f"Invoice for Order #{order_number}",
            body=html,
            attachments=attachments,
            is_html=True,
        )

    async def send_stockout_alert(
        self,
        to_email: str,
        product_name: str,
        current_stock: int,
        days_until_stockout: int,
    ) -> bool:
        """Send stockout alert email"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #DC2626; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px 20px; background: #f9f9f9; }
                .alert { background: #FEE2E2; border-left: 4px solid #DC2626; padding: 15px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Stock Alert</h1>
                </div>
                <div class="content">
                    <div class="alert">
                        <h3>{{ product_name }}</h3>
                        <p><strong>Current Stock:</strong> {{ current_stock }} units</p>
                        <p><strong>Predicted Stockout:</strong> {{ days_until_stockout }} days</p>
                    </div>
                    <p>This product is predicted to run out of stock soon. Please place a reorder to avoid stockouts.</p>
                    <p>Log in to your dashboard for detailed forecasts and reorder recommendations.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 D2C Analytics. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html = Template(template).render(
            product_name=product_name,
            current_stock=current_stock,
            days_until_stockout=days_until_stockout,
        )

        severity = "CRITICAL" if days_until_stockout < 7 else "HIGH"

        return await self.send_email(
            to_email=to_email,
            subject=f"[{severity}] Stock Alert: {product_name}",
            body=html,
            is_html=True,
        )

    async def send_report_email(
        self,
        to_email: str,
        report_name: str,
        report_file: bytes,
        report_filename: str,
    ) -> bool:
        """Send scheduled report via email"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px 20px; background: #f9f9f9; }
                .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Your Scheduled Report</h1>
                </div>
                <div class="content">
                    <p>Your scheduled report "{{ report_name }}" is ready.</p>
                    <p>Please find the report attached to this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 D2C Analytics. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html = Template(template).render(report_name=report_name)

        attachments = [
            {
                'content': report_file,
                'filename': report_filename,
            }
        ]

        return await self.send_email(
            to_email=to_email,
            subject=f"Scheduled Report: {report_name}",
            body=html,
            attachments=attachments,
            is_html=True,
        )


# Global email service instance
email_service = EmailService()
