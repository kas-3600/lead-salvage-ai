import streamlit as st
import pandas as pd
import io
from datetime import datetime
from pydantic import BaseModel
from pydantic_ai import Agent

# 1. SETUP THE BRAIN (Same as your main.py)
class LeadEvaluation(BaseModel):
    older_than_4_months: bool
    response: str

agent = Agent('gemini-1.5-flash', output_type=LeadEvaluation)

# 2. THE WEB INTERFACE (Streamlit)
st.set_page_config(page_title="Lead Salvage AI", page_icon="💰")
st.title("Lead Salvage & Recovery Tool")
st.write("Upload your 'dead' leads CSV. We'll find the gold and write the follow-ups.")

uploaded_file = st.file_uploader("Upload your Lead CSV", type=["csv"])

if uploaded_file is not None:
    # Read the CSV into memory
    df = pd.read_csv(uploaded_file)
    st.write(f"Loaded {len(df)} leads. Ready to process.")
    
    if st.button("Start Lead Recovery"):
        today = datetime.now().strftime("%Y-%m-%d")
        processed_rows = []
        
        # Progress Bar for user feedback
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            prompt = f"Today's date is {today}. Lead data: {row_dict}. Task: 1. Contacted >4 months ago? 2. If yes, write a 2-3 sentence personalized re-engagement message."
            
            try:
                # Sync run for simplicity; progress bar updates each loop
                result = agent.run_sync(prompt)
                
                if result.data.older_than_4_months:
                    row_dict['personalized_response'] = result.data.response
                    processed_rows.append(row_dict)
                
                # Update UI
                progress = (index + 1) / len(df)
                progress_bar.progress(progress)
                status_text.text(f"Processing lead {index + 1} of {len(df)}...")
                
            except Exception as e:
                st.error(f"Error on row {index}: {e}")

        # 3. CREATE ENTIRELY NEW OUTPUT
        if processed_rows:
            output_df = pd.DataFrame(processed_rows)
            
            # Convert DF to CSV in memory for download
            csv_buffer = io.StringIO()
            output_df.to_csv(csv_buffer, index=False)
            csv_output = csv_buffer.getvalue()
            
            st.success(f"Recovery Complete! Found {len(output_df)} lost opportunities.")
            
            # THE DOWNLOAD BUTTON
            st.download_button(
                label="Download Recovered Leads CSV",
                data=csv_output,
                file_name=f"recovered_leads_{today}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No leads found matching the >4 month criteria.")