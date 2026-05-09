import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from datetime import datetime
import os

from auth import check_password
import database
import reports

# --- Page Config ---
st.set_page_config(
    page_title="TutorPro Daily",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load Custom CSS ---
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# --- Authentication ---
if not check_password():
    st.stop()

# --- Load Data ---
roster_df = database.load_roster()
logs_df = database.load_logs()

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("### 📚 TutorPro Daily")
    menu = sac.menu([
        sac.MenuItem('Dashboard', icon='house-fill'),
        sac.MenuItem('Daily Entry', icon='pencil-square'),
        sac.MenuItem('Settings', icon='gear-fill'),
    ], size='md', variant='filled', color='indigo')
    
    st.divider()
    
    st.download_button(
        label="Download Local Database",
        data=open("TutorPro_DB.xlsx", "rb").read() if os.path.exists("TutorPro_DB.xlsx") else b"",
        file_name="TutorPro_DB.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# --- View Routing ---

if menu == 'Dashboard':
    st.title("Good Morning, Parvin Banu! ☀️")
    st.markdown("Manage your dynamic student roster here.")
    
    # Dashboard Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Students", len(roster_df))
    col2.metric("Active Grades", roster_df['Grade'].nunique() if not roster_df.empty else 0)
    col3.metric("Total Records Synced", len(logs_df))
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🧑‍🎓 Your Students")
        if roster_df.empty:
            st.info("Your roster is currently empty. Add a student to get started!")
        else:
            st.dataframe(roster_df, use_container_width=True, hide_index=True)
            
    with col2:
        with st.container(border=True):
            st.markdown("### ➕ Add New Student")
            with st.form("add_student_form"):
                new_name = st.text_input("Full Name")
                new_grade = st.selectbox("Grade Level", ["Kindergarten", "Grade 1", "Grade 2", "Grade 3"])
                submitted = st.form_submit_button("Add to Roster", type="primary")
                
                if submitted:
                    if new_name.strip() == "":
                        st.error("Please enter a valid name.")
                    else:
                        new_id = f"S{len(roster_df) + 1:03d}"
                        new_student = pd.DataFrame([{
                            "ID": new_id,
                            "Name": new_name,
                            "Grade": new_grade,
                            "EnrollmentDate": datetime.today().date().isoformat()
                        }])
                        updated_roster = pd.concat([roster_df, new_student], ignore_index=True)
                        database.save_roster(updated_roster)
                        st.success(f"Added {new_name} to the roster!")
                        st.rerun()

elif menu == 'Daily Entry':
    st.title("📝 Daily Tracker & Portfolio")
    st.markdown("Select a student, upload their work, and generate a report.")
    
    if roster_df.empty:
        st.warning("Please add students in the Dashboard first.")
    else:
        student_names = roster_df['Name'].tolist()
        
        with st.form("daily_entry_form"):
            col1, col2 = st.columns(2)
            with col1:
                entry_date = st.date_input("Date", datetime.today())
                selected_student = st.selectbox("Student", student_names)
                selected_cat = st.selectbox("Category", ["Reading", "Writing", "Speaking", "Listening"])
            with col2:
                set_num = st.number_input("Set (1-32)", min_value=1, max_value=32, step=1)
                
            st.divider()
            st.markdown("### 📸 Uploads")
            col_img, col_pdf = st.columns(2)
            with col_img:
                photo_file = st.file_uploader("Upload Student Work (Image)", type=["jpg", "jpeg", "png"])
            with col_pdf:
                pdf_file = st.file_uploader("Upload Worksheet (PDF)", type=["pdf"])
                
            st.divider()
            remarks = st.text_area("Teacher's Remarks", height=150)
            
            submitted = st.form_submit_button("Save Entry & Generate Report", type="primary")
            
            if submitted:
                os.makedirs("uploads", exist_ok=True)
                
                photo_path = None
                if photo_file:
                    photo_path = os.path.join("uploads", f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo_file.name}")
                    with open(photo_path, "wb") as f:
                        f.write(photo_file.getbuffer())
                        
                pdf_path = None
                if pdf_file:
                    pdf_path = os.path.join("uploads", f"pdf_{datetime.now().strftime('%Y%m%d%H%M%S')}_{pdf_file.name}")
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                        
                s_id = roster_df[roster_df['Name'] == selected_student].iloc[0]['ID']
                
                new_log = pd.DataFrame([{
                    "Date": entry_date,
                    "ID": s_id,
                    "Category": selected_cat,
                    "Set": set_num,
                    "PhotoPath": photo_path if photo_path else "",
                    "PDFPath": pdf_path if pdf_path else "",
                    "Remarks": remarks
                }])
                database.save_logs(new_log)
                st.success("Entry saved successfully to the database!")
                
                # Generate PDF
                with st.spinner("Merging PDF Report..."):
                    try:
                        pdf_bytes = reports.generate_daily_report_pdf(
                            student_name=selected_student,
                            date=entry_date.strftime("%Y-%m-%d"),
                            category=selected_cat,
                            set_num=set_num,
                            remarks=remarks,
                            photo_path=photo_path,
                            pdf_path=pdf_path
                        )
                        st.session_state['last_pdf'] = pdf_bytes
                        st.session_state['last_pdf_name'] = f"{selected_student.replace(' ', '_')}_{entry_date}_Report.pdf"
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")

        if 'last_pdf' in st.session_state:
            st.markdown("### 🎉 Report Ready!")
            st.download_button(
                label="📥 Download Generated PDF Report",
                data=st.session_state['last_pdf'],
                file_name=st.session_state['last_pdf_name'],
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

elif menu == 'Settings':
    st.title("⚙️ Settings")
    st.markdown("Manage your application settings and raw database.")
    
    st.markdown("### Roster Management")
    if not roster_df.empty:
        st.markdown("#### Delete Students")
        students_to_delete = st.multiselect("Select students to remove from active roster", roster_df['Name'].tolist())
        if st.button("Delete Selected Students", type="primary"):
            if students_to_delete:
                new_roster = roster_df[~roster_df['Name'].isin(students_to_delete)]
                database.save_roster(new_roster)
                st.success(f"Removed {len(students_to_delete)} students successfully!")
                st.rerun()
            else:
                st.warning("Please select at least one student.")
        
        st.divider()
        st.markdown("#### Edit Roster Data")
        edited_roster = st.data_editor(roster_df, num_rows="dynamic", use_container_width=True)
        if st.button("Save Roster Changes"):
            database.save_roster(edited_roster)
            st.success("Roster updated successfully!")
            st.rerun()
    else:
        st.info("Roster is empty.")
