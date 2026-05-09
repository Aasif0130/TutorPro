import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from datetime import datetime, timedelta
import os
import random

from auth import check_password
import database
import reports

# Constants for Categories and Subtopics
CATEGORIES = {
    "Reading": ["Letter sounds", "Blending", "Sight words", "Fluency", "Comprehension"],
    "Writing": ["Letter formation", "Spelling", "Sentence writing", "Dictation", "Handwriting"],
    "Speaking": ["Pronunciation", "Vocabulary", "Conversation", "Confidence", "Storytelling"],
    "Listening": ["Following instructions", "Sound recognition", "Listening comprehension", "Attention", "Response"]
}

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
        sac.MenuItem('Weekly Reports', icon='calendar-week'),
        sac.MenuItem('Monthly Analytics', icon='graph-up'),
        sac.MenuItem('Settings', icon='gear-fill'),
    ], size='md', variant='filled', color='indigo')
    
    st.divider()
    
    # Demo Mode Toggle
    demo_mode = st.toggle('🧪 Preview Mode (Demo Data)')
    
    st.divider()
    
    st.download_button(
        label="Download Local Database",
        data=open("TutorPro_DB.xlsx", "rb").read() if os.path.exists("TutorPro_DB.xlsx") else b"",
        file_name="TutorPro_DB.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# --- Demo Data Generator ---
def generate_demo_logs(student_id, days=30):
    demo_logs = []
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=days)
    current = start_date
    while current <= end_date:
        for cat, subtopics in CATEGORIES.items():
            for sub in subtopics:
                demo_logs.append({
                    "Date": current,
                    "ID": student_id,
                    "Category": cat,
                    "Subtopic": sub,
                    "Level": random.randint(1, 32),
                    "Score": random.randint(6, 10),
                    "Note": "Demo note"
                })
        current += timedelta(days=1)
    return pd.DataFrame(demo_logs)

# --- View Routing ---

