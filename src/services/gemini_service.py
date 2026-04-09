import json

from google import genai
from google.genai import types


HTR_MODEL_OPTIONS = [
    ("Gemini 3.1 Pro Preview", "gemini-3.1-pro-preview"),
    ("Gemini 3 Flash Preview", "gemini-3-flash-preview"),
    ("Gemini 3.1 Flash-Lite Preview", "gemini-3.1-flash-lite-preview"),
]

ANALYSIS_MODEL_OPTIONS = [
    ("Gemini 3 Flash Preview", "gemini-3-flash-preview"),
    ("Gemini 3.1 Flash-Lite Preview", "gemini-3.1-flash-lite-preview"),
]

BOX_MODEL_OPTIONS = [
    ("Gemini 3 Pro Image Preview", "gemini-3-pro-image-preview"),
    ("Gemini 3.1 Flash Image Preview", "gemini-3.1-flash-image-preview"),
]

TTS_MODEL_OPTIONS = [
    ("Gemini 2.5 Flash Text-to-Speech", "gemini-2.5-flash-preview-tts"),
]

DEFAULT_HTR_MODEL = "gemini-3.1-pro-preview"
DEFAULT_ANALYSIS_MODEL = "gemini-3-flash-preview"
DEFAULT_BOX_MODEL = "gemini-3-pro-image-preview"
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"

MODEL_OPTIONS = {
    "htr": HTR_MODEL_OPTIONS,
    "analysis": ANALYSIS_MODEL_OPTIONS,
    "box": BOX_MODEL_OPTIONS,
    "tts": TTS_MODEL_OPTIONS,
}

DEFAULT_MODELS = {
    "htr": DEFAULT_HTR_MODEL,
    "analysis": DEFAULT_ANALYSIS_MODEL,
    "box": DEFAULT_BOX_MODEL,
    "tts": DEFAULT_TTS_MODEL,
}


def model_choices(task_type: str) -> list[tuple[str, str]]:
    return MODEL_OPTIONS[task_type]


def model_labels(task_type: str) -> list[str]:
    return [label for label, _ in model_choices(task_type)]


def model_label_for_code(task_type: str, code: str) -> str:
    for label, value in model_choices(task_type):
        if code == value:
            return label
    default_code = DEFAULT_MODELS[task_type]
    for label, value in model_choices(task_type):
        if value == default_code:
            return label
    return model_choices(task_type)[0][0]


def model_code_for_label(task_type: str, label: str) -> str:
    for option_label, code in model_choices(task_type):
        if option_label == label:
            return code
    return DEFAULT_MODELS[task_type]


def normalize_model_selection(task_type: str, code: str | None) -> str:
    allowed_codes = {value for _, value in model_choices(task_type)}
    if code in allowed_codes:
        return code
    return DEFAULT_MODELS[task_type]


def _default_image_config():
    return types.GenerateContentConfig(
        temperature=0,
        thinkingConfig=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        media_resolution=types.MediaResolution.MEDIA_RESOLUTION_HIGH,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def transcribe_image(api_key: str, prompt_text: str, image_path: str, model_name: str = DEFAULT_HTR_MODEL):
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
        model=model_name,
        contents=contents,
        config=_default_image_config(),
    )
    return model_name, response


def stream_transcribe_image(
    api_key: str, prompt_text: str, image_path: str, model_name: str = DEFAULT_HTR_MODEL
):
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

    def response_stream():
        client = genai.Client(api_key=api_key)
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=_default_image_config(),
        )
        for response in stream:
            yield response

    return model_name, response_stream()


def verify_transcription(
    api_key: str, image_path: str, original_text: str, model_name: str = DEFAULT_HTR_MODEL
):
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
        model=model_name,
        contents=[
            types.Part.from_text(text=prompt + "\nTranskrypcja: " + original_text),
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
        config=_default_image_config(),
    )
    return model_name, response


def extract_entities(api_key: str, text: str, model_name: str = DEFAULT_ANALYSIS_MODEL):
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
        model=model_name,
        contents=prompt + "\nTekst: " + text,
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        ),
    )
    return model_name, response


def locate_entities(
    api_key: str,
    image_path: str,
    entities_to_find: list[tuple[str, str]],
    model_name: str = DEFAULT_BOX_MODEL,
):
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
        model=model_name,
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
    return model_name, response


def build_nominative_map(api_key: str, names_list: list[str], model_name: str = DEFAULT_ANALYSIS_MODEL):
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
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            ),
        )

        if response.usage_metadata:
            usage_entries.append((model_name, response.usage_metadata))

        if response.text:
            json_str = response.text.replace("```json", "").replace("```", "").strip()
            nominative_map.update(json.loads(json_str))

    return nominative_map, usage_entries


def synthesize_speech(
    api_key: str,
    text: str,
    voice_name: str = "Enceladus",
    model_name: str = DEFAULT_TTS_MODEL,
):
    client = genai.Client(api_key=api_key)
    prompt = """Przeczytaj uważnie podany dalej tekst. Odczytuj dokładnie,
oddając oryginalne brzmienie także słów archaicznych.
Tekst:
"""

    response = client.models.generate_content(
        model=model_name,
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
    return model_name, response
