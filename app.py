import os
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS
import google.generativeai as genai
import re
from flask import session
from firebase_admin import credentials, initialize_app, storage, firestore
import datetime
from werkzeug.utils import secure_filename
import base64
import json
from firebase_admin import credentials, initialize_app
from dotenv import load_dotenv
load_dotenv()

#emergency
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

app = Flask(__name__)

FIREBASE_CRED_B64 = os.environ.get("FIREBASE_CREDENTIALS_B64")

if FIREBASE_CRED_B64:
    firebase_cert_dict = json.loads(base64.b64decode(FIREBASE_CRED_B64))
    cred = credentials.Certificate(firebase_cert_dict)
    initialize_app(cred, {'storageBucket': 'sutrulaago-8d19a.appspot.com'})  # replace with actual
    db = firestore.client()

else:
    raise Exception("FIREBASE_CREDENTIALS_B64 environment variable not set")

# weather
WEATHER_API_KEY = 'adf564d37b67d84e1e5e8d04f279f0aa'


# Wise API Configurations
WISE_API_KEY = "8965a7e3-fe68-47b2-af43-0bce63549941"  
WISE_BASE_URL = "https://api.sandbox.transferwise.tech"

#chatbot
CORS(app)

# Configure Gemini
genai.configure(api_key="AIzaSyArASoxnTW5acFITrTGgIXhQQsG_Qt8ZYI")  # Replace with your own API key
models = genai.list_models()
print(models)  # Print available models to check the names

# Choose a model based on the available models (replace with the correct identifier)
model_id = "gemini-1.5-pro"  # Example, replace with actual model id from the printed list
model = genai.GenerativeModel(model_id)

@app.route('/<path:path>')
def catch_all(path):
    return render_template(f'{path}.html') if path in TEMPLATE_NAMES else abort(404)
    
@app.route('/chatbot', methods=['POST'])  # Add this route decorator
def chat():
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"reply": "Please ask something about Tamil Nadu 😊"}), 400

    prompt = f"""
    You are Paadhai, a friendly and informative travel assistant who specializes in Tamil Nadu.
    The user is a curious traveler who wants to know more about Tamil Nadu.
    Reply both in tamil and english.
    Provide useful, engaging, and fun responses to the following tourist question:
    
    {user_message}
    """

    try:
        response = model.generate_content(prompt)
        reply = response.text.strip()
    except Exception as e:
        print("Error from Gemini:", e)
        reply = "Oops! Something went wrong. 😢"

    return jsonify({"reply": reply})

# travellog updates
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

app.secret_key = 'AIzaSyBTSqnDhr7assffH0B5Qn5NEcyg0YUSNMM'
# Ensure the credentials file exists
def ensure_credentials_file():
    file_path = 'userdetails.txt'
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            pass
        print(f"Created {file_path}")

@app.route('/toggle-language', methods=['POST'])
def toggle_language():
    session['language'] = 'tamil' if session.get('language') == 'english' else 'english'
    return jsonify({'language': session['language']})


  # Add a secret key for session management

@app.before_request
def set_default_language():
    if 'language' not in session:
        session['language'] = 'english'

# Google Custom Search API credentials
API_KEY = 'AIzaSyB86zcSPyIkd3aEB-q5VEpDkc_oH7S-PCY'
CX = 'b69d68a0e1bdd48f7'

# Function to get image URL for a place using Google Places API
def get_image(place_name):
    # Step 1: Find place_id
    find_place_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": place_name,
        "inputtype": "textquery",
        "fields": "place_id",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(find_place_url, params=params)
    if response.status_code != 200:
        return None
    candidates = response.json().get("candidates")
    if not candidates:
        return None
    place_id = candidates[0]["place_id"]

    # Step 2: Get place details (photos)
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "photo",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(details_url, params=params)
    if response.status_code != 200:
        return None
    photos = response.json().get("result", {}).get("photos")
    if not photos:
        return None
    photo_reference = photos[0]["photo_reference"]

    # Step 3: Construct photo URL
    photo_url = (
        f"https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth=800"
        f"&photoreference={photo_reference}"
        f"&key={GOOGLE_API_KEY}"
    )
    return photo_url

# Function to get a longer description for a place using Google Custom Search API and Gemini

