from flask import Flask, redirect, request, session,jsonify,url_for,render_template,send_file
import requests
import os
import json
import time
from datetime import datetime
from datahandler import *
from setup import *
#The below 2 lines to be commented on pythonanywhere, and uncommented if using on local PC
# os.environ['http_proxy'] = ''
# os.environ['https_proxy'] = ''

# JSON file path

DATA_FILE = 'data.json'

# Ensure the data file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as file:
        json.dump([], file)

def load_data(file_path):
    """Load and return the JSON data from a file."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    print(data)
    return data

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = "/home/urpythonanywehere/files"


start_date = "2023-09-18"  # Start date (YYYY-MM-DD)
end_date = "2023-10-18"    # End date (YYYY-MM-DD)

#To get all activities of authorized user from start date to end date
def get_all_activities(access_token, start_date, end_date):
    activities = []
    page = 1
    per_page = 30  # Number of activities per page (maximum is 30)

    # Convert start_date and end_date to Unix timestamps
    after_timestamp = int(time.mktime(datetime.strptime(start_date, "%Y-%m-%d").timetuple()))
    before_timestamp = int(time.mktime(datetime.strptime(end_date, "%Y-%m-%d").timetuple()))

    while True:
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "page": page,
                "per_page": per_page,
                "after": after_timestamp,   # Filter by start date
                "before": before_timestamp  # Filter by end date
            }
        )
        if(response.status_code == 200):
            page_activities = response.json()

            if not page_activities:
                # If the response is empty, we have reached the last page
                break

            activities.extend(page_activities)
            page += 1  # Move to the next page
        else:
            return f"Failed to fetch activities: {response.json()}"

    return activities

# Gets new access token of a user
def refresh_access_token(data_entry):
    # Check if the token is expired
    if time.time() > data_entry['expires_at']:
        print(f"Access token for athlete {data_entry['athlete_id']} expired, refreshing...")

        # Make a request to refresh the access token
        response = requests.post(TOKEN_URL, data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': data_entry['refresh_token']
        })

        if response.status_code == 200:
            new_token_data = response.json()

            # Update the entry with the new token information
            data_entry['access_token'] = new_token_data['access_token']
            data_entry['refresh_token'] = new_token_data['refresh_token']
            data_entry['expires_at'] = new_token_data['expires_at']

            print(f"Access token for athlete {data_entry['athlete_id']} refreshed successfully.")
            return data_entry['access_token']
        else:
            print(f"Failed to refresh access token for athlete {data_entry['athlete_id']}.")
            return None
    else:
        print(f"Access token for athlete {data_entry['athlete_id']} is still valid.")
        return data_entry['access_token']

def remove_athlete_entry(access_token):
    with open(DATA_FILE, 'r+') as file:
        data = json.load(file)

        # Find the athlete by access token and remove them
        athlete = next((item for item in data if item['access_token'] == access_token), None)
        if athlete:
            data.remove(athlete)

            # Save the updated data back to the file
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()
    return

def generate_data():
    with open(DATA_FILE, 'r') as file:
        try:
            users = json.load(file)
        except:
            return "Some error in loading data.json"
        users_len = len(users)
        count = 0
        skipped_users = []
        e_value = None
    for user in users:
        #Refersh access token, if same token is valid, it does not request for new, handled inside function
        new_access_token = refresh_access_token(user)
       # Fetch activities from Strava
        activities = get_all_activities(new_access_token,start_date,end_date)

        # for activity in activities:
        try:
            json_data =  activities
            name = user['name']
            filename = f"{name}.json"
            output_file = app.config['UPLOAD_FOLDER']+"/"+"combined_athlete_activities.xlsx"
            processdata(json_data,name,output_file)
            # Save activities to a JSON file
            with open(filename, 'w') as json_file:
                json.dump(json_data, json_file, indent=4)
            count = count + 1
        except Exception as e:
            skipped_users.append(user['name'])
            e_value = e
            continue

    return render_template("message.html",message = f"Fetched {count} athletes activities from {start_date} to {end_date} out of {users_len} authorized athlets , skipped users: {skipped_users}  exception:{e_value}")

@app.route('/')
def home():
    return render_template("homepage.html")

@app.route('/auth')
def auth():
    return redirect(f"{AUTHORIZE_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=read,activity:read_all&approval_prompt=force")

# Authorize an user and log in his details to json file [working]
@app.route('/authorized')
def authorized():
    code = request.args.get('code')
    scope = request.args.get('scope')
    if not code:
        return render_template("message.html", message="Authorization code not provided.")

    # Request the access token from Strava
    token_response = requests.post(TOKEN_URL, data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    }).json()

    # Debugging: Print the token response to see what is returned
    print("Token Response:", token_response)

    # Check if the access token is in the response
    if 'access_token' in token_response:
        # Check for the necessary scope
        if 'read' == scope:
            return render_template("message.html", message="Error: Required scope 'activity:read_all' not granted. Authorize again by selecting read private activities box.")

        # Store the access token in the session
        session['access_token'] = token_response['access_token']
        session['name'] = f"{token_response['athlete']['firstname']} {token_response['athlete']['lastname']}"
        print(f"Current token: {token_response['access_token']}")

        entry = {
            'name': f"{token_response['athlete']['firstname']} {token_response['athlete']['lastname']}",
            'gender': token_response['athlete']['sex'],
            'refresh_token': token_response['refresh_token'],
            'expires_at': token_response['expires_at'],
            'athlete_id': token_response['athlete']['id'],
            'access_token': token_response['access_token']
        }

        # Load the existing data from the file and update or append the entry
        with open(DATA_FILE, 'r+') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                # If the file is empty or has invalid JSON, start with an empty list
                data = []

            # Update or append the entry
            data = [entry if existing_entry['athlete_id'] == entry['athlete_id'] else existing_entry for existing_entry in data]
            if not any(existing_entry['athlete_id'] == entry['athlete_id'] for existing_entry in data):
                data.append(entry)

            # Write the updated data back to the file
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()

        return render_template("message.html", message=f"Hello {token_response['athlete']['firstname']} {token_response['athlete']['lastname']}, thank you for providing the authorization to read your activity.")
    else:
        try:
            # Handle the error, e.g., display a message or log the error
            error_message = token_response.get('message', 'Unknown error occurred.')
            return render_template("message.html", message=f"Error: {error_message}.")
        except:
            return render_template("message.html", message="Unknown error in auth.")

# Endpoint to deauthorize the user in active session [working]
@app.route('/deauthorize')
def deauthorize():
    access_token = session.get('access_token')

    if not access_token:
        return render_template("message.html",message = "User is not authorized.")

    url = 'https://www.strava.com/oauth/deauthorize'
    response = requests.post(url, params={'access_token': access_token})
    print(f"Token while deauth {access_token}")

    try:
        if response.status_code == 200:
            session.pop('access_token', None)

            # Remove athlete entry from data.json
            remove_athlete_entry(access_token)

            return render_template("message.html",message = f"Deauthorization sucessfull")
        else:
            return render_template("message.html",message = f"Deauthorization failed. Status code: {response.status_code}, Response: {response.json()}")
    except:
            return render_template("message.html",message = f"Deauthorization failed. Status code: {response.status_code}, Response: {response.json()}")

# Endpoint is for fetching activities from start date to end date [working]
@app.route('/activities')
def activities():
    # Get the access token from the session
    access_token = session.get('access_token')

    if not access_token:
        return redirect(url_for('home'))

    # Fetch activities from Strava
    activities = get_all_activities(access_token,start_date,end_date)

    # for activity in activities:
    try:
        json_data =  activities
        name = session['name']
        filename = app.config['UPLOAD_FOLDER']+"/"+f"{session['name']}.json"
        output_file = app.config['UPLOAD_FOLDER']+"/"+f"{session['name']}.xlsx"
        processdata(json_data,name,output_file)
        # Save activities to a JSON file
        with open(filename, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
        return render_template("message.html",message = "Data fetched")
    except:
        return render_template("message.html",message = activities)

@app.route('/activities/<int:athlete_id>', methods=['GET'])
def activitiesbyid(athlete_id):
    # Get the access token from the session
    with open(DATA_FILE, 'r+') as file:
        data = json.load(file)
        athlete = next((item for item in data if item['athlete_id'] == int(athlete_id)), None)

        if not athlete:
            return render_template("message.html",message = "Athlete ID not found"), 404

        # Refresh the access token if needed
        access_token = refresh_access_token(athlete)

    # Fetch activities from Strava
    activities = get_all_activities(access_token,start_date,end_date)

    # for activity in activities:
    try:
        json_data =  activities
        name = session['name']
        filename = f"{app.config['UPLOAD_FOLDER']/name}.json"
        output_file = app.config['UPLOAD_FOLDER']+"/"+f"{name}.xlsx"
        processdata(json_data,name,output_file)
        # Save activities to a JSON file
        with open(filename, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
        return render_template("message.html",message = "Data fetched")
    except Exception as e:
        return render_template("message.html",message = e)


@app.route('/users')
def display_users():
    # Load data from the JSON file
    with open(DATA_FILE, 'r') as file:
        try:
            users = json.load(file)
        except json.JSONDecodeError:
            users = []

    # Render the 'users.html' template with the user data
    return render_template('users.html', users=users)

# Endpoint to handle athlete deauthorization
@app.route('/deauthorize/<int:athlete_id>', methods=['GET'])
def deauthorize_athlete(athlete_id):
    if not athlete_id:
        return render_template("message.html",message = "Athlete ID is required"), 400

    with open(DATA_FILE, 'r+') as file:
        data = json.load(file)
        athlete = next((item for item in data if item['athlete_id'] == int(athlete_id)), None)

        if not athlete:
            return render_template("message.html",message = "Athlete ID not found"), 404

        # Refresh the access token if needed
        access_token = refresh_access_token(athlete)
        if not access_token:
            return jsonify({"error": "Failed to refresh access token"}), 500

        # Deauthorize the athlete
        response = requests.post(DEAUTHORIZE_URL, headers={
            'Authorization': f'Bearer {access_token}'
        })

        if response.status_code == 200:
            # Remove the athlete from the JSON file
            data = [item for item in data if item['athlete_id'] != int(athlete_id)]
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()

            return render_template("message.html",message =  f"Athlete {athlete_id} deauthorized successfully."),200
        else:
            return render_template("message.html",message = "error: Failed to deauthorize athlete"),500

@app.route('/task')
def task():
    return generate_data()

# Route to download the generated file
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        return send_file(file_path, as_attachment=True)
    except FileNotFoundError:
        return render_template("message.html",message = "File not found"),500

# Custom 404 error handler
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True)
