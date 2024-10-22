# Virtual Try-On WhatsApp Bot

A WhatsApp-based AI service that enables users to virtually try on clothes by sending their photos and garment images. The service utilizes AI to create realistic visualizations of how clothes would look on the user.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/WarriorOfLiberation/Virtual-try-on.git

# Navigate to project directory
cd Virtual-try-on

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # For Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Run the application
python app.py
```

## Prerequisites

- Python 3.8+
- Redis Server
- Twilio Account
- Ngrok (for local development)
- SQLite

## Configuration

Create a `.env` file in the root directory:

```env
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
REDIS_HOST=localhost
REDIS_PORT=6379
NGROK_URL=your_ngrok_url
```

## Required Packages

```txt
flask==2.0.1
redis==4.3.4
twilio==7.14.0
gradio-client==0.2.7
python-dotenv==0.19.2
Flask-SQLAlchemy==3.0.3
opencv-python==4.7.0
requests==2.28.2
```

## Features

- WhatsApp-based interaction
- AI-powered virtual try-on
- Real-time image processing
- Session management
- Rate limiting (100 requests/user/day)
- User history tracking

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/webhook` | POST | WhatsApp webhook |
| `/user/<phone>/limits` | GET | Check rate limits |
| `/static/<filename>` | GET | Serve images |

## Future Enhancements

### Machine Learning Improvements
- Enhanced garment segmentation model
- Improved body pose estimation
- Advanced texture synthesis
- Better garment fitting algorithm
- Real-time style transfer capabilities

### System Architecture
- Distributed processing pipeline
- Load balancing with HAProxy
- Migration to PostgreSQL
- Redis cluster implementation
- Containerization with Docker

### Storage Optimization
- Cloud storage integration
- CDN implementation
- Image compression pipeline
- Efficient caching strategy
- Database partitioning

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/Enhancement`)
3. Commit changes (`git commit -m 'Add Enhancement'`)
4. Push to branch (`git push origin feature/Enhancement`)
5. Open Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

---
Developed by Sai Khadloya
