import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 760, "SmartEstate AI — Final Year Project Diary #04")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(40, 752, 572, 752)
        
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 30, page_text)
        self.drawString(40, 30, "Department of CSE (AIML) | SmartEstate AI Project")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 42, 572, 42)
        self.restoreState()

def generate_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#1e3a8a") # Deep Navy Blue
    secondary_color = colors.HexColor("#0284c7") # Ocean Blue
    text_dark = colors.HexColor("#1e293b")
    text_muted = colors.HexColor("#475569")
    bg_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#cbd5e1")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        alignment=1 # Center
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        alignment=1
    )
    
    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark
    )
    
    meta_bold = ParagraphStyle(
        'MetaBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=primary_color
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4
    )
    
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=secondary_color,
        spaceBefore=5,
        spaceAfter=3
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        spaceAfter=3
    )
    
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )
    
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_dark
    )
    
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.white
    )
    
    story = []
    
    # Title Section
    story.append(Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING (AI & ML)", subtitle_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph("FINAL YEAR PROJECT DIARY / LOGBOOK — ENTRY #04", title_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))
    
    # Meta Information Box
    meta_data = [
        [
            Paragraph("<b>Project Title:</b>", meta_bold),
            Paragraph("SmartEstate AI — Intelligent Real Estate Valuation, Fraud Detection & Property Discovery Platform", meta_style),
            Paragraph("<b>Phase / Diary No:</b>", meta_bold),
            Paragraph("Entry 04 (Week 7 – Week 8)", meta_style)
        ],
        [
            Paragraph("<b>Domain:</b>", meta_bold),
            Paragraph("Full-Stack Web App, Machine Learning, Cloud Database", meta_style),
            Paragraph("<b>Project Phase:</b>", meta_bold),
            Paragraph("Part 1: Foundation & Base Shell", meta_style)
        ],
        [
            Paragraph("<b>Student Name:</b>", meta_bold),
            Paragraph("Bhargavi Digu Naik & Team", meta_style),
            Paragraph("<b>Repository:</b>", meta_bold),
            Paragraph("MonikaKS545/smart-estate-ai (GitHub)", meta_style)
        ]
    ]
    
    meta_table = Table(meta_data, colWidths=[80, 210, 95, 147])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))
    
    # 1. Objectives
    story.append(Paragraph("1. Objectives for the Week / Phase", h1_style))
    story.append(Paragraph("• Establish the core backend infrastructure utilizing <b>FastAPI</b> and cloud-hosted <b>PostgreSQL (Neon)</b>.", bullet_style))
    story.append(Paragraph("• Design, normalize, and execute database migrations for all <b>16 relational tables</b> using <b>SQLAlchemy ORM</b> and <b>Alembic</b>.", bullet_style))
    story.append(Paragraph("• Implement a multi-channel secure authentication subsystem (Email/Password, Email OTP verification, Google OAuth 2.0, and JWT token sessions).", bullet_style))
    story.append(Paragraph("• Develop RESTful API endpoints for Property CRUD operations, image uploads, favorites, and saved searches.", bullet_style))
    story.append(Paragraph("• Scaffold the <b>React + Vite + Tailwind CSS v4</b> frontend shell with role-based protected routing and stub dashboards.", bullet_style))
    story.append(Paragraph("• Populate seed data (30 properties, 15 amenities) for integration testing across endpoints.", bullet_style))
    story.append(Spacer(1, 6))
    
    # 2. Work Done
    story.append(Paragraph("2. Detailed Activities & Technical Execution", h1_style))
    
    story.append(Paragraph("A. Database Architecture & Alembic Migrations", h2_style))
    story.append(Paragraph("Configured connection pools to Neon PostgreSQL. Implemented complete schema definitions across 16 entities: Auth & Users (<code>users</code>, <code>user_roles</code>, <code>otp_verifications</code>), Property Domain (<code>properties</code>, <code>property_images</code>, <code>amenities</code>, <code>property_amenities</code>), User Actions (<code>favorites</code>, <code>saved_searches</code>), and Placeholder Tables for upcoming ML modules (<code>price_predictions</code>, <code>fraud_analysis</code>, <code>document_verifications</code>, <code>chat_sessions</code>, <code>chat_messages</code>). Migrations executed seamlessly via <code>alembic upgrade head</code>.", body_style))
    
    story.append(Paragraph("B. Authentication & Multi-Channel Verification", h2_style))
    story.append(Paragraph("Implemented password hashing with <code>passlib[bcrypt]</code>. Integrated stateless JWT issuance/verification using <code>python-jose</code>. Configured transactional OTP email delivery over SSL/TLS via Python's <code>smtplib</code> using Gmail App Passwords. Integrated Google OAuth 2.0 authentication flow with <code>Authlib</code>.", body_style))
    
    story.append(Paragraph("C. REST API Endpoints Development (FastAPI)", h2_style))
    story.append(Paragraph("Engineered modular routers prefixed under <code>/api/v1</code>: Auth endpoints (<code>/auth/register</code>, <code>/auth/login</code>, <code>/auth/otp/*</code>, <code>/auth/google/*</code>, <code>/auth/me</code>), Property management with query filters and pagination (<code>/properties</code>), multipart image uploads (<code>/properties/{id}/images</code>), and user interactions (<code>/favorites</code>, <code>/saved-searches</code>, <code>/admin/*</code>).", body_style))
    
    story.append(Paragraph("D. Frontend Shell & Navigation (React + Vite)", h2_style))
    story.append(Paragraph("Created Single Page Application structure with React 18, Vite, and Tailwind CSS v4. Configured <code>React Router v6</code> with protected route guards (<code>PrivateRoute.jsx</code>) for Buyer, Agent, and Admin dashboards. Set up Axios API clients with automatic JWT Authorization header interceptors.", body_style))
    
    story.append(Paragraph("E. Data Seeding & Integration Testing", h2_style))
    story.append(Paragraph("Executed <code>seed.py</code> inserting 30 comprehensive property listings with geolocation, pricing, specs, and 15 amenities. Validated all endpoints via Swagger UI (<code>/docs</code>).", body_style))
    story.append(Spacer(1, 6))
    
    # 3. Tech Stack
    story.append(Paragraph("3. Technologies, Frameworks & Libraries", h1_style))
    tech_data = [
        [
            Paragraph("<b>Backend:</b>", meta_bold),
            Paragraph("FastAPI, Uvicorn, Pydantic v2, Python 3.11", table_cell),
            Paragraph("<b>Database:</b>", meta_bold),
            Paragraph("PostgreSQL (Neon Cloud), SQLAlchemy, Alembic", table_cell)
        ],
        [
            Paragraph("<b>Frontend:</b>", meta_bold),
            Paragraph("React 18, Vite, Tailwind CSS v4, React Router DOM", table_cell),
            Paragraph("<b>Security / Auth:</b>", meta_bold),
            Paragraph("JWT (python-jose), Bcrypt (passlib), Authlib, smtplib", table_cell)
        ],
        [
            Paragraph("<b>Tools:</b>", meta_bold),
            Paragraph("Git, GitHub, VS Code, Postman, Swagger UI", table_cell),
            Paragraph("<b>Data / Seeding:</b>", meta_bold),
            Paragraph("30 properties, 15 amenities seeded for test workflows", table_cell)
        ]
    ]
    tech_table = Table(tech_data, colWidths=[80, 185, 90, 177])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 8))
    
    # 4. Challenges & Solutions Table
    story.append(Paragraph("4. Technical Challenges Encountered & Resolutions", h1_style))
    challenges_data = [
        [
            Paragraph("<b>#</b>", table_cell_bold),
            Paragraph("<b>Challenge Encountered</b>", table_cell_bold),
            Paragraph("<b>Root Cause Analysis</b>", table_cell_bold),
            Paragraph("<b>Resolution Applied</b>", table_cell_bold)
        ],
        [
            Paragraph("1", table_cell),
            Paragraph("CORS errors during frontend API requests", table_cell),
            Paragraph("Origins between Vite (port 5173) and FastAPI (port 8000) not linked", table_cell),
            Paragraph("Configured <code>CORSMiddleware</code> in <code>main.py</code> allowing explicit origins and credentials.", table_cell)
        ],
        [
            Paragraph("2", table_cell),
            Paragraph("Uploaded property images inaccessible over HTTP", table_cell),
            Paragraph("Uploaded directory was saved on disk but not mounted on FastAPI router", table_cell),
            Paragraph("Mounted <code>/uploads</code> route using Starlette's <code>StaticFiles</code> handler.", table_cell)
        ],
        [
            Paragraph("3", table_cell),
            Paragraph("Gmail SMTP OTP authentication failure", table_cell),
            Paragraph("Standard account password rejected due to 2FA restrictions", table_cell),
            Paragraph("Generated dedicated Google App Password and wrapped connection in SSL/TLS context.", table_cell)
        ],
        [
            Paragraph("4", table_cell),
            Paragraph("Branch divergence on remote repository", table_cell),
            Paragraph("Concurrent teammate commits on <code>main</code> branch", table_cell),
            Paragraph("Rebased local branch onto <code>origin/main</code>, resolved router merge in <code>main.py</code>, and pushed cleanly.", table_cell)
        ]
    ]
    challenges_table = Table(challenges_data, colWidths=[20, 150, 162, 200])
    challenges_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light])
    ]))
    story.append(challenges_table)
    story.append(Spacer(1, 8))
    
    # 5. Deliverables Achieved
    story.append(Paragraph("5. Measurable Outcomes & Deliverables Achieved", h1_style))
    story.append(Paragraph("<b>[Done]</b> Central PostgreSQL database with all 16 normalized tables deployed on Neon cloud.", bullet_style))
    story.append(Paragraph("<b>[Done]</b> Complete authentication lifecycle (Register, Login, OTP Verify, OAuth 2.0, JWT) active.", bullet_style))
    story.append(Paragraph("<b>[Done]</b> Property CRUD, image upload processing, and interactive Swagger docs (<code>/docs</code>) operational.", bullet_style))
    story.append(Paragraph("<b>[Done]</b> React frontend shell with role-based protected routes and Axios auth interceptors functional.", bullet_style))
    story.append(Paragraph("<b>[Done]</b> Codebase synchronized and pushed to team GitHub repository (<code>main</code> and <code>part2-ml</code> branches).", bullet_style))
    story.append(Spacer(1, 6))
    
    # 6. Plan for Next Phase
    story.append(Paragraph("6. Plan for Next Phase (Phase 5 / Diary 5: AI & ML Services)", h1_style))
    story.append(Paragraph("• Train machine learning price estimation model on Bangalore properties dataset (<code>train_price_model.py</code>).", bullet_style))
    story.append(Paragraph("• Implement heuristic & statistical fraud risk scoring engine for property verification (<code>fraud_scorer.py</code>).", bullet_style))
    story.append(Paragraph("• Build duplicate listing detection algorithm using Jaccard text similarity and geospatial tolerance (<code>duplicate_detector.py</code>).", bullet_style))
    story.append(Paragraph("• Expose ML microservice endpoints under <code>/api/v1/ml/*</code> and connect with the property submission pipeline.", bullet_style))
    story.append(Spacer(1, 14))
    
    # Signatures Table
    sig_data = [
        [
            Paragraph("<b>Student Signature:</b>", meta_bold),
            Paragraph("____________________________", meta_style),
            Paragraph("<b>Guide / Supervisor Signature:</b>", meta_bold),
            Paragraph("____________________________", meta_style)
        ],
        [
            Paragraph("<b>Date:</b>", meta_bold),
            Paragraph("28 / 08 / 2026", meta_style),
            Paragraph("<b>Evaluation Status:</b>", meta_bold),
            Paragraph("[  ] Satisfactory &nbsp;&nbsp;&nbsp; [  ] Needs Improvement", meta_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[110, 150, 140, 132])
    sig_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(KeepTogether(sig_table))
    
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated: {filename}")

if __name__ == "__main__":
    output_path = r"C:\Users\Bhargavi Digu Naik\OneDrive\Desktop\SmartEstate_AI_Project_Diary_4.pdf"
    generate_pdf(output_path)
