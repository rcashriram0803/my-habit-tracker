import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION ---
st.set_page_config(page_title="TaskTraQ", page_icon="✅", layout="wide")

# --- CONNECT TO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Load data. If empty, create a starter dataset
    try:
        df = conn.read(worksheet="Sheet1", usecols=[0, 1, 2], ttl=0)
        # If the sheet is brand new/empty
        if df.empty or len(df.columns) < 2:
            raise ValueError("Sheet is empty")
        # Fix date format
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    except:
        # Create initial data structure if sheet is empty
        dates = [datetime.now().date() - timedelta(days=i) for i in range(7)]
        habits = ["Wake up 6am", "Drink Water", "Workout", "Read"]
        data = [{'Date': d, 'Habit': h, 'Completed': False} for d in dates for h in habits]
        df = pd.DataFrame(data)
        # Convert date to string for saving
        save_df = df.copy()
        save_df['Date'] = save_df['Date'].astype(str)
        conn.update(worksheet="Sheet1", data=save_df)
        return df

def update_data(df):
    # Save changes to Google Sheets
    save_df = df.copy()
    save_df['Date'] = save_df['Date'].astype(str)
    conn.update(worksheet="Sheet1", data=save_df)
    st.toast("Saved successfully!", icon="✅")

# --- APP UI ---
st.title("💪 My Daily Habit Tracker")

# 1. Load Data
df = get_data()

# 2. Check if today exists, if not, add it
today = datetime.now().date()
if today not in df['Date'].values:
    unique_habits = df['Habit'].unique()
    new_rows = [{'Date': today, 'Habit': h, 'Completed': False} for h in unique_habits]
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    update_data(df)
    st.rerun()

# 3. Sidebar - Add New Habit
with st.sidebar:
    st.header("Manage Habits")
    new_h = st.text_input("New Habit Name")
    if st.button("Add Habit"):
        if new_h:
            # Add this habit for all recorded dates
            dates = df['Date'].unique()
            new_rows = [{'Date': d, 'Habit': new_h, 'Completed': False} for d in dates]
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            update_data(df)
            st.rerun()

# 4. Main Dashboard - The Grid
st.subheader("Your Week")

# Prepare data for the grid view
days_to_show = 7
start_date = today - timedelta(days=days_to_show-1)
mask = (df['Date'] >= start_date) & (df['Date'] <= today)
current_df = df.loc[mask].copy()

# Pivot to make it look like a spreadsheet
pivot_df = current_df.pivot(index='Habit', columns='Date', values='Completed')
pivot_df.columns = [d.strftime('%a %d') for d in pivot_df.columns] # Rename columns to "Mon 01"

# Show the editable grid
edited_df = st.data_editor(
    pivot_df,
    column_config={col: st.column_config.CheckboxColumn(col, default=False) for col in pivot_df.columns},
    use_container_width=True,
    height=400
)

# 5. Save Logic
if not pivot_df.equals(edited_df):
    # If changes detected, convert back to format for Google Sheets
    date_map = {d.strftime('%a %d'): d for d in pd.date_range(start=start_date, end=today).date}
    
    for habit in edited_df.index:
        for col_name, is_done in edited_df.loc[habit].items():
            real_date = date_map.get(col_name)
            if real_date:
                # Update the specific row in main dataframe
                condition = (df['Date'] == real_date) & (df['Habit'] == habit)
                df.loc[condition, 'Completed'] = is_done
    
    update_data(df)

# 6. Analytics
st.divider()
score = (df['Completed'].sum() / len(df)) * 100
st.metric("Total Consistency Score", f"{score:.1f}%")
