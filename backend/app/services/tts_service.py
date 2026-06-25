from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

def synthesize_speech(text):

    input_text = texttospeech.SynthesisInput(
        text=text
    )

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-IN",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config
    )

    return response.audio_content