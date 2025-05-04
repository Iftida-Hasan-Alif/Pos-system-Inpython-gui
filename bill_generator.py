import logging
import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
import webbrowser
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        self.output_dir = os.path.join(os.path.expanduser('~'), 'POS_Invoices')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _create_custom_styles(self):
        # Add modern styles
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            fontName='Helvetica-Bold',
            fontSize=30,
            leading=30,
            textColor=colors.HexColor('#2c3e50'),
            alignment=1  # Center
        ))
        
        self.styles.add(ParagraphStyle(
            name='CompanyAdrs',
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=10,
            textColor=colors.HexColor('#2c3e50'),
            alignment=1  # Center
        ))

        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#3498db'),
            alignment=1  # Center
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=8,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            fontName='Helvetica-Oblique',
            fontSize=6,
            leading=8,
            textColor=colors.HexColor('#7f8c8d'),
            alignment=1  # Center
        ))

    def _draw_background(self, canvas, doc):
        """Add watermark/background logo"""
        canvas.saveState()
        
        # Add semi-transparent background logo (without opacity)
        logo_path = resource_path("logo.png")# Replace with your logo path
        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)
            # Calculate center position
            logo_width = 3.0 * inch  # Adjust width as needed
            logo_height = 1.5 * inch  # Adjust height as needed
            x = (doc.width - logo_width) / 0.72 # Center horizontally
            y = doc.height - 0.5 * inch  # Position from top
            canvas.drawImage(logo, x, y, width=logo_width, height=logo_height, 
                            mask='auto', preserveAspectRatio=True)
        canvas.restoreState()


    def generate_pdf_bill(self, sale_id, customer_name, customer_phone, customer_email, 
                        items, subtotal, discount, total, previous_due, amount_paid, new_due):
        """
        Generate a professional PDF invoice with complete transaction details
        
        Args:
            sale_id (str): Unique invoice ID
            customer_name (str): Customer's full name
            customer_phone (str): Customer contact number
            customer_email (str): Customer email address
            items (list): List of tuples (product_name, quantity, unit_price)
            subtotal (float): Sum before discounts
            discount (float): Discount amount
            total (float): Final amount after discount
            previous_due (float): Previous outstanding balance
            amount_paid (float): Amount paid in this transaction
            new_due (float): New outstanding balance
            
        Returns:
            str: Path to generated PDF file
            
        Raises:
            ValueError: For invalid input data
            RuntimeError: If PDF generation fails
        """
        try:
            # Validate inputs
            if not all(isinstance(x, (int, float)) for x in [subtotal, discount, total, previous_due, amount_paid, new_due]):
                raise ValueError("All monetary values must be numbers")
                
            if not isinstance(items, list) or not all(len(item) == 3 for item in items):
                raise ValueError("Items must be a list of (name, quantity, price) tuples")
                
            if not sale_id or not customer_name:
                raise ValueError("Invoice ID and customer name are required")

            # Create output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.output_dir, f"Invoice_{sale_id}_{timestamp}.pdf")
            
            # Initialize document with proper margins
            doc = SimpleDocTemplate(
                filename,
                pagesize=letter,
                leftMargin=0.5*inch,
                rightMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            
            # Build PDF content
            story = self._build_pdf_content(
                sale_id, customer_name, customer_phone, customer_email,
                items, subtotal, discount, total, previous_due, amount_paid, new_due
            )
            
            # Generate PDF with background
            doc.build(
                story,
                onFirstPage=self._draw_background,
                onLaterPages=self._draw_background
            )
            
            # Open in default PDF viewer
            webbrowser.open(filename)
            
            return filename
            
        except Exception as e:
            error_msg = f"Failed to generate PDF invoice: {str(e)}"
            logging.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _build_pdf_content(self, sale_id, customer_name, customer_phone, customer_email,
                        items, subtotal, discount, total, previous_due, amount_paid, new_due):
        """Construct the PDF content structure"""
        story = []
        
        # 1. Header Section
        story.extend(self._create_header(sale_id))
        
        # 2. Customer Information
        story.extend(self._create_customer_section(
            customer_name, customer_phone, customer_email
        ))
        
        # 3. Items Table
        story.extend(self._create_items_table(items))
        
        # 4. Payment Summary
        story.extend(self._create_payment_summary(
            subtotal, discount, total, previous_due, amount_paid, new_due
        ))
        
        # 5. Footer
        story.extend(self._create_footer())
        
        return story

    def _create_header(self, sale_id):
        """Generate the invoice header section"""
        return [
            # Company Info
            Paragraph("M/s Alif Seed Farm", self.styles['CompanyName']),
            Paragraph("Sayed Market, Highcourt-Mor, Jashore-7400", self.styles['CompanyAdrs']),
            Paragraph("Phone: +8801712087445 | +8801303621895", self.styles['CompanyAdrs']),
            Paragraph("Email: alifseedfarm@outlook.com", self.styles['CompanyAdrs']),
            Spacer(1, 0.1*inch),
            Paragraph("=" * 88, self.styles['Normal']),
            Spacer(1, 0.1*inch),
            
            # Invoice Title
            Paragraph("SALES INVOICE", self.styles['InvoiceTitle']),
            Spacer(1, 0.2*inch),
            
            # Invoice Info
            Table([
                [f"Invoice #: {sale_id}", f"Date: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}"]
            ], colWidths=['*', '*'], style=[
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]),
            Spacer(1, 0.2*inch)
        ]

    def _create_customer_section(self, name, phone, email):
        """Generate customer information section"""
        return [
            Paragraph("CUSTOMER DETAILS", self.styles['SectionHeader']),
            Table([
                ["Name:", name],
                ["Phone:", phone],
                ["Email:", email if email else "N/A"]
            ], colWidths=[80, '*'], style=[
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ]),
            Spacer(1, 0.3*inch)
        ]

    def _create_items_table(self, items):
        """Generate the product items table"""
        item_data = [["Product", "Qty", "Unit Price", "Total"]]
        item_data.extend(
            [name, str(qty), f"{price:.2f} tk", f"{qty*price:.2f} tk"]
            for name, qty, price in items
        )
        
        return [
            Paragraph("ITEMS PURCHASED", self.styles['SectionHeader']),
            Table(item_data, colWidths=['*', 50, 80, 80], style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]),
            Spacer(1, 0.3*inch)
        ]

    def _create_payment_summary(self, subtotal, discount, total, previous_due, amount_paid, new_due):
        """Generate the payment summary section"""
        return [
            Paragraph("PAYMENT SUMMARY", self.styles['SectionHeader']),
            Table([
                ["Subtotal:", f"{subtotal:.2f} tk"],
                ["Discount:", f"{discount:.2f} tk"],
                ["Total:", f"{total:.2f} tk"],
                ["Previous Due:", f"{previous_due:.2f} tk"],
                ["Amount Paid:", f"{amount_paid:.2f} tk"],
                ["New Due:", f"{new_due:.2f} tk"]
            ], colWidths=['*', 100], style=[
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fff3cd')),
                ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#d4edda')),
                ('LINEABOVE', (0, 2), (-1, 2), 1, colors.HexColor('#e0e0e0')),
                ('LINEABOVE', (0, 5), (-1, 5), 1, colors.HexColor('#28a745')),
                ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ]),
            Spacer(1, 0.5*inch)
        ]

    def _create_footer(self):
        """Generate the invoice footer"""
        return [
            Table([
                [Paragraph("Thank you for your business!", self.styles['Footer'])],
                [Paragraph("We appreciate your trust in our products", self.styles['Footer'])],
                [Paragraph("Terms: All sales are final. Please contact us within 7 days for any issues.", 
                        self.styles['Footer'])],
            ], colWidths=['*'])
        ]
# Example usage:
if __name__ == "__main__":
    pdf_gen = PDFGenerator()
    
    # Sample data
    items = [
        ("Premium Rice Seeds 1kg", 2, 120.50),
        ("Organic Fertilizer 5kg", 1, 350.00),
        ("Gardening Tools Set", 1, 450.75)
    ]
    
    pdf_gen.generate_pdf_bill(
        sale_id="INV-2023-001",
        customer_name="John Doe",
        customer_phone="+880123456789",
        customer_email="john.doe@example.com",
        items=items,
        subtotal=1041.75,
        discount=41.75,
        total=1000.00,
        previous_due=250.50,
        amount_paid=800.00,
        new_due=450.50
    )