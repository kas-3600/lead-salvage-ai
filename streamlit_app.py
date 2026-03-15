import streamlit as st
import pandas as pd
import io
from datetime import datetime
from pydantic import BaseModel
from pydantic_ai import Agent

# 1. SETUP THE BRAIN (Same as your main.py)
class SalvagedLead(BaseModel):
    name: str
    email: str
    original_row_index: int  # To map back if needed
    personalized_response: str

agent = Agent("google-gla:gemini-3-flash-preview", output_type=SalvagedLead)

# 2. THE WEB INTERFACE (Streamlit)
st.set_page_config(page_title="Lead Salvage AI", page_icon="💰")
st.title("Lead Salvage & Recovery Tool")
st.write("Upload your 'dead' leads CSV. We'll find the gold and write the follow-ups.")

uploaded_file = st.file_uploader("Upload your Lead CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    csv_string = df.to_csv(index=False) # Convert entire sheet to string
    
    if st.button("Recover All Leads"):
        with st.spinner("AI is processing the entire database..."):
            prompt = f"""
            Analyze this CSV data. 
            Identify every lead not contacted in >4 months. 
            For each one, write a 2-3 sentence personalized follow-up.
            Return the results as a list of salvaged leads.
            
            CSV DATA:
            {csv_string}
            """
            
            result = agent.run_sync(prompt)
            
            # Convert the list of Pydantic objects back into a DataFrame
            output_df = pd.DataFrame([lead.model_dump() for lead in result.data.leads])
            
            st.success(f"Found {len(output_df)} leads!")
            st.dataframe(output_df)
            
            st.download_button("Download CSV", output_df.to_csv(index=False), "recovered.csv")