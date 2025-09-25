import logging
import traceback
from datetime import datetime
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    error_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"DRF Exception Traceback:\n{error_trace}")

    response = exception_handler(exc, context)

    if response is not None:
        errors_payload = response.data
        message = "An error occurred."
        if isinstance(errors_payload, dict):
            for value in errors_payload.values():
                if isinstance(value, list) and value:
                    message = value[0]
                    break
                elif isinstance(value, str):
                    message = value
                    break
        elif isinstance(errors_payload, list) and errors_payload:
            message = errors_payload[0]

        response.data = {
            'success': False,
            'code': response.status_code,
            'message': message,
            'timestamp': int(datetime.now().timestamp()),
            'errors': errors_payload
        }

    return response