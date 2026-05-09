import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import zipfile
import tempfile
import io

def generate_subtopic_chart(df_student, student_name, return_fig=False):
    if df_student.empty:
        return None
    
    # Calculate average scores per Category and Subtopic
    avg_scores = df_student.groupby(['Category', 'Subtopic'])['Score'].mean().reset_index()
    
    fig = px.bar(
        avg_scores, 
        x="Subtopic", 
        y="Score", 
        color="Category",
        facet_col="Category",
        facet_col_wrap=2,
        title=f"Detailed Skill Breakdown: {student_name}",
        height=600
    )
    
    fig.update_yaxes(range=[0, 10])
    # Unlink x-axes so each category shows only its own subtopics
    fig.update_xaxes(matches=None)
    fig.update_layout(showlegend=False, margin=dict(t=50, l=20, r=20, b=50))
    
    if return_fig:
        return fig
        
    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    fig.write_image(temp_img.name, width=700, height=500)
    return temp_img.name

class PDF(FPDF):
    def header(self):
        # Colorful Header
        self.set_fill_color(99, 102, 241) # #6366f1
        self.rect(0, 0, 210, 30, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'TutorPro Daily Progress Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, 'Page ' + str(self.page_no()), 0, 0, 'C')

def generate_student_pdf(student_name, df_student, remarks, start_date, end_date):
    pdf = PDF()
    pdf.add_page()
    
    # Title section
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, f'Student: {student_name}', 0, 1)
    
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 10, f'Period: {start_date} to {end_date}', 0, 1)
    pdf.ln(5)
    
    # Charts
    chart_path = generate_subtopic_chart(df_student, student_name)
    
    if chart_path:
        pdf.image(chart_path, x=10, y=pdf.get_y(), w=190)
        
    pdf.ln(110) # Move below charts
    
    # Level Progress
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, 'Level Progress (Current out of 32):', 0, 1)
    
    pdf.set_font('Arial', '', 12)
    if not df_student.empty:
        latest_levels = df_student.sort_values('Date').groupby('Category').last()['Level']
        for cat in ['Reading', 'Writing', 'Speaking', 'Listening']:
            lvl = latest_levels.get(cat, 1)
            pdf.cell(0, 8, f"{cat}: Level {lvl}/32", 0, 1)
    else:
        pdf.cell(0, 8, "No data available.", 0, 1)
    
    pdf.ln(5)

    # Scores Table
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, 'Recent Scores:', 0, 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 10, 'Date', 1)
    pdf.cell(25, 10, 'Category', 1)
    pdf.cell(45, 10, 'Subtopic', 1)
    pdf.cell(15, 10, 'Lvl', 1)
    pdf.cell(15, 10, 'Score', 1)
    pdf.cell(65, 10, 'Note', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 9)
    # Sort by date descending and take last 10
    recent_logs = df_student.sort_values('Date', ascending=False).head(10)
    for index, row in recent_logs.iterrows():
        pdf.cell(25, 10, str(row['Date'])[:10], 1)
        pdf.cell(25, 10, str(row['Category'])[:10], 1)
        sub = str(row.get('Subtopic', 'General'))
        pdf.cell(45, 10, sub[:25], 1)
        lvl = str(row.get('Level', 1))
        pdf.cell(15, 10, lvl, 1)
        pdf.cell(15, 10, str(row['Score']), 1)
        note_str = str(row['Note']) if pd.notnull(row['Note']) else ""
        pdf.cell(65, 10, note_str[:30], 1)
        pdf.ln()
        
    pdf.ln(10)
    
    # Remarks
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Teacher's Remarks:", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 8, remarks)
    
    # Clean up temp files
    if chart_path and os.path.exists(chart_path): os.remove(chart_path)
    
    # Output to byte string
    return pdf.output(dest='S').encode('latin1')

def generate_zip_reports(roster_df, logs_df, remarks_dict, start_date, end_date):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for index, student in roster_df.iterrows():
            s_id = student['ID']
            s_name = student['Name']
            df_s = logs_df[logs_df['ID'] == s_id]
            remarks = remarks_dict.get(s_id, "Keep up the good work!")
            
            pdf_bytes = generate_student_pdf(s_name, df_s, remarks, start_date, end_date)
            zip_file.writestr(f"{s_name.replace(' ', '_')}_Report.pdf", pdf_bytes)
            
    return zip_buffer.getvalue()
