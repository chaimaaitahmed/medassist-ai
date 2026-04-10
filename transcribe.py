import whisper
import warnings
warnings.filterwarnings("ignore")


print("Chargement du modèle Whisper...")
modele = whisper.load_model("small")

print("Transcription en cours...")
resultat = modele.transcribe("enregistrement.wav", language="fr")

texte = resultat["text"]
print("\n--- Transcription ---")
print(texte)