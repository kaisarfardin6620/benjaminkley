# core/renderers.py

from rest_framework.renderers import JSONRenderer
from datetime import datetime

class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')

        # If the response is already in our final format, don't touch it.
        if isinstance(data, dict) and 'success' in data:
            return super().render(data, accepted_media_type, renderer_context)

        is_error = response and response.status_code >= 400
        
        # --- THIS IS THE NEW, INTELLIGENT LOGIC ---
        
        specific_message_found = None

        if isinstance(data, dict):
            # 1. Check for the special 'custom_meta' block from the login response.
            if 'custom_meta' in data and 'message' in data.get('custom_meta', {}):
                specific_message_found = data['custom_meta']['message']
                del data['custom_meta']
            
            # 2. If not found, search for the message in a prioritized list of common keys.
            else:
                # This list can be expanded if your API uses other keys for messages.
                message_keys_in_priority = ['message', 'detail', 'status']
                for key in message_keys_in_priority:
                    if key in data and isinstance(data[key], str):
                        specific_message_found = data[key]
                        break # Stop as soon as we find the first one.

            # 3. If it is an error and we still haven't found a clear message,
            #    it's likely a validation error. We will extract the first error string.
            if is_error and not specific_message_found:
                for value in data.values():
                    if isinstance(value, list) and value and isinstance(value[0], str):
                        specific_message_found = value[0]
                        break
                    elif isinstance(value, str):
                        specific_message_found = value
                        break
        
        # Finally, decide which message to use.
        if specific_message_found:
            message = specific_message_found
        else:
            # Use a smart default based on whether the request succeeded or failed.
            message = "An error occurred." if is_error else "Request was successful."

        # --- END OF NEW LOGIC ---

        response_data = {
            'success': not is_error,
            'code': response.status_code if response else 200,
            'message': message,
            'timestamp': int(datetime.now().timestamp()),
            'data': data
        }

        return super().render(response_data, accepted_media_type, renderer_context)