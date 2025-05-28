import os
import sys
import json
import logging
from datetime import datetime
from loguru import logger as loguru_logger

from app.core.config import settings

# Remove default logger
loguru_logger.remove()


class CloudLoggingAdapter:
    """
    Adapter to convert Loguru log records to Cloud Logging compatible JSON format
    """
    def __init__(self):
        self.env = os.getenv("ENV", "development")
        self.service_name = settings.PROJECT_NAME

    def write(self, message):
        record = json.loads(message)
        
        # Basic structure required by Cloud Logging
        cloud_log = {
            "severity": record["level"].name,
            "time": record["time"].isoformat(),
            "message": record["message"],
            "logging.googleapis.com/labels": {
                "environment": self.env,
                "service": self.service_name
            }
        }
        
        # Add user-specific fields if available
        if "extra" in record:
            for k, v in record["extra"].items():
                cloud_log[k] = v
        
        # Add exception info if available
        if record.get("exception"):
            cloud_log["exception"] = record["exception"]
            
        # Print as JSON for Cloud Logging structured logs
        print(json.dumps(cloud_log), file=sys.stderr)


# Configure Loguru
loguru_logger.configure(
    handlers=[
        {
            "sink": CloudLoggingAdapter().write,
            "format": lambda record: json.dumps({
                "time": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
                "level": {"name": record["level"].name, "no": record["level"].no},
                "message": record["message"],
                "extra": record.get("extra", {}),
                "exception": record["exception"].replace("\n", " ") if record["exception"] else None
            }),
            "serialize": False
        }
    ]
)

# Set level based on settings
loguru_logger.level(settings.LOG_LEVEL)

# Export the logger
logger = loguru_logger
