"""Language picker: the 10 major Indian languages (by Wikipedia edition + speaker count),
plus English as the usual reference language. code = Wikipedia language subdomain code."""
INDIAN_LANGUAGES = [
    ("Hindi", "hi"), ("Bengali", "bn"), ("Telugu", "te"), ("Marathi", "mr"),
    ("Tamil", "ta"), ("Urdu", "ur"), ("Gujarati", "gu"), ("Kannada", "kn"),
    ("Malayalam", "ml"), ("Punjabi", "pa"),
]
REFERENCE_LANGUAGES = [("English", "en")] + INDIAN_LANGUAGES
ALL_LANGUAGES = REFERENCE_LANGUAGES + [("Odia", "or"), ("Assamese", "as"), ("Maithili", "mai"),
                                       ("Sanskrit", "sa"), ("Nepali", "ne")]
NAME_BY_CODE = {code: name for name, code in ALL_LANGUAGES}
