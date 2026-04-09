import json

from google import genai
from google.genai import types


MODEL_HTR_OCR = "gemini-3-pro-preview"
MODEL_VERIFY = "gemini-3-pro-preview"
MODEL_NER = "gemini-3-pro-preview"
MODEL_BOX = "gemini-3-pro-image-preview"
MODEL_NOMINATIVE = "gemini-flash-latest"
MODEL_TTS = "gemini-2.5-flash-preview-tts"


def _default_image_config():
    return types.GenerateContentConfig(
        temperature=0,
        thinkingConfig=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        media_resolution=types.MediaResolution.MEDIA_RESOLUTION_HIGH,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def transcribe_image(api_key: str, prompt_text: str, image_path: str):
    client = genai.Client(api_key=api_key)

    with open(image_path, "rb") as handle:
        image_bytes = handle.read()

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            ],
        )
    ]

    response = client.models.generate_content(
        model=MODEL_HTR_OCR,
        contents=contents,
        config=_default_image_config(),
    )
    return MODEL_HTR_OCR, response


def stream_transcribe_image(api_key: str, prompt_text: str, image_path: str):
    client = genai.Client(api_key=api_key)

    with open(image_path, "rb") as handle:
        image_bytes = handle.read()

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            ],
        )
    ]

    stream = client.models.generate_content_stream(
        model=MODEL_HTR_OCR,
        contents=contents,
        config=_default_image_config(),
    )
    return MODEL_HTR_OCR, stream


def verify_transcription(api_key: str, image_path: str, original_text: str):
    client = genai.Client(api_key=api_key)

    with open(image_path, "rb") as handle:
        image_bytes = handle.read()

    prompt = """
Otrzymasz skan dokumentu oraz jego wstępną transkrypcję.

Twoim zadaniem jest zweryfikować tekst z obrazem i poprawić wszelkie błędy:
1. Popraw literówki i błędnie odczytane słowa.
2. Uzupełnij pominięte słowa.
3. Zachowaj oryginalny układ wierszy.
4. Nie dodawaj własnych komentarzy, zwróć TYLKO poprawiony tekst.

Pamiętaj o zasadach oznaczania niepewności:
- Jeśli fragment (słowo lub litera) jest całkowicie nieczytelny (plama, zniszczenie), oznacz go jako: [nieczytelne].
- Jeśli odczyt jest wątpliwy, ale masz przypuszczenie, zapisz je i dodaj znak zapytania w nawiasie, np.: [słowo?] lub słow[o?].
- Jeśli w tekście występuje skreślenie, oznacz je jako: [skreślenie].
"""

    response = client.models.generate_content(
        model=MODEL_VERIFY,
        contents=[
            types.Part.from_text(text=prompt + "\nTranskrypcja: " + original_text),
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
        config=_default_image_config(),
    )
    return MODEL_VERIFY, response


def extract_entities(api_key: str, text: str):
    client = genai.Client(api_key=api_key)

    prompt = """
Jesteś ekspertem w dziedzinie historii i paleografii XVIII, XIX oraz XX wieku. Twoim zadaniem
jest ekstrakcja nazw własnych z transkrypcji dokumentów historycznych.

Zasady klasyfikacji:
1. PERS (Osoby): Wyodrębnij nazwy osób, mogą to być pełne imiona i nazwiska, ale także zapisy
   samych nazwisk lub imion, zapisy inicjałów np. A. T., zapisy nazw stosowane w średniowieczu
   np. Jan z Dąbrówki, uwzględnij także nazwy narodów lub plemion. DOŁĄCZ do nazwy towarzyszące im
   tytuły szlacheckie (np. hr., margrabia), stopnie wojskowe (np. kpt., gen.),
   funkcje urzędowe (np. rządzca, wójt) oraz zwroty grzecznościowe (np. JW Pan, Ob.),
   jeśli występują bezpośrednio przy nazwisku.
2. LOC (Geografia): Wyodrębnij nazwy miast, wsi, krajów, państw, folwarków, majątków ziemskich, rzek,
   jezior, guberni oraz konkretne nazwy ulic i placów.
3. ORG (Organizacje): Wyodrębnij nazwy urzędów, instytucji, pułków wojskowych, parafii, komitetów, stowarzyszeń,
   fabryk i towarzystw (np. "Towarzystwo Kredytowe Ziemskie").

Instrukcje techniczne:
- Rekonstrukcja: Jeśli nazwa jest podzielona między wiersze (np. "Krak-" i "ów"),
  połącz ją w jedno słowo bez dywizu ("Kraków").
- Normalizacja: Zwróć nazwy w takiej formie (deklinacji), w jakiej występują w tekście, ale usuń
  znaki podziału wiersza.
- Czystość: Ignoruj nazwy pospolite, chyba że są częścią nazwy własnej.

Zwróć wynik WYŁĄCZNIE jako JSON w formacie:
{
  "PERS": ["nazwa1", ...],
  "LOC": ["nazwa1", ...],
  "ORG": ["nazwa1", ...]
}
"""

    response = client.models.generate_content(
        model=MODEL_NER,
        contents=prompt + "\nTekst: " + text,
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        ),
    )
    return MODEL_NER, response


