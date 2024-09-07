import os



CLIENT_ID = 'YourClientID'
CLIENT_SECRET = 'YourClientSecret'
REDIRECT_URI = 'http://localhost:5000/authorized'  #replace ur with ur pythonanywhere webapp url
AUTHORIZE_URL = 'https://www.strava.com/oauth/authorize'
TOKEN_URL = 'https://www.strava.com/oauth/token'
ACTIVITIES_URL = 'https://www.strava.com/api/v3/athlete/activities'
DEAUTHORIZE_URL = 'https://www.strava.com/oauth/deauthorize'