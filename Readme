# MedAssist AI

An intelligent voice-based medical assistant designed for emergency departments.
It listens to conversations between medical staff and patients, transcribes them in real time, and automatically extracts structured medical information — entirely offline, at no cost.

---

## The Problem

In emergency settings, physicians are under constant pressure to act fast while simultaneously gathering critical information about the patient. When patients are unconscious, disoriented, or unable to communicate, this information often comes from companions or paramedics — verbally, under stress, and without structure.

The result: key details get lost, misheard, or forgotten before they can be documented. This creates real risks in diagnosis and treatment decisions.

---

## What MedAssist AI Does

MedAssist AI captures the spoken exchange in the room, converts it to text using a local speech recognition model, and passes that text to a language model that understands medical French. The output is a clean, structured patient summary — symptoms, allergies, current medications, medical history, vital signs — ready to read or download in seconds.

No cloud. No subscription. No internet required.

---

## How It Works

```
Microphone input
      ↓
Audio capture — sounddevice
      ↓
Speech-to-Text — Whisper (local, offline)
      ↓
Medical NLP — Ollama + qwen2.5:1.5b (local LLM)
      ↓
Structured JSON output
      ↓
Web interface — Flask + HTML/CSS/JS
```

---

## Stack

| Component | Purpose |
|-----------|---------|
| Whisper (OpenAI) | French speech-to-text, runs fully offline |
| Ollama | Local LLM inference server |
| qwen2.5:1.5b | Medical entity extraction via structured prompting |
| Flask | Backend API, orchestrates the pipeline |
| sounddevice | Microphone capture |
| HTML / CSS / JS | Frontend interface |

All components are free and open source. The entire system runs on a standard laptop with no GPU.

---

## Extracted Medical Entities

The language model is prompted to identify and classify the following from the transcription :

- Symptoms
- Known allergies
- Medical history and chronic conditions
- Current medications and dosages
- Vital signs (blood pressure, heart rate, SpO2, temperature, etc.)
- Patient information (age, sex, weight if mentioned)
- Requested or performed examinations
- Context of arrival (ambulance, fall, road accident, etc.)

It also handles negation correctly — "no fever" will not appear under symptoms.

---

## Installation

**Requirements**

- Python 3.8+
- [Ollama](https://ollama.com/download) installed and running
- ffmpeg installed (`winget install ffmpeg` on Windows)
- A microphone

**Setup**

```bash
git clone https://github.com/YOUR_USERNAME/medassist-ai.git
cd medassist-ai

pip install -r requirements.txt
python -m spacy download fr_core_news_sm

ollama pull qwen2.5:1.5b
```

Start Ollama (open the desktop app or run `ollama serve`), then launch the app :

```bash
python app.py
```

Open your browser at `http://127.0.0.1:5000`.

---

## Usage

1. Click **Start recording**
2. Speak naturally in French — the system handles medical vocabulary
3. Click **Stop**
4. Wait 20 to 30 seconds for transcription and analysis
5. Review the generated patient summary
6. Download the full report if needed

---

## Configuration

To change the LLM based on available RAM :

```python
# in app.py
model = "qwen2.5:1.5b"   # ~2 GB RAM — default
model = "mistral"          # ~5 GB RAM — higher accuracy
model = "phi3:mini"        # ~2.3 GB RAM — alternative
```

To change the Whisper model :

```python
modele_stt = whisper.load_model("small")    # faster
modele_stt = whisper.load_model("medium")   # more accurate
```

---

## Current Limitations

- Whisper may struggle with highly specialized medical terminology
- Smaller LLMs (1.5B parameters) occasionally miss complex entities or context
- No persistent storage — patient data is not saved between sessions
- Speaker diarization (identifying who is speaking) is not yet implemented

---

## Roadmap

- Automatic speaker identification (physician / patient / companion)
- Session history and patient database
- Support for Moroccan Arabic (Darija)
- Mobile application
- Integration with existing hospital information systems

---

## License

MIT License