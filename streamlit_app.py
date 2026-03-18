import streamlit as st
import pandas as pd
import io
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from st_supabase_connection import SupabaseConnection



# 1. SETUP THE BRAIN 
class SalvagedLead(BaseModel):
    index: int = Field(description="The original row index from the CSV + 1")
    name: str
    phone: str = Field(description="The phone number, if available")
    email: str = Field(description="The email address, if available")
    address: str = Field(description="The address, if available")
    zip_code: str = Field(description="The zip code, if available")
    original_notes: str = Field(description="The original notes from the CSV for this lead")
    last_serviced_date: str = Field(description="The last date this lead was serviced, in YYYY-MM-DD format")
    last_serviced_date_ago: str = Field(description="How long ago the last service date was, in months")
    personalized_response: str

class SalvageBatch(BaseModel):
    leads: List[SalvagedLead]
    last_processed_index: int
    has_more_leads: bool = Field(description="Set to true if there are more rows left to process that didn't fit in this response")

agent = Agent("google-gla:gemini-3-flash-preview", output_type=SalvageBatch)



# SETUP SUPABASE CONNECTION 
conn = st.connection("supabase", type=SupabaseConnection)



# 2. THE WEB INTERFACE
st.set_page_config(page_title="Lead Salvage AI", page_icon="💰")
st.title("Lead Salvage & Recovery Tool")



# --- LICENSE GATE LOGIC ---
st.sidebar.header("Access Control")
user_key = st.sidebar.text_input("Enter License Key", type="password")

def verify_license(key: str) -> bool:
    if not key:
        return False
    # Logic: Query Supabase for the key where status is active
    res = conn.table("Clients").select("status").eq("license_key", key).eq("status", "active").execute()
    return len(res.data) > 0

if not verify_license(user_key):
    st.warning("Please enter a valid, active license key.")
    st.markdown("[Buy a License Key here](https://buy.stripe.com/6oU00igzTaRb6dDe7i2Ji00)")
    st.stop()



# App only renders past this point if authorized
st.write("Upload your 'dead' leads CSV. We'll find the gold and write the follow-ups.")
uploaded_file = st.file_uploader("Upload your Lead CSV", type=["csv"])

def process_bulk_with_continuation(df):
    all_salvaged = []
    start_index = 0
    total_rows = len(df)
    
    # Initialize Progress UI
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    
    while start_index < total_rows:
        # Interpolate progress safely
        current_progress = min(start_index / total_rows, 1.0)
        progress_bar.progress(current_progress)
        status_text.text(f"Processing rows {start_index} to {total_rows}...")

        remaining_data = df.iloc[start_index:].to_csv(index=True)
        
        prompt = f"""
        Analyze these leads. 
        Current Progress: Starting from row index {start_index}.
        
        TASK:
        1. Identify leads not contacted in >4 months.
        2. Write personalized responses.
        3. If you are approaching your output token limit, STOP, set 'has_more_leads' to true, and report the 'last_processed_index'.
        
        DATA:
        {remaining_data}
        """
        
        result = agent.run_sync(prompt)
        batch = result.output
        
        all_salvaged.extend(batch.leads)
        
        if not batch.has_more_leads or batch.last_processed_index >= total_rows - 1:
            break
            
        start_index = batch.last_processed_index + 1
        
    # Snap to 100% on completion
    progress_bar.progress(1.0)
    status_text.text(f"Complete! Extracted {len(all_salvaged)} leads.")
    
    return pd.DataFrame([l.model_dump() for l in all_salvaged])



if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if st.button("Recover All Leads"):
        SalvagedLeads = process_bulk_with_continuation(df)
        st.download_button(
            label="Download Recovered CSV", 
            data=SalvagedLeads.to_csv(index=False), 
            file_name="recovered.csv",
            mime="text/csv")