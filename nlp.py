import re
import json

def extraire_entites(texte):
    patterns = {
        "symptomes": [
            r"douleur\s+\w+",
            r"nausée[s]?",
            r"fièvre",
            r"sueurs?\s+\w+",
            r"doulor\w+\s+\w+",  # capture les variantes Whisper
        ],
        "allergies": [
            r"allergi\w+\s+(?:à|au|aux)\s+([\w]+)",
        ],
        "antecedents": [
            r"hypertensi\w+",
            r"diabète",
            r"cardiaque",
            r"asthme",
        ],
        "medicaments": [
            r"[A-Z][a-z]+(?:ine|ol|am|ate|pine)\b",
        ],
    }

    resultats = {}
    for categorie, regexes in patterns.items():
        trouve = []
        for r in regexes:
            matches = re.findall(r, texte, re.IGNORECASE)
            trouve += matches
        resultats[categorie] = list(set(trouve))

    return resultats

# Test avec ta transcription
texte = """Le patient présente une dolorité uracique depuis ce matin.
Elle est allergique à la pénicilline et prend de l'Amlodipine."""

entites = extraire_entites(texte)
print(json.dumps(entites, ensure_ascii=False, indent=2))