# app.py
import os
from datetime import datetime, timedelta
from functools import wraps

import cv2
import redis
import requests
from dotenv import load_dotenv
from flask import Flask, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from gradio_client import Client as GradioClient, file
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# Environment and Configuration
load_dotenv()

class Config:
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    NGROK_URL = os.getenv("NGROK_URL")
    SQLALCHEMY_DATABASE_URI = 'sqlite:///virtual_tryon.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'
    MAX_DAILY_REQUESTS = 100
    RATE_LIMIT_DURATION = timedelta(days=1)

# Initialize Flask and extensions
app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
redis_client = redis.Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=0,
    decode_responses=True
)
twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
gradio_client = GradioClient("Nymbo/Virtual-Try-On")

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_request = db.Column(db.DateTime)
    request_count = db.Column(db.Integer, default=0, nullable=False)
    sessions = db.relationship('Session', backref='user', lazy=True)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    person_image = db.Column(db.String(500))
    garment_image = db.Column(db.String(500))
    result_image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

# Initialize database
with app.app_context():
    db.create_all()

class RateLimiter:
    @staticmethod
    def check_limit(phone_number):
        """Check if user has exceeded rate limit"""
        with redis_client.pipeline() as pipe:
            current_count = redis_client.get(f"rate_limit:{phone_number}")
            
            if current_count is None:
                pipe.setex(
                    f"rate_limit:{phone_number}",
                    Config.RATE_LIMIT_DURATION,
                    1
                )
                pipe.execute()
                return False
            
            if int(current_count) >= Config.MAX_DAILY_REQUESTS:
                return True
                
            pipe.incr(f"rate_limit:{phone_number}")
            pipe.execute()
            return False

class ImageProcessor:
    @staticmethod
    def download_from_twilio(media_url, filename):
        """Download image from Twilio and save locally"""
        try:
            message_sid, media_sid = media_url.split('/')[-3], media_url.split('/')[-1]
            media = twilio_client.api.accounts(Config.TWILIO_ACCOUNT_SID).messages(message_sid).media(media_sid).fetch()
            
            media_uri = media.uri.replace('.json', '')
            image_url = f"https://api.twilio.com{media_uri}"
            
            response = requests.get(
                image_url, 
                auth=(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
            )
            
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename
            return None
            
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None

    @staticmethod
    def process_virtual_tryon(person_image_url, garment_image_url):
        """Process virtual try-on using Gradio API"""
        person_image = ImageProcessor.download_from_twilio(person_image_url, 'person_image.jpg')
        garment_image = ImageProcessor.download_from_twilio(garment_image_url, 'garment_image.jpg')
        
        if not all([person_image, garment_image]):
            return None
            
        try:
            result = gradio_client.predict(
                dict={"background": file(person_image), "layers": [], "composite": None},
                garm_img=file(garment_image),
                garment_des="A cool description of the garment",
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon"
            )
            
            if result and len(result) > 0:
                try_on_image_path = result[0]
                if os.path.exists(try_on_image_path):
                    os.makedirs('static', exist_ok=True)
                    
                    img = cv2.imread(try_on_image_path)
                    result_path = os.path.join('static', 'result.png')
                    cv2.imwrite(result_path, img)
                    
                    return f"{Config.NGROK_URL}/static/result.png"
            return None
            
        except Exception as e:
            print(f"Gradio API error: {e}")
            return None

class MessageHandler:
    @staticmethod
    def send_media_message(to_number, media_url):
        """Send media message via Twilio"""
        message = twilio_client.messages.create(
            from_=Config.TWILIO_WHATSAPP_NUMBER,
            body="Here is your virtual try-on result:",
            media_url=[media_url],
            to=to_number
        )
        print(f"Sent media message {message.sid} to {to_number}")

    @staticmethod
    def create_error_response(message):
        """Create error response message"""
        resp = MessagingResponse()
        resp.message(message)
        return str(resp)

def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        phone_number = request.form.get('From')
        if not phone_number:
            return MessageHandler.create_error_response("Unable to identify phone number."), 400
            
        if RateLimiter.check_limit(phone_number):
            return MessageHandler.create_error_response(
                "You've reached your daily limit of 100 requests. Please try again tomorrow."
            ), 429
            
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            user = User(phone_number=phone_number)
            db.session.add(user)
        
        user.last_request = datetime.utcnow()
        user.request_count += 1
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {e}")
            
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return "Virtual try-on chatbot API", 200

@app.route('/webhook', methods=['POST'])
@rate_limit
def webhook():
    sender_number = request.form.get('From')
    media_url = request.form.get('MediaUrl0')
    
    if not media_url:
        return MessageHandler.create_error_response(
            "We didn't receive an image. Please try sending your image again."
        )
    
    user = User.query.filter_by(phone_number=sender_number).first()
    active_session = Session.query.filter_by(
        user_id=user.id,
        completed_at=None
    ).first()
    
    resp = MessagingResponse()
    
    if not active_session:
        active_session = Session(user_id=user.id, person_image=media_url)
        db.session.add(active_session)
        db.session.commit()
        resp.message("Great! Now please send the image of the garment you want to try on.")
    
    elif not active_session.garment_image:
        active_session.garment_image = media_url
        
        try_on_result = ImageProcessor.process_virtual_tryon(
            active_session.person_image,
            media_url
        )
        
        if try_on_result:
            active_session.result_image = try_on_result
            active_session.completed_at = datetime.utcnow()
            db.session.commit()
            
            MessageHandler.send_media_message(sender_number, try_on_result)
            resp.message("Here is your virtual try-on result!")
        else:
            resp.message("Sorry, something went wrong with the try-on process.")
    
    else:
        active_session = Session(user_id=user.id, person_image=media_url)
        db.session.add(active_session)
        db.session.commit()
        resp.message("Starting a new virtual try-on session. Please send the garment image.")
    
    return str(resp)

@app.route('/user/<phone_number>/limits')
def check_limits(phone_number):
    current_count = redis_client.get(f"rate_limit:{phone_number}")
    ttl = redis_client.ttl(f"rate_limit:{phone_number}")
    user = User.query.filter_by(phone_number=phone_number).first()
    
    return {
        "phone_number": phone_number,
        "daily_requests_used": int(current_count) if current_count else 0,
        "daily_requests_remaining": Config.MAX_DAILY_REQUESTS - (int(current_count) if current_count else 0),
        "reset_in_seconds": ttl if ttl > 0 else 86400,
        "total_requests_all_time": user.request_count if user else 0,
        "last_request": user.last_request.isoformat() if user and user.last_request else None
    }

@app.route('/static/<path:filename>')
def serve_static_file(filename):
    if os.path.exists(os.path.join('static', filename)):
        return send_from_directory('static', filename, mimetype='image/png')
    return "File not found", 404

if __name__ == '__main__':
    app.run(port=8080)