
from django.http import FileResponse, Http404
import os
from django.conf import settings

def serve_obj_file(request, filename):
    obj_path = os.path.join(settings.MEDIA_ROOT, 'scans', 'outputs', filename)
    if not os.path.exists(obj_path):
        raise Http404("OBJ file not found")
    response = FileResponse(open(obj_path, 'rb'), content_type='application/octet-stream')
    response['Access-Control-Allow-Origin'] = '*'
    return response