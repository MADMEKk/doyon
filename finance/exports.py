import csv
from io import BytesIO
from decimal import Decimal
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ExportService:
    @staticmethod
    def export_transactions_csv(queryset, filename="transactions.csv"):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow(['رقم السند', 'النوع', 'التاريخ', 'المبلغ', 'العملة', 'سعر الصرف', 'المبلغ المعادل', 'الحساب', 'التصنيف', 'المشروع', 'الشريك', 'جهة الاتصال', 'البيان'])
        
        for t in queryset:
            writer.writerow([
                t.reference_no,
                t.get_transaction_type_display(),
                t.date.strftime('%Y-%m-%d'),
                f"{t.amount:.2f}",
                t.currency,
                f"{t.exchange_rate:.6f}",
                f"{t.base_amount:.2f}",
                t.account.name if t.account else '',
                t.category.name if t.category else '',
                t.project.name if t.project else '',
                t.partner.name if t.partner else '',
                t.contact.name if t.contact else '',
                t.description or ''
            ])
        return response

    @staticmethod
    def export_transactions_excel(queryset, filename="transactions.xlsx"):
        wb = Workbook()
        ws = wb.active
        ws.title = "Financial Transactions"
        ws.sheet_view.rightToLeft = True

        headers = ['رقم السند', 'النوع', 'التاريخ', 'المبلغ', 'العملة', 'سعر الصرف', 'المبلغ المعادل', 'الحساب', 'التصنيف', 'المشروع', 'الشريك', 'جهة الاتصال', 'البيان']
        ws.append(headers)

        header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')

        for col_idx, col_name in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')

        for t in queryset:
            ws.append([
                t.reference_no,
                str(t.get_transaction_type_display()),
                t.date.strftime('%Y-%m-%d'),
                float(t.amount),
                t.currency,
                float(t.exchange_rate),
                float(t.base_amount),
                t.account.name if t.account else '',
                t.category.name if t.category else '',
                t.project.name if t.project else '',
                t.partner.name if t.partner else '',
                t.contact.name if t.contact else '',
                t.description or ''
            ])

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def export_summary_pdf(title, data_rows, headers, filename="financial_report.pdf"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            alignment=1, # Center
            textColor=colors.HexColor('#0F172A'),
        )
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 15))

        table_data = [headers] + data_rows
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