def get_description(place_name):
    # Step 1: Get short description from Google Custom Search
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY,
        "cx": CX,
        "q": place_name,
        "num": 1
    }
    response = requests.get(search_url, params=params)
    short_desc = "No description found."
    if response.status_code == 200:
        results = response.json()
        try:
            item = results.get('items', [])[0]
            snippet = item.get('snippet', '')
            pagemap = item.get('pagemap', {})
            meta_desc = ""
            if 'metatags' in pagemap and len(pagemap['metatags']) > 0:
                meta_desc = pagemap['metatags'][0].get('og:description') or pagemap['metatags'][0].get('description', '')
            if meta_desc and meta_desc != snippet:
                short_desc = meta_desc + " " + snippet
            elif meta_desc:
                short_desc = meta_desc
            elif snippet:
                short_desc = snippet
        except (KeyError, IndexError):
            pass

    # Step 2: Use Gemini to expand the description
    if short_desc and short_desc != "No description found.":
        prompt = f"Expand the following short travel description into a detailed, engaging travel guide paragraph for visitors. Give the text in tamil (100 words):\n\n{short_desc}"
        try:
            gemini_response = model.generate_content(prompt)
            long_desc = gemini_response.text.strip()
            return long_desc
        except Exception as e:
            print("Gemini expansion error:", e)
            return short_desc  # fallback to short description
    else:
        return short_desc

# Function to fetch weather data for a city
def get_weather(place_name):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={place_name}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    
    print("Weather API Response:", response.json())  # Debugging

    if response.status_code == 200:
        weather_data = response.json()
        try:
            weather_info = {
                'city': place_name,
                'temperature': weather_data['main']['temp'],
                'weather': weather_data['weather'][0]['description'],
                'humidity': weather_data['main']['humidity'],
                'clouds': weather_data['clouds']['all'],
                'wind_speed': weather_data['wind']['speed'],
            }
            return weather_info
        except (KeyError, IndexError) as e:
            print(f"Error while extracting weather data: {e}")
            return None
    else:
        print(f"API Error: {response.status_code}")
        return None

# New API route to fetch weather data for frontend cloud button
@app.route('/get-weather/<city>')
def get_weather_api(city):
    weather_info = get_weather(city)
    if weather_info:
        return jsonify(weather_info)
    else:
        return jsonify({'error': 'Could not fetch weather data.'})

# Landing page
@app.route('/')
def landing():
    return render_template('index.html')

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    ensure_credentials_file()
    action = 'signup'

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if len(password) < 6:
            return "<h3>Password must be at least 6 characters long. <a href='/signup'>Try again</a></h3>"

        with open('userdetails.txt', 'a') as f:
            f.write(f"{name},{email},{password}\n")
        
        # Store username in session
        session['username'] = name
        return redirect('/main')

    return render_template('auth.html', action=action)

# Signin page
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    ensure_credentials_file()
    action = 'signin'

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with open('userdetails.txt', 'r') as f:
            creds = f.readlines()

        for cred in creds:
            parts = cred.strip().split(',')
            if len(parts) < 3:
                continue  # Skip invalid or blank lines
            stored_name, stored_email, stored_password = parts[:3]
            if email == stored_email and password == stored_password:
                # Store username in session
                session['username'] = stored_name
                return redirect('/main')
        
        return "<h3>Invalid credentials. <a href='/signin'>Try again</a></h3>"

    return render_template('auth.html', action=action)

# Main page with Explore Places search functionality
@app.route('/main', methods=['GET', 'POST'])
def main():
    image_url = None
    place_name = None
    weather_info = None

    if request.method == 'POST':
        place_name = request.form['place_name']
        image_url = get_image(place_name)

        # Get weather info for the place
        weather_info = get_weather(place_name)
        if weather_info:
            print("Weather Info:", weather_info)

    return render_template('main.html', image_url=image_url, place_name=place_name, weather_info=weather_info)

#360 view
@app.route('/360view/<city>')
def city_360view(city):
    return render_template('360view.html', city=city)

