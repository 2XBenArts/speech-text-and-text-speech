# views.py
import json
import os
import tempfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import whisper
import requests
from pydub import AudioSegment
from urllib.parse import urlparse

def get_audio_file(data):
    """
    Get audio file from various input methods.
    
    Args:
    data (dict): Request data containing audio information
    
    Returns:
    str: Path to the audio file
    """
    if 'audio_file' in data:
        # Handle file upload
        uploaded_file = data['audio_file']
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_file.close()
        return temp_file.name
    
    elif 'audio_url' in data:
        # Handle URL input
        return download_audio(data['audio_url'])
    
    elif 'audio_path' in data:
        # Handle local file path
        if os.path.exists(data['audio_path']):
            return data['audio_path']
        else:
            raise FileNotFoundError(f"File not found: {data['audio_path']}")
    
    else:
        raise ValueError("No audio input provided")

def download_audio(url):
    """
    Download audio file from the given URL.
    
    Args:
    url (str): URL of the audio file
    
    Returns:
    str: Path to the downloaded temporary file
    """
    response = requests.get(url)
    if response.status_code == 200:
        file_extension = os.path.splitext(urlparse(url).path)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, mode='wb') as temp_file:
            temp_file.write(response.content)
            return temp_file.name
    else:
        raise Exception(f"Failed to download audio: HTTP {response.status_code}")

def convert_to_wav(input_file):
    """
    Convert the input audio file to WAV format.
    
    Args:
    input_file (str): Path to the input audio file
    
    Returns:
    str: Path to the converted WAV file
    """
    audio = AudioSegment.from_file(input_file)
    wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    audio.export(wav_file.name, format="wav")
    return wav_file.name

def transcribe_audio(file_path):
    """
    Transcribe audio file using OpenAI's Whisper model.
    
    Args:
    file_path (str): Path to the audio file
    
    Returns:
    str: Transcribed text
    """
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]

def cleanup(*file_paths):
    """
    Remove temporary audio files.
    
    Args:
    *file_paths (str): Paths to the files to be removed
    """
    for file_path in file_paths:
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error removing file {file_path}: {e}")

# views.py

@csrf_exempt
@require_http_methods(["POST"])
def transcribe_view(request):
    """
    Django view to handle audio transcription requests.

    Accepts audio file uploads in different formats (mp3, wav, ogg, etc.).
    Returns transcribed text as a JSON response.
    """
    try:
        if 'audio' not in request.FILES:
            return JsonResponse({"error": "No audio file provided"}, status=400)

        audio_file = request.FILES['audio']

        file_extension = os.path.splitext(audio_file.name)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            for chunk in audio_file.chunks():
                temp_file.write(chunk)
        
        input_file_path = temp_file.name

        if file_extension != ".wav":
            audio = AudioSegment.from_file(input_file_path)
            wav_file_path = tempfile.mktemp(suffix='.wav')
            audio.export(wav_file_path, format="wav")
        else:
            wav_file_path = input_file_path

        model = whisper.load_model("base")
        result = model.transcribe(wav_file_path)
        transcription = result["text"]
        
        os.remove(input_file_path)
        if file_extension != ".wav":
            os.remove(wav_file_path)

        return JsonResponse({"transcription": transcription})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)








# install chat history
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatHistory
import json

@csrf_exempt
def model_update(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        input_text = data.get('input_text')
        output_text = data.get('output_text')
        
        # Create a title from the first 4 words of the output
        title = ' '.join(output_text.split()[:4]) + '...'
        
        chat_history = ChatHistory.objects.create(
            title=title,
            input_text=input_text,
            output_text=output_text
        )
        
        return JsonResponse({
            'id': chat_history.id,
            'title': chat_history.title,
            'timestamp': chat_history.timestamp.isoformat()
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)