def locate_entities(api_key: str, image_path: str, entities_to_find: list[tuple[str, str]]):
    client = genai.Client(api_key=api_key)

    with open(image_path, "rb") as handle:
        image_bytes = handle.read()

    entities_str = "".join(f"{name},{category}\n" for name, category in entities_to_find)

    prompt = f"""
Na załączonym obrazie znajdź lokalizację następujących nazw,
(podanych w formie listy par: nazwa_do_wyszukania, kategoria_nazwy, każda para w osobnym wierszu np.
Felicjan Słomkowski, PERS
Gniezno, LOC):

{entities_str}.

Uwzględnij tylko i wyłącznie nazwy z listy, inne zignoruj.
Dla każdej nazwy podaj współrzędne ramki w formacie:

nazwa, nazwa_kategorii [ymin, xmin, ymax, xmax]

na przykład:
Krakowa, LOC [ymin, xmin, ymax, xmax]
Henryk Walezy, PERS [ymin, xmin, ymax, xmax]
...

Wszystkie współrzędne w skali 0-1000.
Zwróć tylko listę tych danych bez żadnych dodatkowych komentarzy.
"""

    response = client.models.generate_content(
        model=MODEL_BOX,
        contents=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            image_config=types.ImageConfig(image_size="1K"),
            response_modalities=["TEXT"],
        ),
    )
    return MODEL_BOX, response


def build_nominative_map(api_key: str, names_list: list[str]):
    client = genai.Client(api_key=api_key)
    nominative_map = {}
    usage_entries = []

    for i in range(0, len(names_list), 50):
        batch = names_list[i:i + 50]
        prompt = (
            "Dla podanej listy nazw własnych z dokumentów historycznych, "
            "podaj ich formę w mianowniku, nie zmieniaj rodzaju nazw (męski, żeński, nijaki). "
            "Zwróć WYŁĄCZNIE czysty JSON: {\"oryginał\": \"mianownik\", ...}. "
            f"Lista: {', '.join(batch)}"
        )

        response = client.models.generate_content(
            model=MODEL_NOMINATIVE,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            ),
        )

        if response.usage_metadata:
            usage_entries.append((MODEL_NOMINATIVE, response.usage_metadata))

        if response.text:
            json_str = response.text.replace("```json", "").replace("```", "").strip()
            nominative_map.update(json.loads(json_str))

    return nominative_map, usage_entries


def synthesize_speech(api_key: str, text: str, voice_name: str = "Enceladus"):
    client = genai.Client(api_key=api_key)
    prompt = """Przeczytaj uważnie podany dalej tekst. Odczytuj dokładnie,
oddając oryginalne brzmienie także słów archaicznych.
Tekst:
"""

    response = client.models.generate_content(
        model=MODEL_TTS,
        contents=prompt + text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    )
                )
            ),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    return MODEL_TTS, response
