
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response

class CustomAPIException(Exception):
    def __init__(self, message, status_code=400, data=None):
        self.message = message
        self.status_code = status_code
        self.data = data or {}
        super().__init__(message)


def custom_exception_handler(exc, context):
    # Handle your custom exception
    if isinstance(exc, CustomAPIException):
        return Response({
            "error": exc.message,
            "details": exc.data
        }, status=exc.status_code)
    
    # Let DRF handle all other exceptions
    response = drf_exception_handler(exc, context)

    # Optional: format non-200 responses
    # if response is not None and not response.status_code // 100 == 2:
    #     response.data = {
    #         "success": False,
    #         "error": response.data.get('detail', 'An error occurred'),
    #         "details": response.data
    #     }

    return response
