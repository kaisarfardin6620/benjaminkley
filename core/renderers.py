from rest_framework.renderers import JSONRenderer
import time

class CustomJSONRenderer(JSONRenderer):
    """
    A custom renderer to create a flat API response structure with a timestamp.

    - For success: { "success": true, "code": 200, "message": "...", "timestamp": ..., "data": ... }
    - For errors:  { "success": false, "code": 400, "message": "...", "timestamp": ..., "errors": ... }
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')
        status_code = response.status_code
        is_success = 200 <= status_code < 300

        # Check if the view/serializer passed a special 'custom_meta' block
        # .pop() removes it from the data so it isn't rendered twice.
        custom_meta_data = data.pop('custom_meta', {}) if isinstance(data, dict) else {}
        
        # Determine the message: use the custom one if provided, otherwise use defaults.
        message = custom_meta_data.get('message', 'Success' if is_success else data.get('detail', 'An error occurred.'))

        # Start building the final response dictionary with the flat keys
        custom_response = {
            'success': is_success,
            'code': status_code,
            'message': message,
            'timestamp': int(time.time())
        }

        # Add either a 'data' or 'errors' key based on success or failure
        if is_success:
            custom_response['data'] = data
        else:
            custom_response['errors'] = data

        # Let the parent renderer handle the final conversion to a JSON string
        return super().render(custom_response, accepted_media_type, renderer_context)