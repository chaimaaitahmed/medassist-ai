import warnings
warnings.filterwarnings("ignore")
import os
import whisper
import ollama
import json
import re
from flask import Flask, request, jsonify, send_file,  redirect, url_for, flash, render_template
from datetime import datetime
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

app = Flask(__name__)
app = Flask(__name__, template_folder='template')
app.secret_key = 'medassist_ai_key_2024' 
# --- CONFIGURATION MYSQL ---
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'      # Par défaut sur XAMPP
app.config['MYSQL_PASSWORD'] = ''      # Par défaut vide sur XAMPP
app.config['MYSQL_DB'] = 'medassist_db' # Le nom de ta base de données

mysql = MySQL(app) # <--- C'est ici qu'on définit 'mysql' !
# ---------------------------

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
# @app.route("/urgence")
# def urgence():
    
#      stats_medassist = {
#         "total_patients": 24,
#         "avg_time": "5m 12s",
#         "alerts": 2,
#         "ai_accuracy": "97%"
#     }
    
#     # 2. On utilise render_template (et on passe les stats à la page)
#     # IMPORTANT : dashboard.html DOIT être dans le dossier "templates" (avec un s)
#      return render_template("dashboard.html", stats=stats_medassist)

# @app.route("/urgence")
# def urgence():
#     cur = mysql.connection.cursor()

#     # 1. Stats simples
#     cur.execute("SELECT COUNT(*) FROM patients WHERE DATE(created_at) = CURDATE()")
#     total_patients = cur.fetchone()[0]

#     cur.execute("SELECT COUNT(*) FROM consultations WHERE niveau_severite = 'Élevé'")
#     alerts = cur.fetchone()[0]

#     # 2. Données pour le graphique ligne (7 derniers jours)
#     # On récupère les jours et le nombre de patients
#     cur.execute("SELECT DATE_FORMAT(created_at, '%a'), COUNT(*) FROM patients GROUP BY DATE(created_at) LIMIT 7")
#     res_line = cur.fetchall()
#     labels = [r[0] for r in res_line]
#     values = [r[1] for r in res_line]

#     # 3. Données pour le Doughnut (Répartition par statut)
#     cur.execute("SELECT status, COUNT(*) FROM patients GROUP BY status")
#     res_pie = cur.fetchall()
#     d_labels = [r[0] for r in res_pie]
#     d_values = [r[1] for r in res_pie]

#     cur.close()

#     stats = {
#         "total_patients": total_patients,
#         "avg_time": "3m 45s",
#         "alerts": alerts,
#         "ai_accuracy": "97.5%"
#     }

#     return render_template("dashboard.html", stats=stats, labels=labels, values=values, d_labels=d_labels, d_values=d_values)

@app.route("/urgence")
def urgence():
    # Sécurité : si personne n'est connecté, retour au login
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 1. Vrai nombre de patients aujourd'hui
    cur.execute("SELECT COUNT(*) FROM patients WHERE DATE(created_at) = CURDATE()")
    vrai_total = cur.fetchone()[0]

    # 2. Vrai nombre d'alertes (consultations avec sévérité élevée)
    cur.execute("SELECT COUNT(*) FROM consultations WHERE niveau_severite = 'Élevé' OR niveau_severite = 'Critique'")
    vraies_alertes = cur.fetchone()[0]

    cur.close()

    # On prépare le dictionnaire pour le HTML
    stats_reelles = {
        "total_patients": vrai_total,
        "avg_time": "3m 45s", # Tu pourras le calculer plus tard
        "alerts": vraies_alertes,
        "ai_accuracy": "98%"
    }

    return render_template("dashboard.html", stats=stats_reelles)



@app.route("/home")
def home():
    # os.getcwd() donne déjà l'adresse du dossier 'medassist-ai'
    # Donc on cherche index.html directement à la racine
    chemin = os.path.join(os.getcwd(), "index.html") 
    return send_file(chemin)
@app.route("/")
def index():
     chemin_fichier = os.path.join(os.getcwd(), "template", "login.html")
     return send_file(chemin_fichier)

# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         email = request.form.get("email")
#         password = request.form.get("password")

#         cur = mysql.connection.cursor()
#         cur.execute("SELECT * FROM users WHERE email = %s", (email,))
#         user = cur.fetchone()
#         cur.close()

#         print(f"DEBUG: Utilisateur trouvé -> {user}") # Affiche les données dans ton terminal

#         if user:
#             mot_de_passe_db = user[5] # Vérifie ici si c'est bien l'index 5
#             if check_password_hash(mot_de_passe_db, password):
#                 return redirect(url_for('urgence'))
#             else:
#                 print("DEBUG: Le mot de passe ne correspond pas au hash.")
#         else:
#             print("DEBUG: Aucun utilisateur trouvé avec cet email.")

#         return "Email ou mot de passe incorrect"

#     return redirect(url_for('index'))


from flask import session # Assure-toi que 'session' est importé en haut

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            # Vérifie bien tes index (5 pour password, 8 pour role selon ton code)
            mot_de_passe_db = user[5] 
            nom_utilisateur = user[1] 
            role_utilisateur = user[8] 

            if check_password_hash(mot_de_passe_db, password):
                session['user_id'] = user[0]
                session['user_name'] = nom_utilisateur
                session['role'] = role_utilisateur
                
                return redirect(url_for('urgence')) 
            else:
                # ERREUR : Mot de passe incorrect
                return render_template("login.html", error="Mot de passe incorrect.")
        else:
            # ERREUR : Email non trouvé
            return render_template("login.html", error="Aucun compte trouvé avec cet email.")

    # Si c'est un GET, on affiche la page normalement
    return render_template("login.html")



# Route pour supprimer (Seulement secrétaire)
@app.route("/delete_patient/<int:id>")
def delete_patient(id):
    if session.get('role') != 'secretary':
        return "Accès interdit : Réservé au secrétariat", 403
    
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM patients WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('page_patients'))

# Route pour l'assistant vocal (Seulement docteur)

# --- ÉTAPE 1 : DEMANDER L'EMAIL ---
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            # On stocke temporairement l'ID dans la session pour savoir qui réinitialise
            session['reset_id'] = user[0]
            return redirect(url_for('reset_password'))
        else:
            return "Email introuvable dans notre base de données."

    return render_template("forgot_password.html")

# --- ÉTAPE 2 : DÉFINIR LE NOUVEAU MOT DE PASSE ---
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if 'reset_id' not in session:
        return redirect(url_for('index'))

    if request.method == "POST":
        new_password = request.form.get("password")
        hashed_password = generate_password_hash(new_password)

        try:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET password = %s WHERE id = %s", 
                        (hashed_password, session['reset_id']))
            mysql.connection.commit()
            cur.close()
            
            # On nettoie la session et on redirige vers le login
            session.pop('reset_id', None)
            return redirect(url_for('index'))
        except Exception as e:
            return f"Erreur : {e}"

    return render_template("reset_password.html")


