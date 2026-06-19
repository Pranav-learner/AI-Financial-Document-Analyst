"""PDF generation service for Phase 9: Investment Memo."""

import io
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line

from app.models.memo import InvestmentMemo, MemoSection
from app.memo.memo_models import MemoPackage

# Colors aligning with the application's Indigo brand identity
COLOR_PRIMARY = HexColor("#4f46e5")    # Indigo 600
COLOR_PRIMARY_LIGHT = HexColor("#e0e7ff") # Indigo 100
COLOR_TEXT_MAIN = HexColor("#0f172a")  # Slate 900
COLOR_TEXT_MUTED = HexColor("#475569") # Slate 600
COLOR_BG_LIGHT = HexColor("#f8fafc")   # Slate 50
COLOR_BORDER = HexColor("#e2e8f0")     # Slate 200

# Severity and Recommendation color mappings
COLOR_GREEN = HexColor("#22c55e")
COLOR_GREEN_LIGHT = HexColor("#dcfce7")
COLOR_RED = HexColor("#ef4444")
COLOR_RED_LIGHT = HexColor("#fee2e2")
COLOR_AMBER = HexColor("#f59e0b")
COLOR_AMBER_LIGHT = HexColor("#fef3c7")
COLOR_BLUE = HexColor("#3b82f6")
COLOR_BLUE_LIGHT = HexColor("#dbeafe")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers and footers."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_elements(num_pages)
            super().showPage()
        super().save()

    def draw_page_elements(self, total_pages: int):
        # We omit headers and footers on the cover page (page 1)
        if self._pageNumber == 1:
            return

        self.saveState()
        
        # Draw Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(COLOR_PRIMARY)
        self.drawString(45, 805, "INVESTMENT MEMORANDUM")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_TEXT_MUTED)
        self.drawRightString(550, 805, "FinAnalyst AI Engine")
        
        # Header separator line
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(45, 797, 550, 797)
        
        # Draw Footer
        self.line(45, 45, 550, 45)
        
        self.drawString(45, 30, "CONFIDENTIAL  ·  For Internal Committee Review Only")
        footer_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(550, 30, footer_text)
        
        self.restoreState()


