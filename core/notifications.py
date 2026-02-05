import logging
import os

from django.core.mail import send_mail

from core.models import Parent, Notification  # Assure-toi que le modèle Parent est bien importé

logger = logging.getLogger(__name__)

def notifier_parent_par_sms(eleve):
    # Récupérer l’objet Parent via l'user lié
    parent = Parent.objects.filter(user=eleve.parent_user).first()
    if not parent:
        logger.warning("Aucun parent trouvé pour l'élève id=%s.", eleve.id)
        return False

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not account_sid or not auth_token or not from_number:
        logger.warning("Twilio non configure (variables d'environnement manquantes).")
        return False
    try:
        from twilio.rest import Client
    except Exception:  # ImportError or runtime issue with twilio
        logger.warning("Twilio n'est pas installé, SMS ignoré.")
        return False

    client = Client(account_sid, auth_token)

    client.messages.create(
        body=f"🚍 Le bus approche de l'arrêt de {eleve.prenom}.",
        from_=from_number,
        to=parent.telephone      # Numéro du parent depuis le modèle Parent
    )
    return True

def notifier_parent_par_email(eleve):
    parent = Parent.objects.filter(user=eleve.parent_user).first()
    if not parent:
        logger.warning("Aucun parent trouvé pour l'élève id=%s.", eleve.id)
        return False

    email = parent.email

    if not email:
        print("❌ Aucun email pour ce parent.")
        return False

    subject = "🚌 Notification Transport Scolaire"
    message = f"Bonjour {parent.nom},\n\nLe bus approche de l'arrêt de {eleve.prenom}."
    
    send_mail(
        subject,
        message,
        'smounat88@gmail.com',  # from_email dans settings.py
        [email],
        fail_silently=False,
    )
    return True


def notifier_parent_par_app(eleve):
    parent = Parent.objects.filter(user=eleve.parent_user).first()
    if not parent:
        logger.warning("Aucun parent trouvé pour l'élève id=%s.", eleve.id)
        return False

    Notification.objects.create(
        user=parent.user,
        eleve=eleve,
        titre="🚌 Transport arrivé",
        message=f"Le transport est arrivé chez {eleve.prenom} {eleve.nom}.",
    )
    return True
