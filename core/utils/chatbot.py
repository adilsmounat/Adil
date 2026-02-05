import openai
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Lire la clé API
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Clé API OpenAI introuvable. Vérifie ton fichier .env.")

# Associer la clé à la lib
openai.api_key = api_key

def poser_question(question):
    # Détection d'une demande d'exercice
    if any(mot in question.lower() for mot in ["exercice", "donne-moi un exercice", "génère un exercice", "je veux un exercice"]):
        prompt = f"""
Tu es un assistant éducatif pour les élèves de primaire.

Génère un exercice simple et amusant au format JSON.
Le thème est : "{question}".

Réponds uniquement avec un JSON clair, sans texte autour :
{{
  "consigne": "Écris ici une consigne claire pour l'élève.",
  "question": "Écris ici la question ou l'exemple à compléter.",
  "réponse": "Réponse attendue."
}}
"""
    else:
        # Question classique
        prompt = question

    # Envoi au modèle OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Tu es un assistant éducatif pour élèves de primaire."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=400,
    )

    return response['choices'][0]['message']['content']