@app.route("/se_connecter")
def registerr():
     chemin_fichier = os.path.join(os.getcwd(), "template", "register.html")

     return send_file(chemin_fichier)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # 1. On récupère les données
        nom = request.form.get("name")
        email = request.form.get("email")
        specialite = request.form.get("specialty")
        id_docteur = request.form.get("doctor_id")
        mdp = request.form.get("password")
        role = request.form.get("role") 

        mdp_crypte = generate_password_hash(mdp)

        try:
            # 2. Tentative d'insertion (Tout ce qui est dans le 'try' est décalé)
            cur = mysql.connection.cursor()
            sql = """
                INSERT INTO users (name, email, specialty, doctor_id, password, role) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            valeurs = (nom, email, specialite, id_docteur, mdp_crypte, role)
            
            cur.execute(sql, valeurs)
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('index'))

        except Exception as e:
            # 3. Gestion d'erreur (Le 'except' est aligné avec le 'try')
            print(f"Erreur SQL détaillée : {e}")
            return f"Erreur MySQL : {e}"

    # 4. Affichage de la page (Le code ci-dessous est aligné avec le premier 'if')
    chemin_fichier = os.path.join(os.getcwd(), "template", "register.html")
    return send_file(chemin_fichier)
@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    cur = mysql.connection.cursor()
    # On récupère toutes les infos du médecin
    cur.execute("SELECT name, email, specialty, doctor_id FROM users WHERE id = %s", (session['user_id'],))
    user_data = cur.fetchone()
    cur.close()

    return render_template("profile.html", user=user_data)


# --- PAGE FORMULAIRE DE MODIFICATION ---
@app.route("/edit_profile")
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, email, specialty, doctor_id FROM users WHERE id = %s", (session['user_id'],))
    user_data = cur.fetchone()
    cur.close()
    return render_template("edit_profile.html", user=user_data)

# --- ACTION DE MISE À JOUR DANS LA BASE DE DONNÉES ---
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    if request.method == "POST":
        new_name = request.form.get("name")
        new_specialty = request.form.get("specialty")
        new_doctor_id = request.form.get("doctor_id")
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE users 
                SET name = %s, specialty = %s, doctor_id = %s 
                WHERE id = %s
            """, (new_name, new_specialty, new_doctor_id, session['user_id']))
            
            mysql.connection.commit()
            cur.close()
            
            # Mettre à jour le nom dans la session pour que le Dashboard change aussi
            session['user_name'] = new_name
            
            return redirect(url_for('profile'))
        except Exception as e:
            return f"Erreur lors de la mise à jour : {e}"
        
# @app.route("/analyser", methods=["POST"])
# def analyser():
#     if "audio" not in request.files:
#         return jsonify({"erreur": "Aucun fichier audio reçu"}), 400

#     fichier = request.files["audio"]
#     fichier.save("temp.wav")

#     # ── Transcription Whisper ──
#     print("Transcription en cours...")
#     resultat_stt = modele_stt.transcribe(
#         "temp.wav",
#         language="fr",
#         temperature=0.0,
#         beam_size=5,
#         best_of=5,
#         condition_on_previous_text=True,
#         initial_prompt=(
#             "Transcription médicale aux urgences. "
#             "Vocabulaire : symptômes, constantes vitales, médicaments, "
#             "antécédents, allergies, douleur thoracique, tension artérielle, "
#             "fréquence cardiaque, saturation, température."
#         ),
#     )
#     texte = resultat_stt["text"].strip()
#     duree = round(resultat_stt.get("duration", 0), 1)
#     print(f"Transcription : {texte}")

#     # ── Extraction NLP via Ollama ──
#     print("Extraction NLP via qwen2.5:1.5b...")
#     entites, erreur = extraire_entites_ollama(texte)
#     print(f"Entités extraites : {entites}")

#     return jsonify({
#         "transcription": texte,
#         "entites": entites,
#         "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
#         "duree_audio": duree,
#         "erreur_nlp": erreur,
#     })


@app.route("/patients") # <--- L'adresse exacte à taper dans le navigateur
def page_patients():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    cur = mysql.connection.cursor()
    # On récupère tous les patients pour les afficher dans le tableau
    cur.execute("SELECT id, first_name, last_name, age, gender, cin, status, created_at FROM patients ORDER BY created_at DESC")
    patients_data = cur.fetchall()
    cur.close()

    # On utilise render_template pour envoyer les données ET le rôle
    return render_template("patients.html", patients=patients_data)

@app.route("/api/add_patient", methods=["GET", "POST"]) # On ajoute GET pour éviter l'erreur 404 en test
def add_patient():
    if request.method == "POST":
        nom = request.form.get("last_name")
        prenom = request.form.get("first_name")
        age = request.form.get("age")
        genre = request.form.get("gender")
        cin = request.form.get("cin")
        status = request.form.get("status")

        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO patients (first_name, last_name, age, gender, cin, status) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (prenom, nom, age, genre, cin, status))
            mysql.connection.commit()
            cur.close()
            # Une fois ajouté, on recharge la page des patients
            return redirect(url_for('page_patients'))
        except Exception as e:
            return f"Erreur MySQL : {e}"
    
    # Si on essaie d'accéder à l'API via l'URL, on redirige vers la page principale
    return redirect(url_for('page_patients'))

