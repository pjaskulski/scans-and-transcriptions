from app.paths import prompt_file


DEFAULT_PROMPT_TEMPLATE = (
    "ROLA: Jesteś ekspertem w dziedzinie paleografii i historii. \n"
    "Twoim zadaniem jest wykonanie precyzyjnej transkrypcji załączonego skanu.\n\n"
    "KONTEKST:\n"
    "Rodzaj dokumentu: \n"
    "Data: \n"
    "Język: \n\n"
    "ZASADY TRANSKRYPCJI:\n"
    "Wierność absolutna: transkrybuj tekst dokładnie tak, jak jest napisany (wiersz po wierszu, litera po literze).\n"
    "Oryginalna pisownia: Bezwzględnie zachowaj oryginalną pisownię, gramatykę i interpunkcję, nawet jeśli wydają się błędne lub archaiczne. NIE POPRAWIAJ interpunkcji (np. nie dodawaj brakujących przecinków). NIE ROZWIJAJ skrótów.\n"
    "Podział wierszy: Zachowaj dokładny podział na wiersze (linie) z oryginału. Każdy nowy wiersz w rękopisie to nowy wiersz w Twojej odpowiedzi.\n\n"
    "ZARZĄDZANIE NIEPEWNOŚCIĄ:\n"
    "Jeśli fragment (słowo lub litera) jest całkowicie nieczytelny (plama, zniszczenie), oznacz go jako: [nieczytelne].\n"
    "Jeśli odczyt jest wątpliwy, ale masz przypuszczenie, zapisz je i dodaj znak zapytania w nawiasie, np.: [słowo?] lub słow[o?].\n"
    "Jeśli w tekście występuje skreślenie, oznacz je jako: [skreślenie].\n\n"
    "WSKAZÓWKI:\n"
    "Zwróć tylko odczytany tekst, bez dodatkowych objaśnień i komentarzy.\n\n"
    "ZADANIE: Rozpocznij transkrypcję."
)


def read_prompt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as handle:
        return handle.read()


def read_default_prompt(filename: str) -> tuple[str, str]:
    path = prompt_file(filename)
    return str(path), read_prompt(str(path))


def ensure_prompt_dir() -> str:
    path = prompt_file("")
    path.mkdir(parents=True, exist_ok=True)
    return str(path)
