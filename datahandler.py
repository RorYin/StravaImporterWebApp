import json
import pandas as pd
from openpyxl import load_workbook



def processdata(json_data, athlete_name,output_file):

    # Load existing data from the Excel file if it exists
    try:
        existing_df = pd.read_excel(output_file)
    except FileNotFoundError:
        existing_df = pd.DataFrame()  # If file does not exist, create an empty DataFrame

    # Create a dictionary to store the combined data
    combined_data = {}

    for entry in json_data:
        activity_name = entry.get('name')
        activity_type = entry.get('type')
        athlete_id = entry.get('athlete', {}).get('id')
        distance = entry.get('distance')
        try:
            pace = (entry.get('moving_time') / 60) / (entry.get('distance') / 1000)
        except:
            continue
        date = (entry["start_date"]).split("T")[0]
        unit = "Km"
        date_str = f"{date}"

        # Print the extracted data
        # print(f"Athlete Name: {athlete_name} Athlete ID: {athlete_id} Activity Type: {activity_type} Activity Name: {activity_name}, Distance: {distance} meters Date: {date} Pace; {pace}")

        # Only consider activities where the pace is greater than 4.5
        if pace and pace > 4.5:
            if date_str not in combined_data:
                combined_data[date_str] = {
                    'Athlete Name': athlete_name,
                    'Athlete ID': athlete_id,
                    'Date': date_str,
                    'Total Distance': 0,
                    'Activities': []
                }

            # Sum the distance for the day
            combined_data[date_str]['Total Distance'] += (distance / 1000)

            # Store activity details
            combined_data[date_str]['Activities'].append({
                'Activity Name': activity_name,
                'Distance': distance,
                'Pace': pace
            })

    # Convert the combined data to a list of dictionaries for DataFrame creation
    data_list = []
    for date_str, data in combined_data.items():
        data_list.append({
            'Athlete Name': data['Athlete Name'],
            'Athlete ID': data['Athlete ID'],
            'Date': data['Date'],
            'Total Distance': data['Total Distance'],
            'Activities': "; ".join([f"{a['Activity Name']} ({a['Distance']}m, Pace: {a['Pace']:.2f})" for a in data['Activities']])
        })

    # Create a pandas DataFrame from the new data
    new_df = pd.DataFrame(data_list)

    # Combine with existing data
    if not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        # Remove duplicates based on 'Athlete ID' and 'Date'
        combined_df.drop_duplicates(subset=['Athlete ID', 'Date'], keep='last', inplace=True)
    else:
        combined_df = new_df

    # Save the DataFrame to the Excel file
    combined_df.to_excel(output_file, index=False)



