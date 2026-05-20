import logging
import os
from django.conf import settings


def setup_logging():
    """Настройка логирования для приложения."""

    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {asctime} {message}',
                'style': '{',
            },
            'detailed': {
                'format': '{levelname} {asctime} {module} {funcName} {lineno} {message}',
                'style': '{',
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'filters': ['require_debug_true'],
            },
            'file_info': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'info.log'),
                'maxBytes': 10485760,  # 10 MB
                'backupCount': 10,
                'formatter': 'verbose',
            },
            'file_error': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'error.log'),
                'maxBytes': 10485760,
                'backupCount': 10,
                'formatter': 'detailed',
            },
            'file_debug': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'debug.log'),
                'maxBytes': 10485760,
                'backupCount': 5,
                'formatter': 'detailed',
            },
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
                'filters': ['require_debug_false'],
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file_info', 'file_error'],
                'level': 'INFO',
                'propagate': True,
            },
            'django.server': {
                'handlers': ['console', 'file_info'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['file_error', 'mail_admins'],
                'level': 'ERROR',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['file_debug'],
                'level': 'WARNING',
                'propagate': False,
            },
            'cinema': {
                'handlers': ['console', 'file_info', 'file_error', 'file_debug'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'cinema.views': {
                'handlers': ['console', 'file_info', 'file_error'],
                'level': 'INFO',
                'propagate': False,
            },
            'cinema.models': {
                'handlers': ['file_info', 'file_debug'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console', 'file_info'],
            'level': 'INFO',
        },
    })