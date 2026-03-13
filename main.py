import os
import csv
from datetime import datetime
from pydantic import BaseModel
from pydantic_ai import Agent

class LeadEvaluation(BaseModel):
    older_than_4_months: bool
    response: str

agent = Agent('gemini-1.5-flash', result_type=LeadEvaluation)

def process_leads(input_file, output_file):
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        with open(input_file, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            # Add the new column for the output CSV
            fieldnames = reader.fieldnames + ['personalized_response']
            
            with open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in reader:
                    prompt = f"""
Today's date is {today}.
Here is a row of data representing a sales lead (columns might be sparse or arbitrary):
{row}

Task:
1. Figure out if this lead was last contacted strictly MORE than 4 months ago.
2. If yes, write a short, friendly 2-3 sentence personalized re-engagement message asking for a quick call or coffee. Use any available notes. If there are no notes or they are empty, default to: "Hi [Name/there], it's been a few months since we last connected. I'd love to grab a quick coffee or call to see what you're up to lately!"
"""
                    try:
                        result = agent.run_sync(prompt)
                        
                        if result.data.older_than_4_months:
                            row['personalized_response'] = result.data.response
                            writer.writerow(row)
                            print(f"Kept lead: {row.get('name', 'Unknown')}")
                        else:
                            print(f"Skipped lead: {row.get('name', 'Unknown')} (recent contact)")
                            
                    except Exception as e:
                        print(f"Error processing row {row}: {e}")

        print(f"Successfully processed leads. Output saved to {output_file}")
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")

if __name__ == "__main__":
    INPUT_CSV = "input_leads.csv"
    OUTPUT_CSV = "filtered_leads_output.csv"
    
    process_leads(INPUT_CSV, OUTPUT_CSV)
