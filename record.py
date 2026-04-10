import sounddevice as sd
import scipy.io.wavfile as wav

DUREE  = 10       # secondes d'enregistrement
SAMPLE = 16000    # fréquence requise par Whisper

print("Enregistrement en cours... parle !")
audio = sd.rec(DUREE * SAMPLE, samplerate=SAMPLE,
               channels=1, dtype='int16')
sd.wait()
wav.write("enregistrement.wav", SAMPLE, audio)
print("Terminé ! Fichier sauvegardé : enregistrement.wav")