@app.route("/api/get_patients")
def get_patients():
    try:
        cur = mysql.connection.cursor()
        # On sélectionne bien les 8 colonnes (0 à 7)
        cur.execute("SELECT id, first_name, last_name, age, gender, cin, status, created_at FROM patients ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        
        liste = []
        for r in rows:
            liste.append({
                "id": r[0],
                "first_name": r[1],
                "last_name": r[2],
                "age": r[3],
                "gender": r[4],
                "cin": r[5],
                "status": r[6],
                # Vérification : si la date existe, on la formate, sinon texte vide
                "date": r[7].strftime('%d/%m/%Y %H:%M') if r[7] else "---"
            })
        return jsonify(liste)
    except Exception as e:
        print(f"Erreur Python : {e}")
        return jsonify({"erreur": str(e)}), 500
    
# --- ACTION : SÉLECTIONNER UN PATIENT POUR L'URGENCE ---
@app.route("/select_patient/<int:id>")
def select_patient(id):
    # On stocke l'ID du patient dans la session pour que la page /analyser sache qui est traité
    session['current_patient_id'] = id
    return redirect(url_for('urgence'))



from flask import session # N'oublie pas d'ajouter session dans tes imports Flask

@app.route("/analyser", methods=["POST"])
def analyser():
    if "audio" not in request.files:
        return jsonify({"erreur": "Aucun fichier audio reçu"}), 400

    fichier = request.files["audio"]
    fichier.save("temp.wav")

    # 1. Transcription Whisper
    print("Transcription en cours...")
    resultat_stt = modele_stt.transcribe(
        "temp.wav",
        language="fr",
        # ... (tes options Whisper)
    )
    texte = resultat_stt["text"].strip()
    duree = round(resultat_stt.get("duration", 0), 1)

    # 2. Extraction NLP via Ollama
    print("Extraction NLP...")
    entites, erreur = extraire_entites_ollama(texte)

    # 3. ENREGISTREMENT DANS LA BASE DE DONNÉES
    try:
        # On récupère l'ID du médecin connecté et du patient sélectionné
        # (Si pas de patient, on peut mettre un ID par défaut pour le test)
        doctor_id = session.get('user_id', 1) 
        patient_id = session.get('current_patient_id', 1) 

        cur = mysql.connection.cursor()
        
        # Préparation des données (on transforme les listes en texte séparé par des virgules)
        sql = """INSERT INTO consultations (
            patient_id, doctor_id, transcription_complete, confiance_stt,
            entites_symptomes, entites_allergies, entites_antecedents, 
            entites_medicaments, entites_constantes, entites_patient, 
            entites_examens, entites_contexte, motif_consultation, 
            niveau_severite, symptomes_principaux, allergies_connues, 
            antecedents_medicaux, traitement_en_cours, constantes_vitales, 
            examens_realises
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        # Sécurité : on gère les champs vides pour éviter les erreurs
        def format_list(key):
            lst = entites.get(key, [])
            return ", ".join(lst) if isinstance(lst, list) and lst else None

        valeurs = (
            patient_id,
            doctor_id,
            texte,
            85.0, # Tu peux simuler ou calculer une confiance ici
            format_list('symptomes'),
            format_list('allergies'),
            format_list('antecedents'),
            format_list('medicaments'),
            format_list('constantes'),
            format_list('patient_info'),
            format_list('examens'),
            format_list('contexte'),
            entites.get('motif_consultation'),
            entites.get('severite', 'Faible'),
            format_list('symptomes'), # Pour symptômes principaux
            format_list('allergies') or "Aucune renseignée",
            format_list('antecedents'),
            format_list('medicaments'),
            format_list('constantes'),
            format_list('examens')
        )

        cur.execute(sql, valeurs)
        mysql.connection.commit()
        cur.close()
        print("Enregistrement réussi dans MySQL !")

    except Exception as e:
        print(f"Erreur lors de l'enregistrement DB : {e}")
        # On ne bloque pas le retour de l'IA même si la DB échoue
        erreur = f"Erreur DB: {str(e)}"

    # 4. Retour des données à l'interface
    return jsonify({
        "transcription": texte,
        "entites": entites,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "duree_audio": duree,
        "erreur_nlp": erreur,
    })

@app.route("/get_patient_by_cin/<cin>")
def get_patient_by_cin(cin):
    if 'user_id' not in session:
        return jsonify({"erreur": "Non connecté"}), 401
    
    cur = mysql.connection.cursor()
    # On cherche le patient par son CIN
    cur.execute("SELECT id, first_name, last_name, age, status FROM patients WHERE cin = %s", (cin,))
    patient = cur.fetchone()
    cur.close()

    if patient:
        # On stocke l'ID dans la session pour la route /analyser
        session['current_patient_id'] = patient[0]
        return jsonify({
            "success": True,
            "name": f"{patient[1]} {patient[2]}",
            "age": patient[3],
            "status": patient[4]
        })
    else:
        return jsonify({"success": False, "message": "Patient introuvable. Veuillez l'enregistrer d'abord."})
    

@app.route("/get_consultation_detail/<int:id>")
def get_consultation_detail(id):
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 401
    
    cur = mysql.connection.cursor()
    # On récupère tout le contenu de la consultation + les infos patient
    query = """
        SELECT c.*, p.first_name, p.last_name, p.cin, p.age, p.gender
        FROM consultations c
        JOIN patients p ON c.patient_id = p.id
        WHERE c.id = %s
    """
    cur.execute(query, (id,))
    columns = [col[0] for col in cur.description]
    result = cur.fetchone()
    cur.close()

    if result:
        # Transformation du résultat en dictionnaire pour le JSON
        data = dict(zip(columns, result))
        # Formater la date pour l'affichage
        data['created_at'] = data['created_at'].strftime('%d/%m/%Y à %H:%M')
        return jsonify(data)
    return jsonify({"erreur": "Introuvable"}), 404

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

@app.route("/logout")
def logout():
    # 1. On vide toutes les données de la session
    session.clear() 
    
    # 2. Optionnel : on peut ajouter un petit message de confirmation dans le terminal
    print("Utilisateur déconnecté avec succès.")
    
    # 3. On redirige vers la page de login (ta fonction index)
    return redirect(url_for('login'))

@app.route("/historique")
def historique():
    # Sécurité : vérifier si le médecin est connecté
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        cur = mysql.connection.cursor()
        # On récupère les consultations en joignant la table patients pour avoir les noms
        query = """
            SELECT 
                c.id, 
                p.first_name, 
                p.last_name, 
                c.motif_consultation, 
                c.niveau_severite, 
                c.created_at,
                p.cin
            FROM consultations c
            JOIN patients p ON c.patient_id = p.id
            ORDER BY c.created_at DESC
        """
        cur.execute(query)
        consultations_data = cur.fetchall()
        cur.close()

        return render_template("historique.html", consultations=consultations_data)
    except Exception as e:
        print(f"Erreur historique : {e}")
        return render_template("historique.html", consultations=[])
    

if __name__ == "__main__":
    app.run(debug=True, port=5000)

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    if user_data:
        # Retourne un objet User avec les données de la DB
        from routes.auth import User 
        return User(user_data)
    return None



# --- PAGE LISTE DES PATIENTS ---
# @app.route("/patients")
# # <-- Vérifie bien l'orthographe ici
# def page_patients():
#     # On cherche le fichier dans le dossier 'template' à côté de app.py
#     chemin_fichier = os.path.join(os.getcwd(), "template", "patients.html")
    
#     # Vérification de sécurité pour toi dans le terminal
#     if not os.path.exists(chemin_fichier):
#         print(f"ERREUR : Le fichier est introuvable ici : {chemin_fichier}")
        
#     return send_file(chemin_fichier)
