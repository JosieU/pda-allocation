import streamlit as st
import pandas as pd
import sqlite3
import os

# --- CONFIGURATION ---
DB_PATH = "task_allocations.db"
TABLE_NAME = "allocations"

# --- PAGE SETUP ---
st.set_page_config(page_title="Task Allocations", layout="wide")
st.title("📋 PDA Allocation Viewer")

# --- Upload Excel File ---
uploaded_file = st.file_uploader("Excell File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, header=0)
    df.columns = df.columns.str.strip()  # Remove extra spaces

    expected_cols = [
        "Date", "Total Hours", "Team members",
        "1st Task Allocation", "Time Allocation 1",
        "2nd Task Allocation", "Time Allocation 2"
    ]

    missing_cols = [col for col in expected_cols if col not in df.columns]

    if missing_cols:
        st.error(f"❌ Missing columns: {missing_cols}")
        st.write("Detected columns:", df.columns.tolist())
        st.stop()

    df = df[expected_cols]
    df.fillna("", inplace=True)

    conn = sqlite3.connect(DB_PATH)

    # Load existing data from the database
    if TABLE_NAME in pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)["name"].values:
        existing_df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
        existing_df["Date"] = pd.to_datetime(existing_df["Date"]).dt.date
    else:
        existing_df = pd.DataFrame(columns=df.columns)

    # Ensure the uploaded 'Date' column is datetime.date for comparison
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # Remove duplicates based on Date + Team members (can expand to more columns if needed)
    dedup_df = df[~df.set_index(["Date", "Team members"]).index.isin(
        existing_df.set_index(["Date", "Team members"]).index
    )]

    if not dedup_df.empty:
        dedup_df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
        st.success(f"✅ {len(dedup_df)} new rows saved to the database.")
    else:
        st.info("ℹ️ No new data to insert — all rows already exist.")

    conn.close()

# --- Load and Display by Calendar Selection ---
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
    conn.close()

    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"]).dt.date

        st.markdown("### 📅 Select up to 2 dates")
        selected_dates = st.date_input("Pick date(s)", [], key="multi_date")

        if selected_dates:
            if len(selected_dates) > 2:
                st.warning("⚠️ You can only select up to 2 dates.")
            else:
                found = False
                for date in selected_dates:
                    date_df = df[df["Date"] == date]
                    if date_df.empty:
                        st.info(f"ℹ️ No data found for {date}")
                    else:
                        found = True
                        st.subheader(f"📋 Allocations for {date}")
                        st.dataframe(date_df.reset_index(drop=True), use_container_width=True)

                if not found:
                    st.warning("⚠️ No data matched the selected date(s).")
    else:
        st.info("📂 No data found in the database.")
else:
    st.info("📂 Please upload a task allocation Excel file to begin.")