if menu == 'Dashboard':
    st.title("Good Morning, Teacher! ☀️")
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
    st.title("📝 The Teacher's Desk")
    st.markdown("Quickly enter daily scores and update levels using this smart grid matrix.")
    
    if roster_df.empty:
        st.warning("Please add students in the Dashboard first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("Date", datetime.today())
        with col2:
            selected_cat = st.selectbox("Select Category", list(CATEGORIES.keys()))
            
        st.markdown(f"### 📊 Enter Scores for {selected_cat} (1-10)")
        
        # Prepare wide data editor frame
        wide_data = []
        for index, student in roster_df.iterrows():
            row_data = {
                "Student": student['Name'],
                "Level (1-32)": 1 # Default, ideally fetched from last entry
            }
            # Add subtopics
            for sub in CATEGORIES[selected_cat]:
                row_data[sub] = None
            row_data["Note"] = ""
            wide_data.append(row_data)
            
        editor_df = pd.DataFrame(wide_data)
        
        # Config columns
        col_config = {
            "Student": st.column_config.TextColumn("Student Name", disabled=True),
            "Level (1-32)": st.column_config.NumberColumn("Level (1-32)", min_value=1, max_value=32, step=1),
            "Note": st.column_config.TextColumn("General Note", width="large")
        }
        for sub in CATEGORIES[selected_cat]:
            col_config[sub] = st.column_config.NumberColumn(sub, min_value=1, max_value=10, step=1)
            
        edited_df = st.data_editor(
            editor_df,
            column_config=col_config,
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Sync to Local Database", type="primary"):
            with st.status("Melting matrix and syncing to database...", expanded=True) as status:
                name_to_id = dict(zip(roster_df['Name'], roster_df['ID']))
                
                new_logs = []
                for index, row in edited_df.iterrows():
                    s_id = name_to_id.get(row['Student'])
                    if s_id:
                        for sub in CATEGORIES[selected_cat]:
                            score = row[sub]
                            if pd.notnull(score):
                                new_logs.append({
                                    "Date": entry_date,
                                    "ID": s_id,
                                    "Category": selected_cat,
                                    "Subtopic": sub,
                                    "Level": int(row['Level (1-32)']),
                                    "Score": int(score),
                                    "Note": row['Note']
                                })
                
                if new_logs:
                    new_logs_df = pd.DataFrame(new_logs)
                    database.save_logs(new_logs_df)
                    status.update(label="Sync complete!", state="complete", expanded=False)
                    st.success(f"Successfully synced {len(new_logs)} entries for {entry_date}.")
                else:
                    status.update(label="No valid scores entered.", state="error", expanded=False)
                    st.warning("Please enter at least one score before syncing.")

elif menu == 'Weekly Reports':
    st.title("📅 Weekly Reporting")
    st.markdown("Generate Glows, Grows, and comprehensive PDFs for the past 7 days.")
    
    if roster_df.empty:
        st.warning("Please add students in the Dashboard first.")
    else:
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=7)
        
        st.info(f"Reporting Period: **{start_date} to {end_date}**")
        
        remarks_dict = {}
        
        tabs = st.tabs(roster_df['Name'].tolist())
        
        for idx, (student_idx, student) in enumerate(roster_df.iterrows()):
            with tabs[idx]:
                s_id = student['ID']
                s_name = student['Name']
                
                if demo_mode:
                    df_s = generate_demo_logs(s_id, days=7)
                else:
                    df_s = logs_df[(logs_df['ID'] == s_id) & (logs_df['Date'] >= start_date) & (logs_df['Date'] <= end_date)]
                
                if df_s.empty:
                    st.write("No entries this week.")
                    remarks_dict[s_id] = "No entries recorded for this period."
                else:
                    avg_score = df_s['Score'].mean()
                    st.metric("Weekly Average Score", f"{avg_score:.1f}/10")
                    
                    if avg_score >= 8:
                        default_remark = "Mastery demonstrated! Great focus and excellent performance this week. Keep up the momentum!"
                    elif avg_score < 5:
                        default_remark = "Needs Focus. We will work on solidifying foundational concepts next week."
                    else:
                        default_remark = "Steady progress. Consistent effort shown this week."
                        
                    remarks = st.text_area(f"Glows and Grows for {s_name}", value=default_remark, key=f"remark_{s_id}")
                    remarks_dict[s_id] = remarks
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(f"Generate {s_name}'s PDF Report", key=f"gen_{s_id}"):
                        with st.spinner("Generating PDF..."):
                            pdf_bytes = reports.generate_student_pdf(s_name, df_s, remarks, start_date, end_date)
                        st.download_button(
                            label=f"Download {s_name}_Report.pdf",
                            data=pdf_bytes,
                            file_name=f"{s_name.replace(' ', '_')}_Report.pdf",
                            mime="application/pdf",
                            type="primary",
                            key=f"dl_btn_{s_id}"
                        )
                    
        st.divider()
        if st.button("Generate & Zip All Reports", type="primary"):
            with st.spinner("Generating beautiful PDFs..."):
                logs_to_pass = logs_df
                if demo_mode:
                    demo_list = []
                    for s in roster_df['ID']:
                        demo_list.append(generate_demo_logs(s, days=7))
                    if demo_list:
                        logs_to_pass = pd.concat(demo_list, ignore_index=True)

                zip_data = reports.generate_zip_reports(roster_df, logs_to_pass, remarks_dict, start_date, end_date)
                
            st.success("Reports generated successfully!")
            st.download_button(
                label="Download ZIP Archive",
                data=zip_data,
                file_name=f"TutorPro_Reports_{start_date}_to_{end_date}.zip",
                mime="application/zip",
                type="primary"
            )

elif menu == 'Monthly Analytics':
    st.title("📈 Monthly Analytics")
    st.markdown("Analyze growth trends and skill balances over a 4-week period.")
    
    if roster_df.empty:
        st.warning("Please add students in the Dashboard first.")
    else:
        student_name = st.selectbox("Select Student", roster_df['Name'].tolist())
        student_id = roster_df[roster_df['Name'] == student_name].iloc[0]['ID']
        
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=28)
        
        if demo_mode:
            df_s = generate_demo_logs(student_id, days=28)
        else:
            df_s = logs_df[(logs_df['ID'] == student_id) & (logs_df['Date'] >= start_date) & (logs_df['Date'] <= end_date)]
        
        if df_s.empty:
            st.warning(f"No data found for {student_name} in the last 28 days. Turn on Demo Mode to preview.")
        else:
            st.plotly_chart(reports.generate_subtopic_chart(df_s, student_name, return_fig=True), use_container_width=True)
            
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
