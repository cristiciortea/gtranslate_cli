import unicodedata
from os import environ
from dotenv import load_dotenv
from google.cloud import translate
import google.auth
import google.oauth2.credentials
load_dotenv()


def list_languages():
    """Lists all available languages."""
    from google.cloud import translate_v2 as translate

    translate_client = translate.Client()

    results = translate_client.get_languages()

    for language in results:
        print(u"{name} ({language})".format(**language))


# [START translate_detect_language]
def detect_language(text):
    """Detects the text's language."""
    from google.cloud import translate_v2 as translate

    translate_client = translate.Client()

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.detect_language(text)

    print("Text: {}".format(text))
    print("Confidence: {}".format(result["confidence"]))
    print("Language: {}".format(result["language"]))


def translate_text(target, text):
    """Translates text into the target language.
    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """
    import six
    from google.cloud import translate_v2 as translate

    # credentials = google.oauth2.credentials.Credentials(
    #     'access_token',
    #     refresh_token='refresh_token',
    #     token_uri='https://oauth2.googleapis.com/token',
    #     client_id='409062876654-loa7grareds74bm9l0lms9jnh3karctk.apps.googleusercontent.com',
    #     client_secret='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')

    credentials, project = google.auth.default()
    translate_client = translate.Client(credentials=credentials)

    if isinstance(text, six.binary_type):
        print('binary')
        text = text.decode("utf-8")
    print(unicodedata.normalize('NFKD', text))

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.translate(text, target_language=target)

    print(u"Text: {}".format(result["input"]))
    print(u"Translation: {}".format(result["translatedText"]))
    print(u"Translation: {}".format(result["translatedText"].encode('utf-8')))
    print(u"Translation: {}".format(result["translatedText"].encode('ascii', 'ignore').decode('utf-8')))
    print(u"Translation: {}".format(result["translatedText"].encode('ascii', 'replace')))
    print(u"Detected source language: {}".format(result["detectedSourceLanguage"]))


translate_text("en", "A porets lakht tsvey mol. Eyn mol lakht er, ven men dartseylt\'em un a tsveytn mol, ven me darklert\'em, vorem farshteyn farshteyt er say-vi-say nit.\”")
