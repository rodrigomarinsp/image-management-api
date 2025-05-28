from setuptools import setup, find_packages

setup(
    name="image_management_api",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.103.1",
        "uvicorn==0.23.2",
        "python-multipart==0.0.6",
        "pydantic==2.3.0",
        "pydantic-settings==2.0.3",
        "email-validator==2.0.0",
        "python-jose==3.3.0",
        "sqlalchemy==2.0.20",
        "alembic==1.12.0",
        "psycopg2-binary==2.9.7",
        "google-cloud-storage==2.10.0",
        "pillow==10.0.0",
        "loguru==0.7.0",
        "python-dotenv==1.0.0",
    ],
)