def get_place_data(place):
    # Enhanced static data for demonstration
    places = {
        "chennai": {
            "place_name": "Chennai",
            "place_image": "chennai.png",
            "place_thumb": "chennai.png",
            "place_tagline": "🌊 தென்னிந்தியாவின் வாயில், கலாச்சாரத்தின் நகரம்",
            "place_description": (
                "சென்னை, தமிழ்நாட்டின் இதயம்! வரலாற்று சிறப்புமிக்க கோட்டை செயின்ட் ஜார்ஜ், "
                "உலகின் மிக நீளமான மரினா கடற்கரை, கலையரங்குகள், அருங்காட்சியகங்கள், "
                "மற்றும் சென்னையின் உணவு வகைகள் என அனைத்தும் உங்கள் மனதை கவரும். "
                "இங்கு பாரம்பரியம் மற்றும் நவீனத்துவம் கலந்த ஒரு தனி அழகு உள்ளது."
                "<br><br>"
                "<b>பிரபலமான இடங்கள்:</b><ul>"
                "<li>மரினா கடற்கரை</li>"
                "<li>சென்ட்ரல் ரயில்வே நிலையம்</li>"
                "<li>கோட்டை செயின்ட் ஜார்ஜ்</li>"
                "<li>கவர்ன்மெண்ட் அருங்காட்சியகம்</li>"
                "<li>கபாலீஸ்வரர் கோவில்</li>"
                "</ul>"
            ),
            "place_tags": ["கடற்கரை", "வரலாறு", "கலை", "உணவு", "பாரம்பரியம்", "நகரம்"],
            "place_map_url": "https://maps.app.goo.gl/gPxn8bsuf16TM6XPA",
            "place_gallery": ["chennai1.jpg", "chennai2.jpg", "chennai3.jpg"]
        },
        "madurai": {
            "place_name": "Madurai",
            "place_image": "madurai.png",
            "place_thumb": "madurai.png",
            "place_tagline": "🏛️ கோயில்களின் நகரம், கலாச்சாரத்தின் மையம்",
            "place_description": (
                "மதுரை, தமிழ் நாட்டின் ஆன்மிகத் தளமாகும். "
                "மீனாட்சி அம்மன் கோயிலின் சிற்பங்கள், திருவிழாக்கள், "
                "மற்றும் மதுரையின் ஜிகர்தண்டா போன்ற இனிப்புகள் உங்கள் பயணத்தை இனிமையாக்கும். "
                "இங்கு பாரம்பரியமும், ஆன்மிகமும் கலந்த ஒரு தனித்துவம் உள்ளது."
                "<br><br>"
                "<b>பிரபலமான இடங்கள்:</b><ul>"
                "<li>மீனாட்சி அம்மன் கோவில்</li>"
                "<li>திருமலை நாயக்கர் மஹால்</li>"
                "<li>காந்தி அருங்காட்சியகம்</li>"
                "<li>அழகர் கோவில்</li>"
                "<li>வைகை ஆறு</li>"
                "</ul>"
            ),
            "place_tags": ["கோவில்", "பாரம்பரியம்", "இனிப்பு", "ஆன்மிகம்", "வரலாறு"],
            "place_map_url": "https://maps.app.goo.gl/c22mHKSdDyL5YMxD8",
            "place_gallery": ["madurai1.jpg", "madurai2.jpg", "madurai3.jpg"]
        },
        "salem": {
            "place_name": "Salem",
            "place_image": "salem.png",
            "place_thumb": "salem.png",
            "place_tagline": "⛰️ மலர்களும், மலைகளும், பாரம்பரியமும் நிறைந்த நகரம்",
            "place_description": (
                "சேலம், தமிழ்நாட்டின் முக்கியமான தொழிற்நகரம் மற்றும் இயற்கை அழகின் மையம். "
                "யேர்காடு மலையிலிருந்து வரும் குளிர்ந்த காற்றும், பழங்கால கோயில்கள், "
                "மற்றும் சேலத்தின் புகழ்பெற்ற மாங்கனி, உங்கள் பயண அனுபவத்தை சிறப்பாக்கும். "
                "இங்கு இயற்கை, பாரம்பரியம் மற்றும் நவீன வசதிகள் ஒன்றாக இணைந்துள்ளன."
                "<br><br>"
                "<b>பிரபலமான இடங்கள்:</b><ul>"
                "<li>யேர்காடு மலை</li>"
                "<li>1008 லிங்கம் கோவில்</li>"
                "<li>கஞ்சாமலை</li>"
                "<li>சுகவனேஸ்வரர் கோவில்</li>"
                "<li>மாங்கனி சந்தை</li>"
                "</ul>"
            ),
            "place_tags": ["மலை", "பாரம்பரியம்", "இயற்கை", "மாங்கனி", "கோவில்"],
            "place_map_url": "https://maps.app.goo.gl/SVF6QKqAWj4kenTZ6",
            "place_gallery": ["salem1.jpg", "salem2.jpg", "salem3.jpg"]
        },
        # Add more places as needed
    }
    return places.get(place.lower(), {
        "place_name": place.capitalize(),
        "place_image": "default.png",
        "place_thumb": "default.png",
        "place_tagline": "Explore this wonderful place!",
        "place_description": "No description available.",
        "place_tags": [],
        "place_map_url": "#",
        "place_gallery": []
    })

# Function to get bottom image for a place

def get_place_image(place):
    # You can expand this dictionary as needed
    images = {
        "chennai": "/static/images/chennai_bottom.jpeg",
        "madurai": "/static/images/madurai_bottom.jpeg",
        "salem": "/static/images/salem_bottom.jpeg"
    }
    return images.get(place.lower(), "/static/default_bottom.jpg")

# Individual place details page
@app.route('/place/<place>')
def place(place):
    place_data = get_place_data(place)
    bottom_image = get_place_image(place)
    return render_template(
        'place.html',
        place_name=place_data['place_name'],
        place_image=place_data['place_image'],
        place_thumb=place_data['place_thumb'],
        place_tagline=place_data['place_tagline'],
        place_description=place_data['place_description'],
        place_tags=place_data['place_tags'],
        place_map_url=place_data['place_map_url'],
        place_gallery=place_data['place_gallery'],
        place_key=place,
        bottom_image=bottom_image  # Pass this to the template
    )

