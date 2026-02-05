from django.core.mail import send_mail
from django.conf import settings


def envoyer_notification_paiement(eleve, montant, mois):
    print(f"[DEBUG] Envoi mail pour {eleve.nom} à {eleve.email_parent}")

    if eleve.email_parent:
        send_mail(
            subject="📩 Confirmation de paiement scolaire",
            message=f"Bonjour, le paiement de {montant}€ pour le mois de {mois} a été enregistré pour {eleve.nom}.",
            from_email="smounat88@gmail.com",
            recipient_list=[eleve.email_parent],
            fail_silently=False  # Important pour voir les erreurs
        )

