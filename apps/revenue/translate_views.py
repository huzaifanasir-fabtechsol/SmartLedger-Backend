from rest_framework.decorators import api_view
from rest_framework.response import Response
try:
    from googletrans import Translator
    translator = Translator()
except Exception:
    translator = None

@api_view(['POST'])
def translate_text(request):
    text = request.data.get('text')
    target_lang = request.data.get('target_lang', 'ja')
    
    if not text:
        return Response({'error': 'Text is required'}, status=400)
    
    try:
        result = translator.translate(text, dest=target_lang)
        return Response({'text': result.text})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def translate_batch(request):
    texts = request.data.get('texts', [])
    target_lang = request.data.get('target_lang', 'ja')
    
    if not texts:
        return Response({'error': 'Texts array is required'}, status=400)
    
    try:
        results = translator.translate(texts, dest=target_lang)
        translated = [r.text for r in results]
        return Response({'texts': translated})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