# Custom search page
@app.route('/custom-search', methods=['GET', 'POST'])
def custom_search():
    image_url = None
    place_name = None
    weather_info = None
    description = None

    if request.method == 'POST':
        place_name = request.form['place_name']
        image_url = get_image(place_name)
        weather_info = get_weather(place_name)
        description = get_description(place_name)

    return render_template('custom_search.html', image_url=image_url, place_name=place_name, weather_info=weather_info, description=description)

@app.route('/travellog')
def travellog():
    posts_ref = db.collection('posts').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    # Add document ID to post data
    posts = [{'id': post.id, **post.to_dict()} for post in posts_ref]  # Changed line
    return render_template('travellog.html', posts=posts)

@app.route('/upload', methods=['POST'])
def upload_post():
    try:
        file = request.files['image']
        caption = request.form['caption']
        
        if file and allowed_file(file.filename):
            # Create upload directory if not exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Generate safe filename
            filename = f"{datetime.datetime.now().timestamp()}_{secure_filename(file.filename)}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save file locally
            file.save(file_path)
            
            # Store relative path in Firestore
            post_ref = db.collection('posts').document()
            post_ref.set({
                'username': session.get('username'),  # added this line
                'caption': caption,
                'image_url': f"/{file_path.replace('\\', '/')}",
                'likes': 0,
                'timestamp': datetime.datetime.now()
            })

        else:
            print("Invalid file type or no file selected")
        
        # Always return redirect after processing
        return redirect('/travellog')
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return redirect('/')

@app.route('/like/<post_id>', methods=['POST'])
def like_post(post_id):
    # This will now receive the correct ID
    post_ref = db.collection('posts').document(post_id)
    post_ref.update({'likes': firestore.Increment(1)})
    
    return '', 204

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpeg', 'jpg'}


@app.route('/itinerary')
def itinerary():
    return render_template('sutrulaa.html')

GOOGLE_API_KEY = "AIzaSyBTSqnDhr7assffH0B5Qn5NEcyg0YUSNMM"
GEMINI_API_KEY = "AIzaSyBRdwktUscXyQ3WxSSRdqTVuEqEHoeVU8Q"

# === Utility Functions from sutrulaa.py ===
def get_places(latlon, interest):
    latlon_str = f"{latlon['lat']},{latlon['lon']}"
    endpoint = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": latlon_str,
        "radius": 1000,
        "keyword": interest,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(endpoint, params=params)
    places = response.json().get("results", [])[:5]
    return [{
        "name": p["name"],
        "lat": p["geometry"]["location"]["lat"],
        "lng": p["geometry"]["location"]["lng"]
    } for p in places]

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

def get_weather_forecast(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }
    res = requests.get(url, params=params)
    data = res.json()
    if "weather" in data and data["weather"]:
        return {
            "description": data["weather"][0]["description"],
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"]
        }
    return {}

def get_distance_matrix(origins, destinations):
    origin_str = "|".join(origins)
    dest_str = "|".join(destinations)
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin_str,
        "destinations": dest_str,
        "key": GOOGLE_API_KEY,
        "mode": "driving"
    }
    res = requests.get(url, params=params)
    return res.json()

def get_coordinates_for_places(place_names):
    coords = []
    for name in place_names:
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": name,
            "inputtype": "textquery",
            "fields": "geometry",
            "key": GOOGLE_API_KEY
        }
        res = requests.get(url, params=params).json()
        try:
            location = res["candidates"][0]["geometry"]["location"]
            coords.append({
                "name": name,
                "lat": location["lat"],
                "lng": location["lng"]
            })
        except:
            continue
    return coords

def extract_locations_by_day_and_slot(text):
    itinerary = {}
    current_day = None
    current_slot = None

    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        # Match Day headers (with or without bold)
        day_match = re.match(r'(\*\*)?Day\s*\d+.*(\*\*)?', line, re.IGNORECASE)
        if day_match:
            current_day = re.sub(r'^\*\*|\*\*$', '', line).strip()
            itinerary[current_day] = {}
            current_slot = None
            continue
        # Match slot headers (Morning, Afternoon, Evening, with or without bold and time)
        slot_match = re.match(r'(\*\*)?(Morning|Afternoon|Evening)[^:]*:.*(\*\*)?', line, re.IGNORECASE)
        if slot_match:
            slot_name = slot_match.group(2).capitalize()
            current_slot = slot_name
            if current_day:
                itinerary[current_day][current_slot] = []
            continue
        # Match indented bullet points for places (with or without bold)
        if current_day and current_slot and re.match(r'^\*{1,2}\s+', line) or re.match(r'^\d+\.', line) or line.startswith('- '):
            # Remove bullet, bold, and leading/trailing whitespace
            clean_line = re.sub(r'^[\*\-\d\.\s]+', '', line)
            # Remove bold if present
            clean_line = re.sub(r'^\*\*|\*\*$', '', clean_line).strip()
            # Extract place name before ":" or "(" if present
            place = re.split(r':|\(', clean_line)[0].strip()
            # Filter out non-place lines
            if place and len(place.split()) <= 8 and not place.lower().startswith(
                ("return", "relax", "rest", "lunch", "dinner", "free time", "optional", "drive back", "explore", "focus", "sample", "spend", "enjoy", "take", "begin", "allow", "be mindful", "marvel", "admire", "visit this", "start your days", "opt for", "carry", "wear", "pre-book", "be prepared", "consider", "be aware", "this itinerary", "remember", "entrance fees", "bargaining", "respectful attire")
            ):
                itinerary[current_day][current_slot].append(place)
    return itinerary

