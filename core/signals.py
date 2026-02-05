# core/signals.py

from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from core.models import Profile
from .models import Transport  # ou Bus, ou autre modèle concerné
from .notifications import notifier_parent_par_email

@receiver(post_save, sender=Transport)
def envoyer_email_depart_bus(sender, instance, created, **kwargs):
    if instance.depart:  # supposons un champ booléen ou timestamp
        eleve = instance.eleve
        notifier_parent_par_email(eleve)

@receiver(post_migrate)
def creer_groupes(sender, **kwargs):
    noms_groupes = ['Enseignants', 'Administration', 'Parents', 'Élèves']
    for nom in noms_groupes:
        Group.objects.get_or_create(name=nom)



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Si un profil existe déjà, ne rien faire
        if hasattr(instance, 'profile'):
            return

        role = 'eleve'  # Par défaut

        # Exemple de logique personnalisée
        if instance.is_superuser:
            role = 'admin'
        elif hasattr(instance, 'enseignant'):
            role = 'enseignant'
        elif hasattr(instance, 'parent'):
            role = 'parent'
        # tu peux aussi tester par username, email, groupe, etc.

        Profile.objects.create(user=instance, role=role)
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance, role='eleve')  # ou un autre rôle par défaut
