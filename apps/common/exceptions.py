import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Standardized DRF Exception Handler.
    Returns consistent response format:
    {
        "success": False,
        "error": {
            "type": "...",
            "message": "...",
            "details": ...
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_details = response.data
        message = "An error occurred while processing your request."

        if isinstance(error_details, dict):
            if "detail" in error_details:
                message = str(error_details["detail"])
            elif "non_field_errors" in error_details:
                message = " ".join([str(err) for err in error_details["non_field_errors"]])
            else:
                first_key = next(iter(error_details))
                first_val = error_details[first_key]
                if isinstance(first_val, list) and first_val:
                    message = f"{first_key}: {first_val[0]}"
                else:
                    message = f"{first_key}: {first_val}"
        elif isinstance(error_details, list) and error_details:
            message = str(error_details[0])

        response.data = {
            "success": False,
            "error": {
                "type": exc.__class__.__name__,
                "message": message,
                "details": error_details,
            },
        }
    else:
        # Unexpected internal error: Log without exposing internal details
        logger.exception("Unhandled server exception: %s", exc, exc_info=context.get("request"))
        response = Response(
            {
                "success": False,
                "error": {
                    "type": "InternalServerError",
                    "message": "A server error occurred. Please contact the administrator.",
                    "details": None,
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