# === Route from sutrulaa.py for Itinerary Generation ===
@app.route("/generate-itinerary", methods=["POST"])
def generate_itinerary():
    data = request.get_json()
    place_name = data.get('place_name')
    days = data['days']
    interests = "sightseeing"

    coords = get_coordinates_for_places([place_name])
    if not coords:
        return jsonify({"error": "Could not find coordinates for the given place."}), 400
    lat = coords[0]['lat']
    lon = coords[0]['lng']

    suggested_places = get_places({'lat': lat, 'lon': lon}, interests)
    weather = get_weather_forecast(lat, lon)

    prompt = f"""
    Create a {days}-day travel itinerary near {place_name} for a traveler interested in {interests}.
    Current weather is {weather['description']} with temperature around {weather['temp']}°C and humidity {weather['humidity']}%.\n
    Suggested places to consider: {[p['name'] for p in suggested_places]}.\n
    Group nearby places together by morning, afternoon, and evening slots.
    Use bullet points for places. 
    """

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    itinerary_text = response.text
    day_wise_places = extract_locations_by_day_and_slot(itinerary_text)
    travel_segments = []

    # --- NEW CODE: Collect all unique places for coordinate lookup ---
    locations=[]
    for day_loc in day_wise_places.keys():
       loc=day_loc.split(" ")[2]
       locations.append(loc)
    print(locations)
    place_coords_list = get_coordinates_for_places(locations)
    place_coords_map = {p['name']: {'lat': p['lat'], 'lng': p['lng']} for p in place_coords_list}
    print("Place coords list:", place_coords_list, flush=True)
    ola_links = []
    for place in place_coords_list:
        lat = place['lat']
        lng = place['lng']
        name = place['name']
        pickup_lat, pickup_lng = 0, 0  # You can use actual user location in frontend
        ola_link = f"https://book.olacabs.com/?pickup_lat={pickup_lat}&pickup_lng={pickup_lng}&drop_lat={lat}&drop_lng={lng}&drop_name={name}"
        ola_links.append({"name": name, "link": ola_link})

    # --- NEW CODE: Build structured itinerary with coordinates ---
    structured_itinerary = {}
    for day, slots in day_wise_places.items():
        structured_itinerary[day] = {}
        for slot, places in slots.items():
            structured_itinerary[day][slot] = []
            for place in places:
                coords = place_coords_map.get(place, {})
                structured_itinerary[day][slot].append({
                    'name': place,
                    'lat': coords.get('lat'),
                    'lng': coords.get('lng')
                })

    for day, slots in day_wise_places.items():
        for slot, places in slots.items():
            coords = get_coordinates_for_places(places)
            if len(coords) < 2:
                continue
            names = [p['name'] for p in coords]
            latlngs = [f"{p['lat']},{p['lng']}" for p in coords]
            for i in range(len(latlngs) - 1):
                result = get_distance_matrix([latlngs[i]], [latlngs[i + 1]])
                if "rows" in result and "elements" in result["rows"][0]:
                    element = result["rows"][0]["elements"][0]
                    duration = element.get("duration", {}).get("text", "N/A")
                    distance = element.get("distance", {}).get("text", "N/A")
                    travel_segments.append(f"{day} - {slot}: {names[i]} → {names[i+1]} = {duration}, {distance}")
                else:
                    travel_segments.append(f"{day} - {slot}: {names[i]} → {names[i+1]} = N/A")

    return jsonify({
        "itinerary": itinerary_text,
        "structured_itinerary": structured_itinerary,
        "travel_info": travel_segments,
        "ola_links": ola_links  # <-- Add this line to your response
    })

#profile thingyyyy

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpeg', 'jpg'}

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    username = session.get('username')
    if not username:
        return redirect('/signin')

    # Fetch user details from userdetails.txt
    user_info = None
    with open('userdetails.txt', 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if parts[0] == username:
                # Pad to at least 5 fields: name, email, password, description, profile_pic
                while len(parts) < 5:
                    parts.append('')
                user_info = parts
                break

    if not user_info:
        return "<h3>User not found.</h3>"

    name = user_info[0]
    email = user_info[1]
    description = user_info[3]
    profile_pic = user_info[4] if user_info[4] else url_for('static', filename='images/default_profile.png')

    # Fetch posts and likes from Firestore
    posts_ref = db.collection('posts').where('username', '==', username).stream()
    posts = [post.to_dict() for post in posts_ref]
    post_count = len(posts)
    like_count = sum(post.get('likes', 0) for post in posts)

    # Handle description update
    if request.method == 'POST':
        new_desc = request.form.get('description', '').strip()
        if new_desc:
            lines = []
            with open('userdetails.txt', 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if parts[0] == username:
                        while len(parts) < 5:
                            parts.append('')
                        parts[3] = new_desc
                        line = ','.join(parts)
                    lines.append(line)
            with open('userdetails.txt', 'w') as f:
                for line in lines:
                    f.write(line + '\n')
            description = new_desc  # Update for current render

    # BADGES: Collect badge image URLs for this user
    badge_folder = os.path.join('static', 'badges', username)
    badge_urls = []
    if os.path.exists(badge_folder):
        for fname in os.listdir(badge_folder):
            if allowed_file(fname):
                badge_urls.append(url_for('static', filename=f'badges/{username}/{fname}'))

    return render_template(
        'profile.html',
        name=name,
        email=email,
        description=description,
        profile_pic=profile_pic,
        posts=posts,
        post_count=post_count,
        like_count=like_count,
        badge_urls=badge_urls
    )


#profile_pic = user_info[4] if len(user_info) > 4 and user_info[4] else url_for('static', filename='images/default_profile.png')
@app.route('/change-profile-pic', methods=['POST'])
def change_profile_pic():
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    data = request.get_json()
    new_pic = data.get('profile_pic')
    if not new_pic:
        return jsonify({'success': False, 'error': 'No picture specified'}), 400

    updated = False
    lines = []
    with open('userdetails.txt', 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if parts[0] == username:
                # Ensure at least 5 fields for profile pic
                while len(parts) < 5:
                    parts.append('')
                parts[4] = f"static/images/{new_pic}"
                updated = True
                line = ','.join(parts)
            lines.append(line)
    if updated:
        with open('userdetails.txt', 'w') as f:
            for line in lines:
                f.write(line + '\n')
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/upload-badge', methods=['POST'])
def upload_badge():
    if 'username' not in session:
        return redirect('/signin')
    username = session['username']
    if 'badge' not in request.files:
        return redirect('/profile')
    file = request.files['badge']
    if file and allowed_file(file.filename):
        # Create user-specific badge folder
        badge_folder = os.path.join('static', 'badges', username)
        os.makedirs(badge_folder, exist_ok=True)
        filename = f"{int(__import__('time').time())}_{secure_filename(file.filename)}"
        file_path = os.path.join(badge_folder, filename)
        file.save(file_path)
    return redirect('/profile')

#game

@app.route('/game')
def menu():
    return render_template('menu.html')

@app.route('/story-game')
def story_game():
    return render_template('Game.html')

@app.route('/language-game')
def language_game():
    return render_template('LanguageGame.html')

@app.route('/api/phrases/<int:level>')
def get_phrases(level):
    phrases = {
        1: [
            {"id": 1, "local": "வணக்கம்", "translation": "Hello"},
            {"id": 2, "local": "நன்றி", "translation": "Thank you"},
            {"id": 3, "local": "பிறகு பார்க்கலாம்", "translation": "See you later"},
            {"id": 4, "local": "எப்படி இருக்கிறீர்கள்", "translation": "How are you"},
        ],
        2: [
            {"id": 5, "local": "காலை வணக்கம்", "translation": "Good morning"},
            {"id": 6, "local": "மாலை வணக்கம்", "translation": "Good evening"},
            {"id": 7, "local": "சாப்பிட்டீர்களா", "translation": "Have you eaten"},
            {"id": 8, "local": "என் பெயர்", "translation": "My name is"},
        ],
        3: [
            {"id": 9, "local": "எனக்கு தமிழ் தெரியும்", "translation": "I know Tamil"},
            {"id": 10, "local": "உங்களுக்கு புரிகிறதா", "translation": "Do you understand"},
            {"id": 11, "local": "மீண்டும் சொல்லுங்கள்", "translation": "Please repeat"},
            {"id": 12, "local": "மெதுவாக பேசுங்கள்", "translation": "Please speak slowly"},
        ]
    }
    return jsonify(phrases.get(level, []))

@app.route('/api/complete_level', methods=['POST'])
def complete_level():
    data = request.json
    level = data.get('level', 1)
    badges = {
        1: {"image": "badge1.png", "title": "Tamil Beginner"},
        2: {"image": "badge2.png", "title": "Tamil Explorer"},
        3: {"image": "badge3.png", "title": "Tamil Master"}
    }
    return jsonify({"badge": badges.get(level)})


#emergency
@app.route('/emergency')
def index():
    return render_template('emergency_html.html')

@app.route('/get_emergency_services', methods=['POST'])
def get_emergency_services():
    data = request.json
    services = {
        'hospital': fetch_places('hospital', data['lat'], data['lng']),
        'police': fetch_places('police', data['lat'], data['lng']),
        'pharmacy': fetch_places('pharmacy', data['lat'], data['lng']),
        'embassy': fetch_places('embassy', data['lat'], data['lng'])
    }
    return jsonify(services)

def fetch_places(service_type, lat, lng):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'key': GOOGLE_API_KEY,
        'location': f"{lat},{lng}",
        'radius': 5000,
        'type': service_type
    }
    response = requests.get(url, params=params)
    return process_places(response.json())

def process_places(data):
    return [{
        'name': item['name'],
        'address': item.get('vicinity', ''),
        'phone': item.get('formatted_phone_number', ''),
        'lat': item['geometry']['location']['lat'],
        'lng': item['geometry']['location']['lng']
    } for item in data.get('results', [])]


@app.route('/wise')
def home():
    return render_template("wise.html")

### 1) Wise Account Registration ###
@app.route('/register_wise', methods=['GET'])
def register_wise():
    """Provide link to Wise registration page with instructions."""
    wise_link = "https://wise.com/signup"
    instructions = (
        "Click the link to register for a Wise account. Once registered, you can connect your account to this app."
    )
    return jsonify({"message": "Register for Wise", "instructions": instructions, "link": wise_link})


### 2) Create Virtual Card ###
def get_profile_id():
    """Fetch Wise Profile ID."""
    url = f"{WISE_BASE_URL}/profiles"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        profiles = response.json()
        return profiles[0]["id"] if profiles else None  # Return first profile ID
    return None

def create_virtual_card():
    """Generate a Wise Virtual Card for making payments."""
    profile_id = 28686056
    if not profile_id:
        return {"error": "Failed to retrieve Wise Profile ID"}
    
    url = "https://api.sandbox.transferwise.tech/v3/spend/profiles/28686056/card-orders"

    headers = {
     "Authorization": f"Bearer 8965a7e3-fe68-47b2-af43-0bce63549941",
     "Content-Type": "application/json",
     "X-idempotence-uuid": str(uuid.uuid4()) 
   }

    payload = {
     "program": "VISA_DEBIT_BUSINESS_UK_1_VIRTUAL_CARDS_API",
     "cardHolderName": "Giovanny Ellis",
      "cardType": "VIRTUAL",
     "address": {
        "firstLine": "33 Norwich Parc",
        "secondLine": None,
        "thirdLine": None,
        "city": "Port Ha",
        "postalCode": "E2 4JJ",
        "state": None,
        "country": "ES"
    },
    "deliveryOption": "POSTAL_SERVICE_STANDARD"
   }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        
        print("Request successful!")
        print("Response status code:", response.status_code)
        print("Response JSON:", response.json())

        return response.json()  # <-- You forgot to return this!

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        if 'response' in locals() and response is not None:
            print(f"Response text: {response.text}")  # Debugging response

        return {"error": "Request failed"}  # Return error instead of None

@app.route('/create_virtual_card', methods=['POST'])
def generate_virtual_card():
    """Create Wise Virtual Card."""
    card_response = create_virtual_card()
    
    if "error" in card_response:
        return jsonify(card_response), 400
    
    return jsonify({"message": "Virtual card created", "card_details": card_response})


### 3) View Wise Balance (Virtual Wallet) ###
def get_wise_balance():
    """Fetch Wise account balance and display it as a Virtual Wallet."""
    url = "https://api.sandbox.transferwise.tech/v4/profiles/28686055/balances?types=STANDARD"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
     accounts = response.json()

     # Extract balances for all currencies
     balance_summary = {acc["currency"]: acc["amount"]["value"] for acc in accounts}

     print("Balances fetched:", balance_summary)
     return {"virtual_wallet": balance_summary}

    else:
     print("Error fetching balance:", response.json())
     return {"error": "Failed to fetch balance"}




@app.route('/balance', methods=['GET'])
def check_balance():
    """Fetch Wise balance and display it as a Virtual Wallet."""
    balance = get_wise_balance()
    return jsonify(balance)


### 4) Fetch Current & Historic Exchange Rates ###
def fetch_exchange_rate(from_currency, to_currency):
    """Fetch the real-time exchange rate from Wise."""
    url = f"https://api.sandbox.transferwise.tech/v1/rates?source={from_currency}&target={to_currency}"
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        rates = response.json()
        return {"exchange_rate": rates[0]["rate"], "date": rates[0]["time"]}
    else:
        return {"error": "Failed to fetch exchange rate"}

@app.route('/exchange_rate/<string:from_currency>/<string:to_currency>', methods=['GET'])
def get_exchange_rate(from_currency, to_currency):
    """Fetch current exchange rates."""
    rate_info = fetch_exchange_rate(from_currency, to_currency)
    return jsonify(rate_info)


### 5) Currency Exchange ###

def create_quote(from_currency, to_currency, amount):
    """Create a quote for currency exchange."""

    url = f"https://api.sandbox.transferwise.tech/v3/profiles/28686055/quotes"
    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "profile": "28686055",  
        "source": from_currency,
        "target": to_currency,
        "rateType": "FIXED",
        "sourceAmount": amount,  # Define the amount being exchanged
        "payOut": "BALANCE"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    #print(response)
    if response.status_code == 200:
        quote = response.json()
        
        # Extracting relevant details
        filtered_data = {
            "quote_id": quote.get("id"),
            "from_currency": quote.get("sourceCurrency"),
            "to_currency": quote.get("targetCurrency"),
            "source_amount": quote.get("sourceAmount"),
            "rate": quote.get("rate"),
            "fee": quote.get("pricingConfiguration", {}).get("fee", {}).get("fixed", 0),
            "discount": quote.get("paymentOptions", [{}])[0].get("fee", {}).get("discount", 0),
            "final_amount": quote.get("paymentOptions", [{}])[0].get("targetAmount")
        }
        
        return filtered_data
    
    else:
        return {"error": "Failed to create quote", "status_code": response.status_code, "message": response.text}

@app.route('/exchange/<string:from_currency>/<string:to_currency>/<path:amount>', methods=['POST'])
def exchange_money(from_currency, to_currency, amount):
    """Perform currency exchange and store in Wise balance."""
    quote = create_quote(from_currency, to_currency, amount)
    quote_id = quote['quote_id']
    quote["approve_url"] = f"/approve_transfer/{quote_id}/{from_currency}/{to_currency}"

    if "error" in quote:
        return jsonify({"error": "Failed to create quote"}), 400  # Early return if quote fails
    
    return jsonify({
        "message": "Quote generated. Please approve to proceed with transfer.",
        "quote_details": quote
    })


def get_balance_id(currency):
    """Retrieve balance ID for a given currency."""
    url = "https://api.sandbox.transferwise.tech/v4/profiles/28686055/balances?types=STANDARD"
    
    headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
    
    response = requests.get(url, headers=headers)
    print(response)
    
    if response.status_code == 200:
        balances = response.json()
        print(balances)
        
        for balance in balances:
            if balance.get("currency") == currency:
                return balance.get("id")  # Ensure safe retrieval
        
        return None  # No balance found for the currency
    
    return None  # Failed request


@app.route('/approve_transfer/<string:quote_id>/<string:from_currency>/<string:to_currency>', methods=['POST'])
def approve_transfer(quote_id,from_currency,to_currency):
    """Handles the approval process and initiates the transfer."""
    profile_id = "28686055"
    #getting balance ids of from and to currencies
    source_balance_id = get_balance_id("EUR")
    target_balance_id = get_balance_id("GBP")
    print(source_balance_id, target_balance_id)
    
    if not source_balance_id or not target_balance_id:
        return jsonify({"error": "Failed to retrieve balance IDs"}), 400

    url = f"https://api.sandbox.transferwise.tech/v2/profiles/28686055/balance-movements"

    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json",
        "X-idempotence-uuid": str(uuid.uuid4())  # Ensures unique request
    }

    payload = {
        "type": "CONVERSION",
        "quoteId": quote_id,  # Uses the quote to determine the exchange
        "sourceBalanceId": source_balance_id,
        "targetBalanceId": target_balance_id,
        "customerTransactionId": str(uuid.uuid4())  # Generates a unique transaction ID
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return jsonify({"message": "Currency exchange successful!", "transaction_details": response.json()})
    else:
        return jsonify({
            "error": "Failed to perform currency exchange",
            "status_code": response.status_code,
            "message": response.text
        }), response.status_code



### 6) Add Virtual Card to GPay ###
@app.route('/add_card_to_gpay', methods=['GET'])
def add_card_to_gpay():
    """Provide GPay link and instructions to manually add a virtual card."""
    gpay_link = "https://pay.google.com/gp/w/u/0/home/paymentmethods"
    instructions = (
        "Currently, direct Google Pay integration is not available. "
        "You can manually add your Wise virtual card by visiting Google Pay's payment methods page."
    )
    
    return jsonify({
        "message": "Soon you'll be able to add our virtual card to GPay directly via the app!",
        "instructions": instructions,
        "gpay_link": gpay_link
    })


### 7) Pay with GPay ###
@app.route('/pay_with_gpay', methods=['GET'])
def pay_with_gpay():
    """Redirect user to GPay for payments using Wise Virtual Card."""
    gpay_payment_link = "https://pay.google.com/gp/w/u/0/send"
    return redirect(gpay_payment_link)


# Run the app
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)



