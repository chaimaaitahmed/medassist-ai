import warnings
warnings.filterwarnings("ignore")

import whisper
import ollama
import json
import re
from flask import Flask, request, jsonify, send_file
from datetime import datetime

app = Flask(__name__)

print("Chargement de Whisper small...")
modele_stt = whisper.load_model("small")
print("Whisper prêt !")
print("Ollama + qwen2.5:1.5b sera appelé à chaque analyse.")

# ─────────────────────────────────────────────
#  EXTRACTION NLP via Ollama (qwen2.5:1.5b)
# ─────────────────────────────────────────────
PROMPT_SYSTEME = """Tu es un assistant médical expert. 
On te donne la transcription d'une conversation aux urgences.
Extrais UNIQUEMENT les informations médicales présentes dans le texte.
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, sans balises markdown.
Si une information est absente, mets une liste vide [].

Format JSON attendu :
{
  "symptomes": [],
  "allergies": [],
  "antecedents": [],
  "medicaments": [],
  "constantes": [],
  "patient_info": [],
  "examens": [],
  "contexte": [],
  "motif_consultation": "",
  "severite": "faible"
}

Règles :
- symptomes : douleurs, nausées, fièvre, tout signe clinique mentionné
- allergies : toute allergie ou intolérance mentionnée
- antecedents : maladies chroniques, hospitalisations passées, chirurgies
- medicaments : tous les médicaments cités, avec dosage si mentionné
- constantes : TA, FC, SpO2, température, glycémie, Glasgow, EVA
- patient_info : âge, sexe, poids si mentionnés
- examens : ECG, radio, prise de sang, scanner, tout examen cité
- contexte : comment le patient est arrivé, circonstances
- motif_consultation : résume en une phrase courte le motif principal
- severite : "faible", "modere" ou "eleve" selon les symptômes
- Ne pas inventer d'informations absentes du texte
- Gérer la négation : "pas de fièvre" → ne pas mettre fièvre dans symptomes
"""

def extraire_entites_ollama(texte):
    try:
        response = ollama.chat(
            model="qwen2.5:1.5b",
            messages=[
                {
                    "role": "system",
                    "content": PROMPT_SYSTEME
                },
                {
                    "role": "user",
                    "content": f"Voici la transcription à analyser :\n\n{texte}"
                }
            ],
            options={
                "temperature": 0.1,
                "num_predict": 512,
            }
        )

        contenu = response["message"]["content"].strip()

        # Nettoyer si le modèle ajoute des balises markdown
        contenu = re.sub(r"```json\s*", "", contenu)
        contenu = re.sub(r"```\s*", "", contenu)
        contenu = contenu.strip()

        entites = json.loads(contenu)

        # S'assurer que toutes les clés existent
        cles = ["symptomes", "allergies", "antecedents", "medicaments",
                "constantes", "patient_info", "examens", "contexte",
                "motif_consultation", "severite"]
        for cle in cles:
            if cle not in entites:
                entites[cle] = [] if cle not in ["motif_consultation", "severite"] else ""

        return entites, None

    except json.JSONDecodeError as e:
        print(f"Erreur parsing JSON Ollama : {e}")
        print(f"Réponse brute : {contenu}")
        return entites_vides(), f"Erreur parsing JSON : {str(e)}"
    except Exception as e:
        print(f"Erreur Ollama : {e}")
        return entites_vides(), str(e)


def entites_vides():
    return {
        "symptomes": [], "allergies": [], "antecedents": [],
        "medicaments": [], "constantes": [], "patient_info": [],
        "examens": [], "contexte": [],
        "motif_consultation": "", "severite": "faible"
    }


# ─────────────────────────────────────────────
#  ROUTES FLASK
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_file("index.html")


@app.route("/analyser", methods=["POST"])
def analyser():
    if "audio" not in request.files:
        return jsonify({"erreur": "Aucun fichier audio reçu"}), 400

    fichier = request.files["audio"]
    fichier.save("temp.wav")

    # ── Transcription Whisper ──
    print("Transcription en cours...")
    resultat_stt = modele_stt.transcribe(
        "temp.wav",
        language="fr",
        temperature=0.0,
        beam_size=5,
        best_of=5,
        condition_on_previous_text=True,
        initial_prompt=(
            "Transcription médicale aux urgences. "
            "Vocabulaire : symptômes, constantes vitales, médicaments, "
            "antécédents, allergies, douleur thoracique, tension artérielle, "
            "fréquence cardiaque, saturation, température."
        ),
    )
    texte = resultat_stt["text"].strip()
    duree = round(resultat_stt.get("duration", 0), 1)
    print(f"Transcription : {texte}")

    # ── Extraction NLP via Ollama ──
    print("Extraction NLP via qwen2.5:1.5b...")
    entites, erreur = extraire_entites_ollama(texte)
    print(f"Entités extraites : {entites}")

    return jsonify({
        "transcription": texte,
        "entites": entites,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "duree_audio": duree,
        "erreur_nlp": erreur,
    })


@app.route("/tester-ollama", methods=["GET"])
def tester_ollama():
    """Route de test pour vérifier qu'Ollama fonctionne."""
    try:
        response = ollama.chat(
            model="qwen2.5:1.5b",
            messages=[{"role": "user", "content": "Réponds juste: ok"}],
            options={"num_predict": 5}
        )
        return jsonify({"status": "ok", "reponse": response["message"]["content"]})
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)