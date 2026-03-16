import streamlit as st
import pandas as pd
import io
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# 1. SETUP THE BRAIN (Same as your main.py)
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

# 2. THE WEB INTERFACE (Streamlit)
st.set_page_config(page_title="Lead Salvage AI", page_icon="💰")
st.title("Lead Salvage & Recovery Tool")
st.write("Upload your 'dead' leads CSV. We'll find the gold and write the follow-ups.")

uploaded_file = st.file_uploader("Upload your Lead CSV", type=["csv"])


def process_bulk_with_continuation(df):
    all_salvaged = []
    start_index = 0
    total_rows = len(df)
    
    while start_index < total_rows:
        # Send only the portion of the CSV from the last stopping point
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
        
        with st.spinner(f"Processing batch starting at {start_index}..."):
            result = agent.run_sync(prompt)
            batch = result.output
            
            all_salvaged.extend(batch.leads)
            
            if not batch.has_more_leads or batch.last_processed_index >= total_rows - 1:
                break
                
            # Update the pointer for the next API call
            start_index = batch.last_processed_index + 1
            
    return pd.DataFrame([l.model_dump() for l in all_salvaged])



if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if st.button("Recover All Leads"):
        SalvagedLeads = process_bulk_with_continuation(df)
        st.download_button("Download CSV", SalvagedLeads.to_csv(index=False), "recovered.csv")