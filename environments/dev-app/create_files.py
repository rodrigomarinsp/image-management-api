import os

structure = """
dev-app/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── api.py                  # Main API router
│   │   ├── dependencies.py         # Shared API dependencies
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── teams.py            # Teams endpoints
│   │       ├── users.py            # Users endpoints
│   │       ├── api_keys.py         # API keys endpoints
│   │       ├── images.py           # Image endpoints
│   │       └── search.py           # Semantic search endpoints (bonus)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Application configuration
│   │   ├── security.py             # Security utilities
│   │   └── logging.py              # Logging configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base models for all tables
│   │   └── session.py              # Database session management
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py                 # API key authentication middleware
│   ├── models/
│   │   ├── __init__.py
│   │   ├── team.py                 # Team database model
│   │   ├── user.py                 # User database model
│   │   ├── api_key.py              # API key database model
│   │   └── image.py                # Image database model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── team.py                 # Team request/response schemas
│   │   ├── user.py                 # User request/response schemas
│   │   ├── api_key.py              # API key request/response schemas
│   │   └── image.py                # Image request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py              # Google Cloud Storage service
│   │   └── vector_search.py        # Vector search service (bonus)
│   └── main.py                     # FastAPI application entry point
├── infrastructure/
│   ├── environments/
│   │   ├── dev/                    # Development environment
│   │   └── prod/                   # Production environment
│   └── modules/                    # Terraform modules
├── migrations/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/                   # Database migration versions
├── scripts/
│   ├── seed_data.py                # Script to seed initial data
│   └── deploy.sh                   # Deployment script
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Test configurations and fixtures
│   ├── test_api/
│   │   ├── __init__.py
│   │   ├── test_teams.py           # Team endpoint tests
│   │   ├── test_users.py           # User endpoint tests
│   │   ├── test_api_keys.py        # API key endpoint tests
│   │   └── test_images.py          # Image endpoint tests
│   └── test_services/
│       ├── __init__.py
│       ├── test_storage.py         # Storage service tests
│       └── test_vector_search.py   # Vector search service tests
├── .env                            # Environment variables for local development
├── .env.example                    # Example environment variables file
├── .gitignore                      # Git ignore file
├── alembic.ini                     # Alembic configuration for migrations
├── Dockerfile                      # Dockerfile for containerization
├── docker-compose.yml              # Local development with Docker
├── pyproject.toml                  # Python project metadata
├── requirements.txt                # Python dependencies
└── README.md       
"""

def create_structure(structure_str):
    lines = structure_str.strip().split('\n')
    base_path = os.getcwd()
    path_stack = []

    for line in lines:
        stripped_line = line.lstrip('│ ').replace('├── ', '').replace('└── ', '').strip()
        depth = (len(line) - len(stripped_line)) // 4

        path_stack = path_stack[:depth]
        path_stack.append(stripped_line)

        current_path = os.path.join(base_path, *path_stack)

        if stripped_line.endswith('/'):
            os.makedirs(current_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(current_path), exist_ok=True)
            open(current_path, 'a').close()

if __name__ == "__main__":
    create_structure(structure)
    print("Directory structure created successfully.")
