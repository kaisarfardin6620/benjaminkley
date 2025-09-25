from rest_framework.renderers import JSONRenderer
from datetime import datetime

class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')

        if isinstance(data, dict) and 'success' in data:
            return super().render(data, accepted_media_type, renderer_context)

        message = 'Request was successful.'

        if (isinstance(data, dict) and
                'custom_meta' in data and
                isinstance(data.get('custom_meta'), dict) and
                'message' in data.get('custom_meta')):
            
            message = data['custom_meta']['message']
            del data['custom_meta']

        response_data = {
            'success': True,
            'code': response.status_code if response else 200,
            'message': message,
            'timestamp': int(datetime.now().timestamp()),
            'data': data
        }

        return super().render(response_data, accepted_media_type, renderer_context)