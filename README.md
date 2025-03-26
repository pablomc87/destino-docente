# Schools Backend

A Django-based backend application for managing school information and studies. This application provides a RESTful API and admin interface for managing schools, studies, and their relationships.

## Features

- RESTful API for school information
- Admin interface for data management
- School search functionality
- Detailed school information display
- Study management and school-study relationships
- Docker support for easy deployment
- ngrok integration for temporary public access

## Prerequisites

- Python 3.11+
- Docker
- ngrok (optional, for public access)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd schools-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Development Setup

### Using Docker (Recommended)

1. Build the development image:
```bash
docker build -t schools-backend-dev -f Dockerfile.dev .
```

2. Run the application with ngrok (for public access):
```bash
python run_with_ngrok.py
```

Or run without ngrok:
```bash
docker run -it --rm -p 8000:8000 -v $(pwd):/app --name schools-backend schools-backend-dev
```

### Without Docker

1. Run migrations:
```bash
python manage.py migrate
```

2. Create a superuser:
```bash
python manage.py createsuperuser
```

3. Run the development server:
```bash
python manage.py runserver
```

## Accessing the Application

- Admin interface: http://localhost:8000/admin/
- API endpoints: http://localhost:8000/api/
- Main application: http://localhost:8000/

## API Endpoints

- `GET /api/schools/` - List all schools
- `GET /api/schools/search/` - Search schools by name
- `GET /api/schools/<id>/` - Get detailed information about a specific school

## Project Structure

```
schools-backend/
├── config/                 # Django project settings
├── schools/               # Main application
│   ├── templates/         # HTML templates
│   ├── migrations/        # Database migrations
│   ├── models.py         # Data models
│   ├── views.py          # View logic
│   ├── urls.py           # URL routing
│   └── serializers.py    # API serializers
├── Dockerfile.dev        # Development Docker configuration
├── requirements.txt      # Python dependencies
└── run_with_ngrok.py    # Script for running with ngrok
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 