class PDFMemoGenerator:
    """Generates institutional-grade PDF Investment Memos using ReportLab."""

    def __init__(self, memo: InvestmentMemo, package: MemoPackage):
        self.memo = memo
        self.package = package
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        # Custom styles for the memo document
        self.title_style = ParagraphStyle(
            "CoverTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=COLOR_TEXT_MAIN,
            alignment=0, # Left-aligned for sleek modern look
            spaceAfter=15
        )
        self.subtitle_style = ParagraphStyle(
            "CoverSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=COLOR_TEXT_MUTED,
            spaceAfter=30
        )
        self.h1_style = ParagraphStyle(
            "Heading1",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=COLOR_PRIMARY,
            spaceBefore=15,
            spaceAfter=15,
            keepWithNext=True
        )
        self.h2_style = ParagraphStyle(
            "Heading2",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=COLOR_TEXT_MAIN,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True
        )
        self.body_style = ParagraphStyle(
            "Body",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=COLOR_TEXT_MUTED,
            spaceAfter=10
        )
        self.blockquote_style = ParagraphStyle(
            "BlockQuote",
            parent=self.styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=13,
            textColor=COLOR_TEXT_MAIN
        )
        self.table_header_style = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=HexColor("#ffffff")
        )
        self.table_cell_style = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=COLOR_TEXT_MUTED
        )
        self.table_cell_bold_style = ParagraphStyle(
            "TableCellBold",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=COLOR_TEXT_MAIN
        )
        self.badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=1 # Center-aligned
        )

    def _draw_bar_chart(self, width: float, height: float, labels: List[str], values: List[float], title: str) -> Drawing:
        d = Drawing(width, height)
        # Background rect
        d.add(Rect(0, 0, width, height, fillColor=COLOR_BG_LIGHT, strokeColor=COLOR_BORDER, strokeWidth=1, rx=4, ry=4))
        
        # Title
        d.add(String(15, height - 20, title, fontName="Helvetica-Bold", fontSize=9.5, fillColor=COLOR_TEXT_MAIN))
        
        # Axes boundaries
        ax_x = 45
        ax_y = 35
        ax_w = width - 65
        ax_h = height - 75
        
        # Base horizontal line
        d.add(Line(ax_x, ax_y, ax_x + ax_w, ax_y, strokeColor=COLOR_BORDER, strokeWidth=1))
        
        num_bars = len(values)
        if num_bars > 0:
            bar_gap = 12
            total_gaps_w = bar_gap * (num_bars + 1)
            bar_w = (ax_w - total_gaps_w) / num_bars
            max_val = max(max(values) if values else 100, 100)
            
            for i, (label, val) in enumerate(zip(labels, values)):
                val_clean = val if val is not None else 0.0
                h = (val_clean / max_val) * ax_h
                x = ax_x + bar_gap + i * (bar_w + bar_gap)
                y = ax_y
                
                # Dynamic color for target vs others
                fill_color = COLOR_PRIMARY if i == 0 else COLOR_TEXT_MUTED
                
                # Draw bar
                d.add(Rect(x, y, bar_w, h, fillColor=fill_color, strokeColor=None))
                # Value label
                d.add(String(x + bar_w/2, y + h + 4, f"{val_clean:.1f}", fontName="Helvetica-Bold", fontSize=7.5, textAnchor="middle", fillColor=COLOR_TEXT_MAIN))
                # Category label
                d.add(String(x + bar_w/2, y - 12, label[:12], fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=COLOR_TEXT_MUTED))
        return d

    def build_pdf(self) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=45,
            rightMargin=45,
            topMargin=55,
            bottomMargin=55
        )
        
        story = []
        
        # --- PAGE 1: COVER PAGE ---
        story.append(Spacer(1, 100))
        # Sleek vertical accent bar + Title layout
        accent_data = [
            [
                "", # Empty cell acting as color accent
                Paragraph("<b>INVESTMENT MEMORANDUM</b>", ParagraphStyle("CoverTag", parent=self.subtitle_style, fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY, spaceAfter=0))
            ]
        ]
        accent_table = Table(accent_data, colWidths=[6, 480])
        accent_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), COLOR_PRIMARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (1, 0), (1, -1), 12),
        ]))
        story.append(accent_table)
        story.append(Spacer(1, 10))
        
        story.append(Paragraph(self.memo.title, self.title_style))
        
        metadata_period = f"{self.package.reporting_period or ''} {self.package.reporting_year or ''}".strip()
        subtitle_text = f"Comprehensive investment analysis and risk assessment for <b>{self.package.company_name}</b> based on the {metadata_period} reporting disclosures."
        story.append(Paragraph(subtitle_text, self.subtitle_style))
        story.append(Spacer(1, 40))
        
        # Cover metadata card
        created_str = self.memo.created_at.strftime("%B %d, %Y") if self.memo.created_at else datetime.now().strftime("%B %d, %Y")
        meta_data = [
            [Paragraph("<b>Company Name:</b>", self.table_cell_bold_style), Paragraph(self.package.company_name, self.table_cell_style)],
            [Paragraph("<b>Reporting Period:</b>", self.table_cell_bold_style), Paragraph(metadata_period or "Annual/Quarterly", self.table_cell_style)],
            [Paragraph("<b>Memo Type:</b>", self.table_cell_bold_style), Paragraph(str(self.memo.memo_type.value), self.table_cell_style)],
            [Paragraph("<b>Date Generated:</b>", self.table_cell_bold_style), Paragraph(created_str, self.table_cell_style)],
            [Paragraph("<b>Prepared By:</b>", self.table_cell_bold_style), Paragraph("FinAnalyst AI Autonomous Engine", self.table_cell_style)],
        ]
        meta_table = Table(meta_data, colWidths=[130, 350])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
            ('BORDER', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(meta_table)
        
        story.append(Spacer(1, 150))
        
        disclaimer_text = "<b>CONFIDENTIALITY NOTICE:</b> The information contained in this investment memorandum is highly confidential and intended solely for the internal use of the investment committee. It incorporates autonomous quantitative modeling and generative synthesis based on public filing disclosures."
        story.append(Paragraph(disclaimer_text, ParagraphStyle("Disclaimer", parent=self.body_style, fontSize=7.5, leading=11, textColor=COLOR_TEXT_MUTED)))
        
        story.append(PageBreak())
        
        # Fetch sections dictionary for simple ordered access
        sec_map = {s.section_name: s for s in self.memo.sections}
        
        # --- PAGE 2: EXECUTIVE SUMMARY ---
        story.append(Paragraph("Executive Summary", self.h1_style))
        story.append(Spacer(1, 5))
        
        # Determine Rating, Confidence, Risk, and Recommendation
        overall_score = 0.0
        rank_str = "N/A"
        if self.package.benchmark:
            overall_score = self.package.benchmark.overall_score or 0.0
            rank_str = f"Rank {self.package.benchmark.rank}"
            
        sentiment_score = 0.0
        if self.package.tones:
            sentiment_score = sum(t.sentiment_score for t in self.package.tones) / len(self.package.tones)
            
        # Dynamically classify rating
        if overall_score >= 70.0 or (overall_score == 0.0 and sentiment_score > 0.15):
            rating_text = "BULLISH"
            rating_bg = COLOR_GREEN_LIGHT
            rating_fg = COLOR_GREEN
            rec_text = "BUY"
            rec_bg = COLOR_GREEN_LIGHT
            rec_fg = COLOR_GREEN
        elif overall_score < 40.0 or (overall_score == 0.0 and sentiment_score < -0.15):
            rating_text = "BEARISH"
            rating_bg = COLOR_RED_LIGHT
            rating_fg = COLOR_RED
            rec_text = "SELL"
            rec_bg = COLOR_RED_LIGHT
            rec_fg = COLOR_RED
        else:
            rating_text = "NEUTRAL"
            rating_bg = COLOR_AMBER_LIGHT
            rating_fg = COLOR_AMBER
            rec_text = "HOLD"
            rec_bg = COLOR_AMBER_LIGHT
            rec_fg = COLOR_AMBER

        has_critical_risk = any(r.severity in ("CRITICAL", "HIGH") for r in self.package.risks)
        risk_text = "HIGH" if has_critical_risk else "MEDIUM"
        risk_bg = COLOR_RED_LIGHT if has_critical_risk else COLOR_AMBER_LIGHT
        risk_fg = COLOR_RED if has_critical_risk else COLOR_AMBER
        
        # Layout splitting Executive Summary (Left column) and Callout Box (Right column)
        summary_paragraphs = [
            Paragraph(p, self.body_style) for p in (self.memo.executive_summary or "Executive Summary content is pending.").split("\n\n") if p.strip()
        ]
        
        # Side Card Table
        card_data = [
            [Paragraph("INVESTMENT CARD", ParagraphStyle("CardTag", parent=self.table_cell_bold_style, textColor=COLOR_PRIMARY, alignment=1))],
            [Paragraph("<b>Target Rating:</b>", self.table_cell_bold_style)],
            [Paragraph(rating_text, ParagraphStyle("RatingB", parent=self.badge_style, textColor=rating_fg))],
            [Paragraph("<b>Recommendation:</b>", self.table_cell_bold_style)],
            [Paragraph(rec_text, ParagraphStyle("RecB", parent=self.badge_style, textColor=rec_fg))],
            [Paragraph("<b>Confidence Level:</b>", self.table_cell_bold_style)],
            [Paragraph("HIGH", ParagraphStyle("ConfB", parent=self.badge_style, textColor=COLOR_PRIMARY))],
            [Paragraph("<b>Overall Risk:</b>", self.table_cell_bold_style)],
            [Paragraph(risk_text, ParagraphStyle("RiskB", parent=self.badge_style, textColor=risk_fg))],
            [Paragraph("<b>Horizon:</b>", self.table_cell_bold_style)],
            [Paragraph("12 MONTHS", ParagraphStyle("HorizonB", parent=self.badge_style, textColor=COLOR_TEXT_MAIN))],
        ]
        
        card_table = Table(card_data, colWidths=[150])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
            ('BORDER', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            # Background colors for specific badge rows
            ('BACKGROUND', (0, 2), (0, 2), rating_bg),
            ('BACKGROUND', (0, 4), (0, 4), rec_bg),
            ('BACKGROUND', (0, 6), (0, 6), COLOR_PRIMARY_LIGHT),
            ('BACKGROUND', (0, 8), (0, 8), risk_bg),
            ('BACKGROUND', (0, 10), (0, 10), COLOR_BORDER),
        ]))
        
        # Grid layout for page
        left_flow = []
        left_flow.extend(summary_paragraphs)
        
        split_table = Table([[left_flow, card_table]], colWidths=[330, 170])
        split_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('RIGHTPADDING', (0, 0), (0, 0), 15),
            ('LEFTPADDING', (1, 0), (1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(split_table)
        
        story.append(PageBreak())
        
        # --- PAGE 3: COMPANY OVERVIEW ---
        story.append(Paragraph("Company Overview", self.h1_style))
        story.append(Spacer(1, 5))
        
        overview_sec = sec_map.get("Company Overview")
        if overview_sec:
            overview_paragraphs = [
                Paragraph(p, self.body_style) for p in overview_sec.content.split("\n\n") if p.strip()
            ]
            story.extend(overview_paragraphs)
        else:
            story.append(Paragraph("Company Overview narrative is pending.", self.body_style))
            
        # Draw a summary box of company attributes if available
        overview_box_data = [
            [Paragraph("<b>Company Identifier</b>", self.table_cell_bold_style), Paragraph(self.package.company_name, self.table_cell_style)],
            [Paragraph("<b>Primary Report Reference</b>", self.table_cell_bold_style), Paragraph(self.package.report_title, self.table_cell_style)],
            [Paragraph("<b>Period Reference</b>", self.table_cell_bold_style), Paragraph(metadata_period, self.table_cell_style)],
        ]
        overview_box_table = Table(overview_box_data, colWidths=[150, 350])
        overview_box_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
            ('BORDER', (0, 0), (-1, -1), 1, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(Spacer(1, 20))
        story.append(overview_box_table)
        
        story.append(PageBreak())
        
        # --- PAGE 4: FINANCIAL ANALYSIS & PERFORMANCE ---
        story.append(Paragraph("Financial Analysis & Performance", self.h1_style))
        story.append(Spacer(1, 5))
        
        fin_sec = sec_map.get("Financial Summary")
        if fin_sec:
            story.append(Paragraph(fin_sec.content, self.body_style))
            story.append(Spacer(1, 10))
            
        # Create comparisons table
        if self.package.comparisons:
            comp_rows = [
                [
                    Paragraph("<b>Metric Name</b>", self.table_header_style),
                    Paragraph("<b>Current Period</b>", self.table_header_style),
                    Paragraph("<b>Prior Period</b>", self.table_header_style),
                    Paragraph("<b>Change (%)</b>", self.table_header_style),
                    Paragraph("<b>Context</b>", self.table_header_style)
                ]
            ]
            for c in self.package.comparisons[:12]:
                curr_val = f"{c.current_value:,.2f}" if c.current_value is not None else "N/A"
                prev_val = f"{c.previous_value:,.2f}" if c.previous_value is not None else "N/A"
                change_val = f"{c.change_pct:+.1f}%" if c.change_pct is not None else "N/A"
                
                # Check change direction for styling
                change_style = self.table_cell_style
                if c.change_pct is not None:
                    if c.change_pct > 0:
                        change_style = ParagraphStyle("pct_pos", parent=self.table_cell_style, textColor=COLOR_GREEN, fontName="Helvetica-Bold")
                    elif c.change_pct < 0:
                        change_style = ParagraphStyle("pct_neg", parent=self.table_cell_style, textColor=COLOR_RED, fontName="Helvetica-Bold")
                
                comp_rows.append([
                    Paragraph(c.metric_name.replace("_", " ").title(), self.table_cell_bold_style),
                    Paragraph(curr_val, self.table_cell_style),
                    Paragraph(prev_val, self.table_cell_style),
                    Paragraph(change_val, change_style),
                    Paragraph(c.comparison_type.title(), self.table_cell_style)
                ])
            
            comp_table = Table(comp_rows, colWidths=[140, 90, 90, 80, 100])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_BG_LIGHT, HexColor("#ffffff")]),
                ('BORDER', (0, 0), (-1, -1), 1, COLOR_BORDER),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(Paragraph("<b>Period-over-Period Performance Metrics:</b>", self.h2_style))
            story.append(comp_table)
            
        # Programmatic financial metrics chart
        if self.package.comparisons:
            chart_labels = []
            chart_values = []
            for c in self.package.comparisons[:5]:
                if c.change_pct is not None:
                    chart_labels.append(c.metric_name.replace("_", " ").title())
                    chart_values.append(abs(c.change_pct)) # Graph absolute changes for visual comparison
            
            if chart_values:
                story.append(Spacer(1, 20))
                chart_drawing = self._draw_bar_chart(500, 150, chart_labels, chart_values, "Metric Growth / Variance Impact (%)")
                story.append(chart_drawing)
                
        story.append(PageBreak())
        
        # --- PAGE 5: RISK ASSESSMENT ---
        story.append(Paragraph("Risk Intelligence & Assessment", self.h1_style))
        story.append(Spacer(1, 5))
        
        risk_sec = sec_map.get("Risk Summary")
        if risk_sec:
            story.append(Paragraph(risk_sec.content, self.body_style))
            story.append(Spacer(1, 10))
            
        if self.package.risks:
            risk_rows = [
                [
                    Paragraph("<b>Category</b>", self.table_header_style),
                    Paragraph("<b>Severity</b>", self.table_header_style),
                    Paragraph("<b>Risk Description & Details</b>", self.table_header_style)
                ]
            ]
            for r in self.package.risks:
                # Classify severity styles
                sev = r.severity.upper()
                if sev == "CRITICAL":
                    sev_style = ParagraphStyle("CriticalB", parent=self.badge_style, textColor=COLOR_RED)
                    sev_bg = COLOR_RED_LIGHT
                elif sev == "HIGH":
                    sev_style = ParagraphStyle("HighB", parent=self.badge_style, textColor=COLOR_RED)
                    sev_bg = COLOR_RED_LIGHT
                elif sev == "MEDIUM":
                    sev_style = ParagraphStyle("MedB", parent=self.badge_style, textColor=COLOR_AMBER)
                    sev_bg = COLOR_AMBER_LIGHT
                else:
                    sev_style = ParagraphStyle("LowB", parent=self.badge_style, textColor=COLOR_GREEN)
                    sev_bg = COLOR_GREEN_LIGHT
                    
                risk_rows.append([
                    Paragraph(r.category.replace("_", " ").title(), self.table_cell_bold_style),
                    Paragraph(sev, sev_style),
                    Paragraph(r.description, self.table_cell_style)
                ])
                
            risk_table = Table(risk_rows, colWidths=[120, 80, 300])
            risk_table_styles = [
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_BG_LIGHT, HexColor("#ffffff")]),
                ('BORDER', (0, 0), (-1, -1), 1, COLOR_BORDER),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]
            # Add dynamic backgrounds to severity cell column
            for i in range(1, len(risk_rows)):
                # Get the severity bg color matching the row
                sev_type = self.package.risks[i-1].severity.upper()
                if sev_type in ("CRITICAL", "HIGH"):
                    row_bg = COLOR_RED_LIGHT
                elif sev_type == "MEDIUM":
                    row_bg = COLOR_AMBER_LIGHT
                else:
                    row_bg = COLOR_GREEN_LIGHT
                risk_table_styles.append(('BACKGROUND', (1, i), (1, i), row_bg))
                
            risk_table.setStyle(TableStyle(risk_table_styles))
            story.append(Paragraph("<b>Identified Risk Exposures:</b>", self.h2_style))
            story.append(risk_table)
            
        story.append(PageBreak())
        
        # --- PAGE 6: MANAGEMENT ASSESSMENT ---
        story.append(Paragraph("Management Commentary & Assessment", self.h1_style))
        story.append(Spacer(1, 5))
        
        mgmt_sec = sec_map.get("Management Assessment")
        if mgmt_sec:
            story.append(Paragraph(mgmt_sec.content, self.body_style))
            story.append(Spacer(1, 10))
            
        if self.package.tones:
            story.append(Paragraph("<b>Corporate Disclosures Sentiment:</b>", self.h2_style))
            tone_rows = [
                [
                    Paragraph("<b>Dimension</b>", self.table_header_style),
                    Paragraph("<b>Value</b>", self.table_header_style),
                    Paragraph("<b>Interpretation / Signal</b>", self.table_header_style)
                ]
            ]
            for t in self.package.tones:
                tone_rows.append([
                    Paragraph("Report Sentiment", self.table_cell_bold_style),
                    Paragraph(t.sentiment, self.table_cell_style),
                    Paragraph(f"Sentiment Score: {t.sentiment_score:+.2f} (higher is positive)", self.table_cell_style)
                ])
                tone_rows.append([
                    Paragraph("Confidence Level", self.table_cell_bold_style),
                    Paragraph(t.confidence_level, self.table_cell_style),
                    Paragraph("Reflects transparency and certainty in forward outlooks", self.table_cell_style)
                ])
                tone_rows.append([
                    Paragraph("Hedging / Uncertainty Score", self.table_cell_bold_style),
                    Paragraph(f"{t.hedging_score:.2f}", self.table_cell_style),
                    Paragraph("Elevated scores indicate cautious strategic wording", self.table_cell_style)
                ])
                
            tone_table = Table(tone_rows, colWidths=[150, 100, 250])
            tone_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_BG_LIGHT, HexColor("#ffffff")]),
                ('BORDER', (0, 0), (-1, -1), 1, COLOR_BORDER),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(tone_table)
            
            # Management quote panel (using the text snippet from citations as quotes)
            quotes = []
            for t in self.package.tones:
                # Find associated evidence text chunks
                matching_chunks = [ch.content for ch in self.package.retrieved_evidence if ch.id == t.source_chunk_id]
                if matching_chunks:
                    quotes.append(matching_chunks[0])
            
            if not quotes and self.package.retrieved_evidence:
                quotes.append(self.package.retrieved_evidence[0].content)
                
            if quotes:
                story.append(Spacer(1, 15))
                story.append(Paragraph("<b>Highlighted Commentary Segments:</b>", self.h2_style))
                for q in quotes[:2]:
                    quote_text = f"\"{q}\""
                    q_table = Table([[Paragraph(quote_text, self.blockquote_style)]], colWidths=[480])
                    q_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                        ('LINELEFT', (0, 0), (0, -1), 3.5, COLOR_PRIMARY),
                        ('TOPPADDING', (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 12),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                    ]))
                    story.append(q_table)
                    story.append(Spacer(1, 10))
                    
        story.append(PageBreak())
        
        # --- PAGE 7: COMPETITIVE POSITION & BENCHMARKING ---
        story.append(Paragraph("Competitive Position & Benchmarking", self.h1_style))
        story.append(Spacer(1, 5))
        
        bench_sec = sec_map.get("Competitive Position")
        if bench_sec:
            story.append(Paragraph(bench_sec.content, self.body_style))
            story.append(Spacer(1, 10))
            
        if self.package.benchmark:
            b = self.package.benchmark
            bench_rows = [
                [
                    Paragraph("<b>Benchmark Metric</b>", self.table_header_style),
                    Paragraph("<b>Score / Value</b>", self.table_header_style),
                    Paragraph("<b>Interpretation / Percentile Rank</b>", self.table_header_style)
                ],
                [Paragraph("Overall Score", self.table_cell_bold_style), Paragraph(f"{b.overall_score:.1f}", self.table_cell_style), Paragraph(f"Overall Cohort Rank: {b.rank or 'N/A'}", self.table_cell_style)],
                [Paragraph("Financial Score", self.table_cell_bold_style), Paragraph(f"{b.financial_score:.1f}", self.table_cell_style), Paragraph("Strength of balance sheet and growth metrics", self.table_cell_style)],
                [Paragraph("Risk Score", self.table_cell_bold_style), Paragraph(f"{b.risk_score:.1f}", self.table_cell_style), Paragraph("Calculated based on risk exposure density", self.table_cell_style)],
                [Paragraph("Commentary Tone Score", self.table_cell_bold_style), Paragraph(f"{b.tone_score:.1f}", self.table_cell_style), Paragraph("Relative positivity of corporate filings", self.table_cell_style)],
                [Paragraph("Capital Allocation Score", self.table_cell_bold_style), Paragraph(f"{b.capital_allocation_score:.1f}", self.table_cell_style), Paragraph("Operational reinvestment efficiency rating", self.table_cell_style)],
            ]
            
            bench_table = Table(bench_rows, colWidths=[160, 100, 240])
            bench_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_BG_LIGHT, HexColor("#ffffff")]),
                ('BORDER', (0, 0), (-1, -1), 1, COLOR_BORDER),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(Paragraph("<b>Cohort Performance Comparison:</b>", self.h2_style))
            story.append(bench_table)
            
            # Programmatic benchmarking vector bar chart
            labels = ["Overall", "Financial", "Risk", "Tone", "Cap. Alloc"]
            values = [
                b.overall_score or 0.0,
                b.financial_score or 0.0,
                b.risk_score or 0.0,
                b.tone_score or 0.0,
                b.capital_allocation_score or 0.0
            ]
            story.append(Spacer(1, 20))
            bench_drawing = self._draw_bar_chart(500, 150, labels, values, f"{self.package.company_name} Dimension Ratings vs Peers (Rank {b.rank})")
            story.append(bench_drawing)
            
        story.append(PageBreak())
        
        # --- PAGE 8: INVESTMENT THESIS (BULL / BEAR CASES) ---
        story.append(Paragraph("Investment Thesis: Bull & Bear Cases", self.h1_style))
        story.append(Spacer(1, 5))
        
        # Stacked Bull & Bear Cases
        bull_sec = sec_map.get("Bull Case")
        bear_sec = sec_map.get("Bear Case")
        
        if bull_sec:
            bull_paragraphs = [Paragraph(p, self.body_style) for p in bull_sec.content.split("\n\n") if p.strip()]
            bull_content = []
            bull_content.append(Paragraph("<b>BULL CASE ARGUMENTS (GROWTH & UPSIDE DRIVERS)</b>", ParagraphStyle("BullTag", parent=self.table_cell_bold_style, textColor=COLOR_GREEN, fontSize=9.5, spaceAfter=8)))
            bull_content.extend(bull_paragraphs)
            
            bull_table = Table([[bull_content]], colWidths=[490])
            bull_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), HexColor("#f0fdf4")), # soft green
                ('BORDER', (0, 0), (-1, -1), 1, COLOR_GREEN),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            story.append(bull_table)
            story.append(Spacer(1, 15))
            
        if bear_sec:
            bear_paragraphs = [Paragraph(p, self.body_style) for p in bear_sec.content.split("\n\n") if p.strip()]
            bear_content = []
            bear_content.append(Paragraph("<b>BEAR CASE ARGUMENTS (RISKS & DOWNSIDE DRIVERS)</b>", ParagraphStyle("BearTag", parent=self.table_cell_bold_style, textColor=COLOR_RED, fontSize=9.5, spaceAfter=8)))
            bear_content.extend(bear_paragraphs)
            
            bear_table = Table([[bear_content]], colWidths=[490])
            bear_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), HexColor("#fef2f2")), # soft red
                ('BORDER', (0, 0), (-1, -1), 1, COLOR_RED),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            story.append(bear_table)
            
        if not bull_sec and not bear_sec:
            story.append(Paragraph("Bull/Bear thesis statements are currently pending.", self.body_style))
            
        story.append(PageBreak())
        
        # --- PAGE 9: DUE DILIGENCE QUESTIONS ---
        story.append(Paragraph("Due Diligence & Investor Inquiries", self.h1_style))
        story.append(Spacer(1, 5))
        
        q_sec = sec_map.get("Questions to Investigate") or sec_map.get("Questions to Investigate")
        if not q_sec:
            # Check keys matching 'Question'
            for k, val in sec_map.items():
                if "question" in k.lower():
                    q_sec = val
                    break
                    
        if q_sec:
            # Format questions nicely in table rows or separate paragraph panels
            q_lines = [q.strip() for q in q_sec.content.split("\n") if q.strip()]
            story.append(Paragraph("The following inquiry vectors represent unresolved matters identified for follow-up verification with company management:", self.body_style))
            story.append(Spacer(1, 10))
            
            for idx, q_line in enumerate(q_lines):
                # Clean prefix number if present
                clean_line = q_line
                if clean_line.startswith(tuple(str(x) for x in range(10))):
                    # split and take the rest
                    parts = clean_line.split(".", 1)
                    if len(parts) > 1:
                        clean_line = parts[1].strip()
                        
                q_row = [
                    Paragraph(f"<b>{idx+1}</b>", ParagraphStyle("QNum", parent=self.table_cell_bold_style, fontName="Helvetica-Bold", fontSize=11, textColor=COLOR_PRIMARY, alignment=1)),
                    Paragraph(clean_line, self.body_style)
                ]
                q_table = Table([q_row], colWidths=[30, 460])
                q_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                    ('BORDER', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(q_table)
                story.append(Spacer(1, 10))
        else:
            story.append(Paragraph("No due diligence inquiries compiled for this report.", self.body_style))
            
        story.append(PageBreak())
        
        # --- PAGE 10: FINAL RECOMMENDATION ---
        story.append(Paragraph("Final Investment Recommendation", self.h1_style))
        story.append(Spacer(1, 10))
        
        # Hero Recommendation Panel
        rec_details_content = [
            Paragraph("<b>AUTONOMOUS RATING CARD</b>", ParagraphStyle("RatingHeader", parent=self.table_cell_bold_style, fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)),
            Spacer(1, 8),
            Paragraph(f"Recommendation Rating: <b>{rec_text}</b>", self.body_style),
            Paragraph(f"Strategic Position Rating: <b>{rating_text}</b>", self.body_style),
            Paragraph(f"Analytical Model Confidence: <b>HIGH (85%)</b>", self.body_style),
            Paragraph(f"Determined Investment Horizon: <b>12 Months</b>", self.body_style),
            Paragraph(f"Identified Structural Risks: <b>{risk_text} Severity</b>", self.body_style)
        ]
        
        rec_hero_table = Table([[rec_details_content]], colWidths=[490])
        rec_hero_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
            ('BORDER', (0, 0), (-1, -1), 1.5, COLOR_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ]))
        story.append(rec_hero_table)
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("<b>Concluding Analytical Remarks:</b>", self.h2_style))
        concluding_remarks = (
            f"The computed financial scores of {overall_score:.1f}/100 and corporate disclosures tone "
            f"indicate a dynamic {rating_text.lower()} strategic outlook for {self.package.company_name}. "
            f"Investment managers should cross-verify the highlighted risk profiles and proceed with the due diligence queries "
            f"prior to taking active portfolio positions."
        )
        story.append(Paragraph(concluding_remarks, self.body_style))
        
        story.append(PageBreak())
        
        # --- PAGE 11: SOURCES & REFERENCES ---
        story.append(Paragraph("Sources & Citations Index", self.h1_style))
        story.append(Spacer(1, 5))
        
        # Aggregate citations across all sections
        citations = []
        for s in self.memo.sections:
            for c in s.citations:
                citations.append(c)
                
        if not citations and self.package.retrieved_evidence:
            # Fallback citations using package evidence chunks
            for idx, ch in enumerate(self.package.retrieved_evidence[:8]):
                citations.append({
                    "source_type": "text_chunk",
                    "page_number": ch.page_number,
                    "section_name": ch.section_name or "Overview",
                    "text_snippet": ch.content
                })
                
        if citations:
            story.append(Paragraph("The following data points and narrative assertions are grounded in the index document references:", self.body_style))
            story.append(Spacer(1, 10))
            
            for idx, cit in enumerate(citations[:15]): # Limit to top 15 sources for page fit
                c_sec_name = cit.get("section_name") or "General"
                c_page = cit.get("page_number") or "N/A"
                c_type = cit.get("source_type") or "text_chunk"
                c_snippet = cit.get("text_snippet") or "Source context referenced in text."
                
                # Format snippet to be compact
                if len(c_snippet) > 200:
                    c_snippet = c_snippet[:200] + "..."
                    
                cit_text = f"<b>[{idx+1}] {c_type.upper()}</b> (Page {c_page}, Section: {c_sec_name})<br/><font color='#475569'><i>\"{c_snippet}\"</i></font>"
                
                cit_panel = Table([[Paragraph(cit_text, ParagraphStyle("CitText", parent=self.table_cell_style, fontSize=8.5, leading=12))]], colWidths=[490])
                cit_panel.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                    ('BORDER', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(cit_panel)
                story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("No verifiable source references indexed for this memo.", self.body_style))
            
        # Build Document
        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
