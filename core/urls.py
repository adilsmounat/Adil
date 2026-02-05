from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EleveViewSet, AbsenceViewSet, NoteViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .views import index
from django.contrib.auth import logout
from django.shortcuts import redirect
from .views import (
    ajouter_note,
    cours_pour_eleve,
    gerer_notes,
    login_view,
    modifier_note,
    supprimer_note,
)



def custom_logout_view(request):
    logout(request)
    return redirect('login')  

router = DefaultRouter()
router.register(r'eleves', EleveViewSet)
router.register(r'absences', AbsenceViewSet)
router.register(r'notes', NoteViewSet)

urlpatterns = [
  path('', views.redirection_dashboard, name='home'),
  path('api/', include(router.urls)),

    # 🔐 Authentification JWT
  path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
  path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
  path('index/', index, name='index'),
  path('emplois/', views.emplois_du_temps, name='emplois_du_temps'),
  path('eleves/', views.liste_eleves, name='liste_eleves'),
  path('transports/ajouter/', views.ajouter_transport, name='ajouter_transport'),
  path('eleves/ajouter/', views.ajouter_eleve, name='ajouter_eleve'),
  path('eleves/modifier/<int:eleve_id>/', views.modifier_eleve, name='modifier_eleve'),
  path('eleves/supprimer/<int:eleve_id>/', views.supprimer_eleve, name='supprimer_eleve'),
  path('recherche/', views.recherche_eleve, name='recherche_eleve'),
  path('transports/ajax/', views.liste_transport, name='liste_transport'),

  path('enseignants/', views.liste_enseignants, name='liste_enseignants'),
  path('enseignants/ajouter/', views.ajouter_enseignant, name='ajouter_enseignant'),
  path('absences/ajouter/', views.ajouter_absence, name='ajouter_absence'),
  path('absences/', views.liste_absences, name='liste_absences'),
  path('non-autorise/', views.acces_refuse, name='non_autorise'),
  path('absences/modifier/<int:absence_id>/', views.modifier_absence, name='modifier_absence'),
  path('absences/supprimer/<int:absence_id>/', views.supprimer_absence, name='supprimer_absence'),
  path('parents/enfants/', views.liste_enfants, name='liste_enfants'),
  path('mon-enfant/', views.enfant_du_parent, name='enfant_du_parent'),
  path('parents/', views.liste_parents, name='liste_parents'),
  path('parents/enseignants/<int:enseignant_id>/contacter/', views.contacter_enseignant, name='contacter_enseignant'),
  
  path('login/', login_view, name='login'),
  
  path('redirection/', views.redirection_dashboard, name='redirection_dashboard'),

  path('eleve/dashboard/', views.dashboard_eleve, name='dashboard_eleve'),

  
 
  path('logout/', custom_logout_view, name='logout'),
  path('dashboard/parent/', views.dashboard_parent, name='dashboard_parent'),
  #path('enseignant/dashboard/', views.dashboard_enseignant, name='dashboard_enseignant'),
   
  path('enseignant/dashboard/', views.dashboard_enseignant, name='dashboard_enseignant'),
  path('notes/ajouter/', ajouter_note, name='ajouter_note'),
  path('notes/modifier/<int:note_id>/', modifier_note, name='modifier_note'),
  path('notes/supprimer/<int:note_id>/', supprimer_note, name='supprimer_note'),
  path('notes/gerer/', gerer_notes, name='gerer_notes'),
  path('notes/gerer/admin/', views.gerer_notes_admin, name='gerer_notes_admin'),
  path('cours/', views.liste_cours, name='liste_cours'),
  path('cours/ajouter/', views.ajouter_cours, name='ajouter_cours'),
  path('cours/modifier/<int:cours_id>/', views.modifier_cours, name='modifier_cours'),
  path('cours/supprimer/<int:cours_id>/', views.supprimer_cours, name='supprimer_cours'),
  path('eleve/cours/', cours_pour_eleve, name='cours_pour_eleve'),
  path('cours/<int:cours_id>/quiz/', views.afficher_quiz, name='afficher_quiz'),
  path('cours/<int:cours_id>/ajouter-quiz/', views.ajouter_quiz, name='ajouter_quiz'),
  # urls.py
  path('quiz/<int:quiz_id>/', views.detail_quiz, name='detail_quiz'),
  path('eleve/quiz/<int:quiz_id>/', views.passer_quiz, name='passer_quiz'),
  path('eleve/profil/', views.profil_eleve, name='profil_eleve'),
  path('eleve/badges/', views.badges_eleve, name='badges_eleve'),
  path('eleve/stats/', views.stats_eleve, name='stats_eleve'),
  path('notes/', views.notes_eleve, name='notes_eleve'),
  path('enseignant/', views.enseignant_eleve, name='enseignant_eleve'),
  path("chatbot/", views.chatbot_view, name="chatbot"),
  path("chatbot/page/", views.chatbot_page, name="chatbot_page"),
  path('jeu/', views.mini_jeu, name='mini_jeu'),
  path('verifier/', views.verifier_reponse, name='verifier_reponse'),
  path('nouveau-mot/', views.nouveau_mot, name='nouveau_mot'),
  path('jeu-maths/', views.mini_jeu_maths, name='mini_jeu_maths'),
  path('verifier-addition/', views.verifier_addition, name='verifier_addition'),
  path('jeux/', views.selection_jeu, name='selection_jeu'),
  path('jeu-francais/', views.mini_jeu, name='mini_jeu_francais'),
  path('nouvelle-addition/', views.nouvelle_addition, name='nouvelle_addition'),
  path('jeu-probleme/', views.jeu_probleme, name='jeu_probleme'),
  path("api/chatbot/", views.chatbot_api, name="chatbot_api"),
  path('ecole/dashboard/', views.dashboard_admin, name='dashboard_admin'),
  path('paiements/eleves/', views.paiements_eleves, name='paiements_eleves'),
  path('paiements/enseignants/', views.paiements_enseignants, name='paiements_enseignants'),
  path('paiements/', views.gestion_paiement, name='gestion_paiement'),
  path('paiements/eleves/ajouter/', views.ajouter_paiement_eleve, name='ajouter_paiement_eleve'),
  path('paiements/enseignants/ajouter/', views.ajouter_paiement_enseignant, name='ajouter_paiement_enseignant'),

  path('transports/carte/', views.carte_transport, name='localisation_point_depart'),
  path('transport/carte_parent/<int:eleve_id>/', views.carte_transport_parent, name='carte_transport_parent'),
  path('transport/position/<int:eleve_id>/', views.transport_position_parent, name='transport_position_parent'),
  path('transport/position/update/', views.transport_update_position, name='transport_update_position'),
  path('transport/arrive/<int:eleve_id>/', views.notifier_bus_arrive, name='notifier_bus_arrive'),







    






]
