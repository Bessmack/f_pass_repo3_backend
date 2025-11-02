"""
Receipt generation utilities for transactions
"""
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import qrcode
from PIL import Image as PILImage


def generate_transaction_receipt(transaction, sender, receiver):
    """
    Generate a PDF receipt for a transaction
    
    Args:
        transaction: Transaction object
        sender: User object (sender)
        receiver: User object (receiver)
    
    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Center',
        alignment=TA_CENTER,
        fontSize=12,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='Right',
        alignment=TA_RIGHT,
        fontSize=10,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='Heading1Custom',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=24,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='Heading2Custom',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    ))
    
    # Add company header
    elements.append(Paragraph("F-Pass Money Transfer", styles['Heading1Custom']))
    elements.append(Paragraph("Transaction Receipt", styles['Center']))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Add receipt info
    receipt_date = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p")
    elements.append(Paragraph(f"Generated: {receipt_date}", styles['Right']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Transaction details header
    elements.append(Paragraph("Transaction Details", styles['Heading2Custom']))
    elements.append(Spacer(1, 0.1 * inch))
    
    # Transaction info table
    transaction_data = [
        ['Transaction ID:', transaction.transaction_id],
        ['Date & Time:', datetime.strftime(transaction.created_at, "%B %d, %Y at %I:%M %p")],
        ['Status:', transaction.status.upper()],
        ['Type:', transaction.type.replace('_', ' ').title()],
    ]
    
    transaction_table = Table(transaction_data, colWidths=[2.5*inch, 3.5*inch])
    transaction_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(transaction_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Sender and Receiver details
    elements.append(Paragraph("Parties Involved", styles['Heading2Custom']))
    elements.append(Spacer(1, 0.1 * inch))
    
    parties_data = [
        ['FROM (Sender)', 'TO (Receiver)'],
        [
            f"{sender.first_name} {sender.last_name}\n{sender.email}\n{sender.phone or 'N/A'}",
            f"{receiver.first_name} {receiver.last_name}\n{receiver.email}\n{receiver.phone or 'N/A'}"
        ]
    ]
    
    parties_table = Table(parties_data, colWidths=[3*inch, 3*inch])
    parties_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(parties_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Amount breakdown
    elements.append(Paragraph("Amount Breakdown", styles['Heading2Custom']))
    elements.append(Spacer(1, 0.1 * inch))
    
    amount_data = [
        ['Transfer Amount:', f'${transaction.amount:.2f}'],
        ['Transaction Fee:', f'${transaction.fee:.2f}'],
        ['Total Amount:', f'${transaction.total_amount:.2f}'],
    ]
    
    amount_table = Table(amount_data, colWidths=[3*inch, 3*inch])
    amount_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 11),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1e40af')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(amount_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Note if present
    if transaction.note:
        elements.append(Paragraph("Transaction Note", styles['Heading2Custom']))
        elements.append(Spacer(1, 0.1 * inch))
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            borderWidth=1,
            borderColor=colors.HexColor('#d1d5db'),
            borderPadding=10,
            borderRadius=5,
            backColor=colors.HexColor('#f9fafb')
        )
        elements.append(Paragraph(transaction.note, note_style))
        elements.append(Spacer(1, 0.3 * inch))
    
    # Generate QR code for transaction verification
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(f"TXN:{transaction.transaction_id}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to buffer
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    # Add QR code to PDF
    elements.append(Paragraph("Verification QR Code", styles['Heading2Custom']))
    elements.append(Spacer(1, 0.1 * inch))
    
    qr_image = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
    qr_table = Table([[qr_image]], colWidths=[6*inch])
    qr_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(qr_table)
    elements.append(Spacer(1, 0.2 * inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("This is a system-generated receipt. No signature required.", footer_style))
    elements.append(Paragraph("For support, contact: support@fpass.com | +1-800-FPASS", footer_style))
    elements.append(Paragraph("© 2025 F-Pass Money Transfer. All rights reserved.", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Reset buffer position
    buffer.seek(0)
    
    return buffer


def generate_wallet_statement(wallet, user, transactions, start_date=None, end_date=None):
    """
    Generate a wallet statement PDF
    
    Args:
        wallet: Wallet object
        user: User object
        transactions: List of Transaction objects
        start_date: Start date for statement
        end_date: End date for statement
    
    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=18,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Add custom styles
    styles.add(ParagraphStyle(
        name='CenterHeading',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=20,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=20,
        fontName='Helvetica-Bold'
    ))
    
    # Header
    elements.append(Paragraph("Wallet Statement", styles['CenterHeading']))
    
    statement_period = f"Period: {start_date.strftime('%B %d, %Y') if start_date else 'All Time'} - {end_date.strftime('%B %d, %Y') if end_date else datetime.utcnow().strftime('%B %d, %Y')}"
    elements.append(Paragraph(statement_period, styles['Center']))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Account info
    account_data = [
        ['Account Holder:', f"{user.first_name} {user.last_name}"],
        ['Email:', user.email],
        ['Wallet ID:', wallet.wallet_id],
        ['Current Balance:', f"${wallet.balance:.2f}"],
        ['Currency:', wallet.currency],
    ]
    
    account_table = Table(account_data, colWidths=[2*inch, 4*inch])
    account_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(account_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Transactions table
    elements.append(Paragraph("Transaction History", styles['Heading2']))
    elements.append(Spacer(1, 0.1 * inch))
    
    if transactions:
        tx_data = [['Date', 'Type', 'Description', 'Amount', 'Balance']]
        
        running_balance = wallet.balance
        for tx in reversed(transactions):
            date = tx.created_at.strftime('%Y-%m-%d')
            tx_type = tx.type.replace('_', ' ').title()
            
            if tx.sender_id == user.id:
                amount = f"-${tx.total_amount:.2f}"
                description = "Transfer Out"
            else:
                amount = f"+${tx.amount:.2f}"
                description = "Transfer In" if tx.type == 'transfer' else "Deposit"
            
            tx_data.append([
                date,
                tx_type,
                description,
                amount,
                f"${running_balance:.2f}"
            ])
        
        tx_table = Table(tx_data, colWidths=[1.2*inch, 1.2*inch, 1.5*inch, 1.2*inch, 1.2*inch])
        tx_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
        ]))
        
        elements.append(tx_table)
    else:
        elements.append(Paragraph("No transactions found for this period.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer