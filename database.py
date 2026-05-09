import streamlit as st
import pandas as pd
import os
from datetime import datetime

DB_FILE = "TutorPro_DB.xlsx"
NEW_LOGS_SHEET = "PortfolioLogs"

def init_db():
    if not os.path.exists(DB_FILE):
        roster_df = pd.DataFrame(columns=["ID", "Name", "Grade", "EnrollmentDate"])
        logs_df = pd.DataFrame(columns=["Date", "ID", "Category", "Set", "PhotoPath", "PDFPath", "Remarks"])
        settings_df = pd.DataFrame(columns=["Setting", "Value"])
        
        with pd.ExcelWriter(DB_FILE) as writer:
            roster_df.to_excel(writer, sheet_name="Roster", index=False)
            logs_df.to_excel(writer, sheet_name=NEW_LOGS_SHEET, index=False)
            settings_df.to_excel(writer, sheet_name="Settings", index=False)
    else:
        # Ensure PortfolioLogs exists in existing DB
        try:
            pd.read_excel(DB_FILE, sheet_name=NEW_LOGS_SHEET)
        except ValueError:
            logs_df = pd.DataFrame(columns=["Date", "ID", "Category", "Set", "PhotoPath", "PDFPath", "Remarks"])
            with pd.ExcelWriter(DB_FILE, mode='a', engine='openpyxl') as writer:
                logs_df.to_excel(writer, sheet_name=NEW_LOGS_SHEET, index=False)

@st.cache_data(ttl=5) # Short TTL for dev
def load_roster():
    init_db()
    return pd.read_excel(DB_FILE, sheet_name="Roster")

@st.cache_data(ttl=5)
def load_logs():
    init_db()
    df = pd.read_excel(DB_FILE, sheet_name=NEW_LOGS_SHEET)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

def save_roster(df):
    logs_df = load_logs()
    settings_df = pd.read_excel(DB_FILE, sheet_name="Settings")
    with pd.ExcelWriter(DB_FILE) as writer:
        df.to_excel(writer, sheet_name="Roster", index=False)
        logs_df.to_excel(writer, sheet_name=NEW_LOGS_SHEET, index=False)
        settings_df.to_excel(writer, sheet_name="Settings", index=False)
    st.cache_data.clear()

def save_logs(new_logs_df):
    roster_df = load_roster()
    settings_df = pd.read_excel(DB_FILE, sheet_name="Settings")
    
    existing_logs = load_logs()
    updated_logs = pd.concat([existing_logs, new_logs_df], ignore_index=True)
    
    with pd.ExcelWriter(DB_FILE) as writer:
        roster_df.to_excel(writer, sheet_name="Roster", index=False)
        updated_logs.to_excel(writer, sheet_name=NEW_LOGS_SHEET, index=False)
        settings_df.to_excel(writer, sheet_name="Settings", index=False)
    st.cache_data.clear()
