# logging_config.py - Custom logging configuration for Docker environment
import os
import logging.config
import sys

# Basic logging configuration that doesn't use multiprocessing queues
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': sys.stdout,
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'uvicorn.access': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'asyncio': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Apply this config when in Docker environment
if os.environ.get('PYTHONMULTIPROCESSING') == '1':
    logging.config.dictConfig(LOGGING_CONFIG)
