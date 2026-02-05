import csv
import json
import logging
import traceback
from random import choice, randint

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from .decorators import allow_iframe
from .forms import (
    AbsenceForm,
    CoursForm,
    EleveForm,
    EnseignantForm,
    NoteForm,
    PaiementEleveForm,
    PaiementEnseignantForm,
    TransportForm,
    ContactEnseignantForm,
)
from .models import (
    Absence,
    Badge,
    Cours,
    Eleve,
    EmploiDuTemps,
    Enseignant,
    Note,
    Notification,
    PaiementEleve,
    PaiementEnseignant,
    Parent,
    Probleme,
    Profile,
    Question,
    Quiz,
    SoumissionQuiz,
    Transport,
)
from .notifications import notifier_parent_par_sms, notifier_parent_par_email, notifier_parent_par_app
from .permissions import is_admin
from .send import envoyer_notification_paiement
from .serializers import AbsenceSerializer, EleveSerializer, NoteSerializer
from .utils.chatbot import poser_question
logger = logging.getLogger(__name__)
def analyse_apprentissage(eleve):
    # Moyenne des notes
    moyenne_notes = (
        Note.objects.filter(eleve=eleve).aggregate(Avg('note'))['note__avg'] or 0
    )

    # Score moyen aux quiz
    moyenne_quiz = (
        SoumissionQuiz.objects.filter(eleve=eleve).aggregate(Avg('score'))['score__avg'] or 0
    )

    # Absences
    nb_absences = Absence.objects.filter(eleve=eleve).count()

    # Badges
    nb_badges = Badge.objects.filter(eleve=eleve).count()

    recommandations = []

    if moyenne_notes < 10:
        recommandations.append("📚 Tu devrais revoir les cours où tu as eu des notes faibles.")
    else:
        recommandations.append("✅ Tes notes sont bonnes, continue comme ça !")

    if moyenne_quiz < 5:
        recommandations.append("🧩 Entraîne-toi sur les quiz pour améliorer ton score.")
    else:
        recommandations.append("🏅 Tes résultats aux quiz sont encourageants.")

    if nb_absences > 3:
        recommandations.append("⏰ Essaie de réduire tes absences pour mieux progresser.")

    if nb_badges == 0:
        recommandations.append("🎯 Commence par terminer un jeu ou un quiz pour gagner ton premier badge.")
    elif nb_badges < 3:
        recommandations.append("✨ Tu as déjà des badges, essaie d’en débloquer encore plus !")

    return {
        "statistiques": {
            "moyenne_notes": round(moyenne_notes, 2),
            "moyenne_quiz": round(moyenne_quiz, 2),
            "absences": nb_absences,
            "badges_total": nb_badges,
        },
        "recommandations": recommandations,
    }


@login_required
@user_passes_test(is_admin)
def ajouter_transport(request):
    if request.method == 'POST':
        form = TransportForm(request.POST)
        if form.is_valid():
            transport = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'id': transport.id})
            messages.success(request, "Transport ajouté avec succès.")
            return redirect('liste_transport')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = TransportForm()
    return render(request, 'transports/ajouter.html', {'form': form})

def liste_transport(request):
    transports = Transport.objects.select_related('eleve').all()
    form = TransportForm()
    return render(request, 'transports/liste_ajax.html', {
        'transports': transports,
        'form': form
    })

def recherche_eleve(request):
    query = request.GET.get('q')
    eleve = None
    notes = absences = transports = []

    if query:
        eleve = get_object_or_404(Eleve, nom__icontains=query)
        notes = Note.objects.filter(eleve=eleve)
        absences = Absence.objects.filter(eleve=eleve)
        transports = Transport.objects.filter(eleve=eleve)

    context = {
        'eleve': eleve,
        'notes': notes,
        'absences': absences,
        'transports': transports,
    }
    return render(request, 'recherche_eleve.html', context)



@login_required
def emplois_du_temps(request):
    emplois = EmploiDuTemps.objects.all()
    return render(request, 'emploi_du_temps.html', {'emplois': emplois})


def is_eleves(user):
    return user.groups.filter(name='eleves').exists()
@login_required
def liste_eleves(request):
    nom = request.GET.get('nom', '')
    classe = request.GET.get('classe', '')

    eleves = Eleve.objects.all()

    if nom:
        eleves = eleves.filter(nom__icontains=nom)

    if classe:
        eleves = eleves.filter(classe__iexact=classe)

    donnees_eleves = []
    for eleve in eleves:
        notes = Note.objects.filter(eleve=eleve)
        absences = Absence.objects.filter(eleve=eleve)
        transport = Transport.objects.filter(eleve=eleve).first()
        parent = Parent.objects.filter(eleve=eleve).first()
        enseignants = eleve.enseignants.all()

        donnees_eleves.append({
            'eleve': eleve,
            'notes': notes,
            'absences': absences,
            'transport': transport,
            'parent': parent,
            'enseignants': enseignants,
        })

    # Récupérer toutes les classes distinctes (en tant que texte)
    classes = Eleve.objects.values_list('classe', flat=True).distinct()

    return render(request, 'liste_eleves.html', {
        'donnees_eleves': donnees_eleves,
        'classes': classes,
    })



   

  


def ajouter_eleve(request):
    if request.method == 'POST':
        form = EleveForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('liste_eleves')  # ou une autre URL
    else:
        form = EleveForm()
    return render(request, 'ajouter_eleve.html', {'form': form})

def modifier_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    if request.method == 'POST':
        form = EleveForm(request.POST, instance=eleve)
        if form.is_valid():
            form.save()
            return redirect('liste_eleves')  # Redirige vers la liste après modification
    else:
        form = EleveForm(instance=eleve)
    
    return render(request, 'modifier_eleve.html', {'form': form, 'eleve': eleve})
def supprimer_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    eleve.delete()
    messages.success(request, "L'élève a été supprimé avec succès.")
    return redirect('liste_eleves')
@login_required
def tableau_de_bord(request):
    context = {
        'nb_eleves': Eleve.objects.count(),
        'nb_notes': Note.objects.count(),
        'nb_absences': Absence.objects.count(),
        'nb_transports': Transport.objects.count(),
    }
    return render(request, 'tableau_de_bord.html', context)

class EleveViewSet(viewsets.ModelViewSet):
    queryset = Eleve.objects.all()
    serializer_class = EleveSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile'):
            if user.profile.role == 'parent':
                return Eleve.objects.filter(parent_user=user)
            elif user.profile.role == 'enseignant':
                return Eleve.objects.filter(enseignants__user=user)
        return Eleve.objects.none()  # aucun résultat pour les autres


class AbsenceViewSet(viewsets.ModelViewSet):
    queryset = Absence.objects.all()
    serializer_class = AbsenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['eleve', 'justifiee', 'date']
    
class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]
@login_required(login_url='login')
def index(request):
    return render(request, 'index.html')
@login_required
def liste_enseignants(request):
    enseignants = Enseignant.objects.all()
    return render(request, 'enseignants/liste_enseignants.html', {'enseignants': enseignants})



def ajouter_enseignant(request):
    if request.method == 'POST':
        form = EnseignantForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')

            # Vérifie si le nom d'user existe déjà
            if User.objects.filter(username=username).exists():
                messages.error(request, "Ce nom d'user existe déjà. Veuillez en choisir un autre.")
            else:
                form.save()
                return redirect('liste_enseignants')
    else:
        form = EnseignantForm()
    
    return render(request, 'enseignants/ajouter_enseignant.html', {'form': form})
def non_autorise(request):
    return render(request, 'non_autorise.html')


def ajouter_absence(request):
    if request.method == 'POST':
        form = AbsenceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('liste_absences')  # assure-toi que cette route existe
    else:
        form = AbsenceForm()
    
    return render(request, 'absences/ajouter_absence.html', {'form': form})

@login_required
def liste_absences(request):
    user = request.user

    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return render(request, 'non_autorise.html')

    if profile.role == 'eleve':
        try:
            eleve = Eleve.objects.get(user=user)
            absences = Absence.objects.filter(eleve=eleve)
            return render(request, 'absences/readonly_view.html', {'absences': absences})
        except Eleve.DoesNotExist:
            return render(request, 'non_autorise.html')

    elif profile.role in ['enseignant', 'admin']:
        if profile.role == 'enseignant':
            eleves = Eleve.objects.filter(enseignants__user=request.user)
            absences = Absence.objects.filter(eleve__in=eleves).select_related('eleve')
        else:
            eleves = Eleve.objects.all()
            absences = Absence.objects.all().select_related('eleve')

        eleve_id = request.GET.get('eleve', '').strip()
        justifiee = request.GET.get('justifiee', '').strip()

        if eleve_id:
            absences = absences.filter(eleve_id=eleve_id)
        if justifiee == 'true':
            absences = absences.filter(justifiee=True)
        elif justifiee == 'false':
            absences = absences.filter(justifiee=False)

        total = absences.count()
        justifiees = absences.filter(justifiee=True).count()
        non_justifiees = absences.filter(justifiee=False).count()

        return render(request, 'absences/liste_absences.html', {
            'absences': absences,
            'eleves': eleves,
            'total': total,
            'justifiees': justifiees,
            'non_justifiees': non_justifiees,
        })

    return render(request, 'non_autorise.html')




def modifier_absence(request, absence_id):
    absence = get_object_or_404(Absence, pk=absence_id)
    form = AbsenceForm(request.POST or None, instance=absence)
    if form.is_valid():
        form.save()
        messages.success(request, "L'absence a été modifiée avec succès.")
        return redirect('liste_absences')
    return render(request, 'absences/modifier_absence.html', {'form': form})

@login_required

def supprimer_absence(request, absence_id):
    absence = get_object_or_404(Absence, pk=absence_id)
    if request.method == 'POST':
        absence.delete()
        messages.success(request, "L'absence a été supprimée avec succès.")
        return redirect('liste_absences')
    return render(request, 'absences/confirm_suppression.html', {'absence': absence})
def acces_refuse(request):
    return render(request, 'non_autorise.html')

@login_required
def liste_enfants(request):
    enfants = Eleve.objects.filter(parent_user=request.user).select_related('transport').prefetch_related('enseignants')

    return render(request, 'parents/liste_enfants.html', {'enfants': enfants})

@login_required
def enfant_du_parent(request):
    eleve = None
    parent = Parent.objects.filter(user=request.user).first()
    if parent and parent.eleve:
        eleve = parent.eleve
    else:
        eleve = Eleve.objects.filter(parent_user=request.user).first()

    return render(request, 'parents/enfants.html', {'eleve': eleve})
@login_required
def dashboard_eleve(request):
    user = request.user

    # Récupérer l'élève connecté
    try:
        eleve = Eleve.objects.get(user=user)
    except Eleve.DoesNotExist:
        return render(request, 'non_autorise.html')

    # 🔄 Maintenant que 'eleve' est défini, on peut récupérer les badges
    badges = Badge.objects.filter(eleve=eleve)

    # Notes de l’élève
    notes = Note.objects.filter(eleve=eleve)

    # Absences de l’élève
    absences = Absence.objects.filter(eleve=eleve)

    # Transport
    transport = getattr(eleve, 'transport', None)

    # Enseignants
    enseignants = eleve.enseignants.all()
    
    analyse = analyse_apprentissage(eleve)
    recommandations = analyse['recommandations']
    stats = analyse['statistiques']

    context = {
        'eleve': eleve,
        'notes': notes,
        'absences': absences,
        'transport': transport,
        'enseignants': enseignants,
        'badges': badges,
        'user_fullname': f"{request.user.first_name} {request.user.last_name}",
        'recommandations': analyse['recommandations'],
        'stats_apprentissage': analyse['statistiques'],
    }


    return render(request, 'dashboards/dashboard_eleve.html', context)
def redirection_dashboard(request):
    if request.user.is_authenticated:
        try:
            profil = Profile.objects.get(user=request.user)
            role = profil.role

            if role == 'parent':
                return redirect('dashboard_parent')
            elif role == 'enseignant':
                return redirect('dashboard_enseignant')
            elif role == 'eleve':
                return redirect('dashboard_eleve')
            elif role == 'admin':
                return redirect('dashboard_admin')
            else:
                print("❌ Rôle inconnu :", role)
                return redirect('login')  # ou afficher une page d’erreur

        except Profile.DoesNotExist:
            print("❌ Aucun profil trouvé pour l'user :", request.user.username)
            return redirect('login')

    print("❌ Utilisateur non authentifié")
    return redirect('login')

@login_required
def dashboard_parent(request):
    user = request.user

    try:
        profile = Profile.objects.get(user=user)
        if profile.role != 'parent':
            return redirect('index')  # Redirige si l'user n'est pas un parent
    except Profile.DoesNotExist:
        return redirect('index')

    # Récupérer les enfants liés à ce parent
    enfants = Eleve.objects.filter(parent_user=user).select_related('transport').prefetch_related('notes', 'absences', 'enseignants')


    notifications = []
    if user.is_authenticated:
        notifications = user.notifications.order_by('-created_at')[:10]

    return render(request, 'dashboards/dashboard_parent.html', {
        'parent': profile,
        'enfants': enfants,
        'notifications': notifications,
    })

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            try:
                profile = Profile.objects.get(user=user)
                role = profile.role
                print("✅ Rôle détecté :", role)

                if role == 'eleve':
                    return redirect('dashboard_eleve')
                elif role == 'parent':
                    return redirect('dashboard_parent')
                elif role == 'enseignant':
                    return redirect('dashboard_enseignant')
                elif role == 'admin':
                    return redirect('dashboard_admin')
                else:
                    print("❌ Rôle inconnu :", role)
                    messages.warning(request, "Rôle inconnu.")
                    return redirect('login')

            except Profile.DoesNotExist:
                messages.warning(request, "Profil user introuvable.")
                return redirect('login')

        else:
            messages.error(request, "Nom d’user ou mot de passe incorrect.")
            return render(request, 'base_auth.html')

    return render(request, 'base_auth.html')
@login_required(login_url='login')
def dashboard_enseignant(request):
    user = request.user
   

    try:
        profile = Profile.objects.get(user=user)


        if profile.role != 'enseignant':
            print("⛔ Mauvais rôle :", profile.role)
            return redirect('index')
    except Profile.DoesNotExist:
        print("❌ Aucun profil")
        return redirect('index')

    try:
        enseignant = Enseignant.objects.get(user=user)
    except Enseignant.DoesNotExist:
        print("❌ Aucun objet Enseignant pour :", user)
        return redirect('index')

    eleves = (
        Eleve.objects.filter(enseignants=enseignant)
        .prefetch_related('notes', 'absences')
    )
    notes = Note.objects.filter(enseignant=enseignant).select_related('eleve')
    absences = Absence.objects.filter(eleve__in=eleves).select_related('eleve')
    cours = Cours.objects.filter(enseignant=enseignant).prefetch_related('quizz')

    quiz = Quiz.objects.filter(cours__in=cours)

    today = timezone.localdate()
    stats = {
        'total_eleves': eleves.count(),
        'total_notes': notes.count(),
        'total_absences': absences.count(),
        'avg_notes': notes.aggregate(avg=Avg('note'))['avg'] or 0,
        'absences_7j': absences.filter(date__gte=today - timedelta(days=7)).count(),
        'total_cours': cours.count(),
        'total_quiz': quiz.count(),
    }
    eleves_par_classe = (
        eleves.values('classe').annotate(total=Count('id')).order_by('classe')
    )
    notes_recentes = notes.order_by('-date')[:6]
    absences_recentes = absences.order_by('-date')[:6]
    cours_stats = cours.annotate(quiz_count=Count('quizz')).order_by('nom')

    notes_par_matiere = (
        notes.values('matiere')
        .annotate(moyenne=Avg('note'), total=Count('id'))
        .order_by('matiere')
    )
    absences_par_jour = (
        absences.filter(date__gte=today - timedelta(days=7))
        .values('date')
        .annotate(total=Count('id'))
        .order_by('date')
    )
    chart_notes_labels = [n['matiere'] or '—' for n in notes_par_matiere]
    chart_notes_values = [float(n['moyenne'] or 0) for n in notes_par_matiere]
    chart_absences_labels = [a['date'].strftime('%d/%m') for a in absences_par_jour]
    chart_absences_values = [a['total'] for a in absences_par_jour]
    chart_classes_labels = [c['classe'] or '—' for c in eleves_par_classe]
    chart_classes_values = [c['total'] for c in eleves_par_classe]

   

    return render(request, 'dashboards/dashboard_enseignant.html', {
        'enseignant': enseignant,
        'profile': profile,
        'eleves': eleves,
        'notes': notes,
        'absences': absences,
        'cours': cours_stats,
        'stats': stats,
        'eleves_par_classe': eleves_par_classe,
        'notes_recentes': notes_recentes,
        'absences_recentes': absences_recentes,
        'chart_notes_labels': json.dumps(chart_notes_labels),
        'chart_notes_values': json.dumps(chart_notes_values),
        'chart_absences_labels': json.dumps(chart_absences_labels),
        'chart_absences_values': json.dumps(chart_absences_values),
        'chart_classes_labels': json.dumps(chart_classes_labels),
        'chart_classes_values': json.dumps(chart_classes_values),
        
    })



@login_required(login_url='login')
def modifier_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, enseignant__user=request.user)
    form = NoteForm(request.POST or None, instance=note)
    if form.is_valid():
        form.save()
        return redirect('dashboard_enseignant')
    return render(request, 'notes/modifier_note.html', {'form': form})


@login_required(login_url='login')
def supprimer_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, enseignant__user=request.user)
    if request.method == 'POST':
        note.delete()
        return redirect('dashboard_enseignant')
    return render(request, 'notes/supprimer_note.html', {'note': note})

@login_required(login_url='login')  # 👈 vérifie que le nom de ton url de login est bien 'login'
def gerer_notes(request):
    try:
        enseignant = Enseignant.objects.get(user=request.user)
    except Enseignant.DoesNotExist:
        return redirect('index')  # 👈 redirige si l'user connecté n'est pas un enseignant

    notes = Note.objects.filter(enseignant=enseignant).select_related('eleve')

    q = request.GET.get('q', '').strip()
    classe = request.GET.get('classe', '').strip()
    matiere = request.GET.get('matiere', '').strip()
    min_note = request.GET.get('min_note', '').strip()
    max_note = request.GET.get('max_note', '').strip()
    date_debut = request.GET.get('date_debut', '').strip()
    date_fin = request.GET.get('date_fin', '').strip()

    if q:
        notes = notes.filter(Q(eleve__nom__icontains=q) | Q(eleve__prenom__icontains=q))
    if classe:
        notes = notes.filter(eleve__classe__iexact=classe)
    if matiere:
        notes = notes.filter(matiere__icontains=matiere)
    if min_note:
        notes = notes.filter(note__gte=min_note)
    if max_note:
        notes = notes.filter(note__lte=max_note)
    if date_debut:
        notes = notes.filter(date__gte=date_debut)
    if date_fin:
        notes = notes.filter(date__lte=date_fin)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="notes_enseignant.csv"'
        writer = csv.writer(response)
        writer.writerow(['Eleve', 'Classe', 'Matiere', 'Note', 'Date'])
        for n in notes.order_by('-date'):
            writer.writerow([f"{n.eleve.nom} {n.eleve.prenom}", n.eleve.classe, n.matiere, n.note, n.date])
        return response

    if request.method == 'POST' and request.POST.get('quick_add') == '1':
        eleve_id = request.POST.get('eleve')
        matiere = request.POST.get('matiere', '').strip()
        note_val = request.POST.get('note', '').strip()
        date_val = request.POST.get('date', '').strip()

        if not (eleve_id and matiere and note_val):
            messages.error(request, "Merci de remplir l'élève, la matière et la note.")
        else:
            eleve = get_object_or_404(Eleve, id=eleve_id, enseignants=enseignant)
            Note.objects.create(
                eleve=eleve,
                enseignant=enseignant,
                matiere=matiere,
                note=note_val,
                date=date_val or timezone.localdate(),
            )
            messages.success(request, "Note ajoutée avec succès.")
        return redirect('gerer_notes')

    classes = Eleve.objects.filter(enseignants=enseignant).values_list('classe', flat=True).distinct()
    matieres = Note.objects.filter(enseignant=enseignant).values_list('matiere', flat=True).distinct()
    eleves = Eleve.objects.filter(enseignants=enseignant).order_by('nom', 'prenom')

    return render(request, 'notes/gerer_notes.html', {
        'enseignant': enseignant,
        'notes': notes,
        'classes': classes,
        'matieres': matieres,
        'eleves': eleves,
    }
    )
   
@login_required(login_url='login')
def ajouter_note(request):
    user = request.user

    try:
        profile = Profile.objects.get(user=user)
        if profile.role != 'enseignant':
            return redirect('index')
    except Profile.DoesNotExist:
        return redirect('index')

    try:
        enseignant = Enseignant.objects.get(user=user)
    except Enseignant.DoesNotExist:
        return redirect('index')

    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.enseignant = enseignant  # Lier automatiquement à l'enseignant connecté
            note.save()
            return redirect('dashboard_enseignant')
    else:
        # Limiter le choix des élèves à ceux de cet enseignant
        form = NoteForm()
        form.fields['eleve'].queryset = Eleve.objects.filter(enseignants=enseignant)

    return render(request, 'notes/ajouter_note.html', {'form': form})
# views.py




@login_required
def liste_cours(request):
    enseignant = get_object_or_404(Enseignant, user=request.user)
    cours = (
        Cours.objects.filter(enseignant=enseignant)
        .annotate(quiz_count=Count('quizz'))
        .prefetch_related('quizz')
    )
    return render(request, 'cours/liste_cours.html', {'cours': cours})


@login_required
def ajouter_cours(request):
    enseignant = get_object_or_404(Enseignant, user=request.user)
    form = CoursForm(request.POST or None, request.FILES or None)  # <-- important !
    if form.is_valid():
        nouveau_cours = form.save(commit=False)
        nouveau_cours.enseignant = enseignant
        nouveau_cours.save()
        return redirect('liste_cours')
    return render(request, 'cours/ajouter_cours.html', {'form': form})


@login_required
def modifier_cours(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id, enseignant__user=request.user)
    form = CoursForm(request.POST or None, instance=cours)
    if form.is_valid():
        form.save()
        return redirect('liste_cours')
    return render(request, 'cours/modifier_cours.html', {'form': form})


@login_required
def supprimer_cours(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id, enseignant__user=request.user)
    if request.method == 'POST':
        cours.delete()
        return redirect('liste_cours')
    return render(request, 'cours/supprimer_cours.html', {'cours': cours})
@login_required
def cours_pour_eleve(request):
    eleve = get_object_or_404(Eleve, user=request.user)
    cours = Cours.objects.filter(classe=eleve.classe).prefetch_related('quizz')
    soumissions = SoumissionQuiz.objects.filter(eleve=eleve)
    quiz_faits = {soumission.quiz.id: soumission for soumission in soumissions}
    badges = Badge.objects.filter(eleve=eleve)
    return render(request, 'cours/cours_classe.html', {
        'cours': cours,
        'eleve': eleve,
        'quiz_faits': quiz_faits,
        'badges': badges,
    })

def afficher_quiz(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    quiz = Quiz.objects.filter(cours=cours)
    return render(request, 'quiz/afficher_quiz.html', {'cours': cours, 'quiz': quiz})



@login_required
def ajouter_quiz(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id, enseignant__user=request.user)

    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        description = request.POST.get('description', '').strip()
        question_texte = request.POST.get('question', '').strip()
        choix_1 = request.POST.get('choix_1', '').strip()
        choix_2 = request.POST.get('choix_2', '').strip()
        choix_3 = request.POST.get('choix_3', '').strip()
        bonne_reponse = request.POST.get('bonne_reponse', '').strip()

        if not all([titre, question_texte, choix_1, choix_2, choix_3, bonne_reponse]):
            messages.error(request, "Merci de remplir tous les champs du quiz.")
            return render(request, 'quiz/ajouter_quiz.html', {'cours': cours})

        quiz = Quiz.objects.create(
            cours=cours,
            titre=titre,
            description=description,
        )
        Question.objects.create(
            quiz=quiz,
            texte=question_texte,
            choix_1=choix_1,
            choix_2=choix_2,
            choix_3=choix_3,
            bonne_reponse=bonne_reponse,
        )

        return redirect('liste_cours')  # Redirection après ajout

    return render(request, 'quiz/ajouter_quiz.html', {'cours': cours})

@login_required
def detail_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    return render(request, 'quiz/detail_quiz.html', {'quiz': quiz})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import Quiz, SoumissionQuiz, Badge, Eleve  # Ajoute tous les modèles nécessaires

@login_required
def passer_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    total_questions = questions.count()
    score = 0
    reponses_corrigees = []

    # Récupération de l'élève connecté
    eleve = get_object_or_404(Eleve, user=request.user)

    if request.method == 'POST':
        for question in questions:
            reponse = request.POST.get(f'q{question.id}')
            est_correcte = (reponse == question.bonne_reponse)
            if est_correcte:
                score += 1

            reponses_corrigees.append({
                'question': question,
                'reponse_donnee': reponse,
                'bonne_reponse': question.bonne_reponse,
                'est_correcte': est_correcte
            })

        # Enregistrer la soumission du quiz
        SoumissionQuiz.objects.create(
            eleve=eleve,
            quiz=quiz,
            score=score
        )

        # Vérifier si l'élève a terminé tous les quiz du cours
        total_quiz = quiz.cours.quizz.count()
        quiz_faits = SoumissionQuiz.objects.filter(eleve=eleve, quiz__cours=quiz.cours).count()

        if quiz_faits == total_quiz:
            Badge.objects.get_or_create(
                eleve=eleve,
                cours=quiz.cours,
                defaults={'titre': f'Badge - {quiz.cours.nom}'}
            )

        return render(request, 'quiz/resultat_quiz.html', {
            'score': score,
            'total': total_questions,
            'reponses_corrigees': reponses_corrigees
        })

    return render(request, 'quiz/passer_quiz.html', {
        'quiz': quiz,
        'questions': questions
    })
@login_required
def profil_eleve(request):
    eleve = get_object_or_404(Eleve, user=request.user)
    return render(request, 'eleve/profil.html', {'eleve': eleve})
@login_required
def badges_eleve(request):
    eleve = get_object_or_404(Eleve, user=request.user)
    badges = Badge.objects.filter(eleve=eleve)
    return render(request, 'eleve/badges.html', {'badges': badges})
@login_required
def stats_eleve(request):
    eleve = get_object_or_404(Eleve, user=request.user)
    # Ajoute ici ta logique de statistiques, par exemple :
    quiz_scores = SoumissionQuiz.objects.filter(eleve=eleve)
    return render(request, 'eleve/stats.html', {
        'eleve': eleve,
        'quiz_scores': quiz_scores
    })
@login_required
def notes_eleve(request):
    try:
        eleve = Eleve.objects.get(user=request.user)
    except Eleve.DoesNotExist:
        return render(request, 'non_autorise.html')

    notes = Note.objects.filter(eleve=eleve)

    return render(request, 'eleve/notes.html', {
        'notes': notes,
        'eleve': eleve
    })
@login_required
def enseignant_eleve(request):
    eleve = get_object_or_404(Eleve, user=request.user)
    enseignants = eleve.enseignants.all()
    return render(request, 'eleve/enseignant.html', {'eleve': eleve, 'enseignants': enseignants})

@login_required
def contacter_enseignant(request, enseignant_id):
    user = request.user
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return render(request, 'non_autorise.html')

    if profile.role != 'parent':
        return render(request, 'non_autorise.html')

    enseignant = get_object_or_404(Enseignant, id=enseignant_id)
    eleve_id = request.GET.get('eleve_id')
    eleve = None
    if eleve_id:
        eleve = Eleve.objects.filter(id=eleve_id, parent_user=user).first()

    if not enseignant.user.email:
        messages.error(request, "Cet enseignant n'a pas d'email enregistré.")
        return redirect('dashboard_parent')

    if request.method == 'POST':
        form = ContactEnseignantForm(request.POST)
        if form.is_valid():
            sujet = form.cleaned_data['sujet']
            message = form.cleaned_data['message']
            email_parent = form.cleaned_data['email_parent'] or user.email or ""

            contexte_eleve = (
                f"\\n\\nÉlève concerné : {eleve.prenom} {eleve.nom} ({eleve.classe})"
                if eleve else ""
            )
            corps = (
                f"Message de parent : {user.get_full_name() or user.username}\\n"
                f"Email parent : {email_parent or 'non renseigné'}\\n"
                f"{contexte_eleve}\\n\\n"
                f"{message}"
            )

            send_mail(
                subject=sujet,
                message=corps,
                from_email=None,
                recipient_list=[enseignant.user.email],
                reply_to=[email_parent] if email_parent else None,
                fail_silently=False,
            )

            messages.success(request, "Message envoyé à l'enseignant.")
            return redirect('dashboard_parent')
    else:
        form = ContactEnseignantForm()

    return render(request, 'parents/contact_enseignant.html', {
        'form': form,
        'enseignant': enseignant,
        'eleve': eleve,
    })


@allow_iframe
def chatbot_view(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        question = request.POST.get('question')

        try:
            reponse = poser_question(question)
        except Exception as e:
            print("⚠️ Erreur OpenAI :", traceback.format_exc())
            return JsonResponse({'reponse': "Désolé, une erreur est survenue avec l'assistant. Réessaie plus tard."})

        # Stocker dans la session
        if 'conversation' not in request.session:
            request.session['conversation'] = []

        request.session['conversation'].append({'role': 'user', 'text': question})
        request.session['conversation'].append({'role': 'bot', 'text': reponse})
        request.session.modified = True

        return JsonResponse({'reponse': reponse})

    # 💥 Gérer le reset de conversation
    if request.GET.get('reset') == '1':
        request.session['conversation'] = []
        request.session.modified = True
        return JsonResponse({'status': 'reset'})

    return render(request, 'chatbot.html', {
        'welcome': "Bonjour 👋 ! Je suis ton assistant éducatif. Pose-moi ta question.",
    })

def chatbot_page(request):
    reponse = ""
    if request.method == "POST":
        question = request.POST.get("question")
        reponse = poser_question(question)
    return render(request, "chatbot_page.html", {"reponse": reponse})
MOTS = [
    {'mot': 'chanter', 'indice': 'Verbe du 1er groupe'},
    {'mot': 'école', 'indice': 'Lieu d’apprentissage'},
    {'mot': 'manger', 'indice': 'Action avec la bouche'},
    {'mot': 'livre', 'indice': 'Contient des pages à lire'},
]
@allow_iframe


def mini_jeu(request):
    if request.user.is_authenticated and not request.session.get('score_reset'):
        request.session['score'] = 0
        request.session['score_reset'] = True
    
    mot = choice(MOTS)
    request.session['mot_jeu'] = mot['mot']
    request.session['indice'] = mot['indice']

    if 'score' not in request.session:
        request.session['score'] = 0

    score = request.session['score']
    badge_gagne = False  # <- nouveau flag

    if score >= 5 and request.user.is_authenticated:
        try:
            eleve = Eleve.objects.get(user=request.user)
            cours = Cours.objects.filter(classe=eleve.classe).first()

            badge_existe = Badge.objects.filter(
                eleve=eleve,
                cours=cours,
                titre="Chasseur de mots"
            ).exists()

            if not badge_existe:
                Badge.objects.create(
                    eleve=eleve,
                    cours=cours,
                    titre="Chasseur de mots"
                )
                badge_gagne = True  # <- déclenche la notification

        except Eleve.DoesNotExist:
            pass

    return render(request, 'mini_jeu.html', {
        'mot': mot,
        'score': score,
        'badge_gagne': badge_gagne  # <- on passe ce flag au template
    })



  

def verifier_reponse(request):
    user_answer = request.POST.get('reponse', '').strip().lower()
    mot_attendu = request.session.get('mot_jeu', '').lower()
    correct = user_answer == mot_attendu

    if correct:
        request.session['score'] += 1
        message = "✅ Bravo ! Bonne réponse."
    else:
        message = f"❌ Mauvaise réponse. C'était : {mot_attendu}"

    return JsonResponse({'correct': correct, 'message': message, 'score': request.session['score']})

def nouveau_mot(request):
    mot = choice(MOTS)
    request.session['mot_jeu'] = mot['mot']
    request.session['indice'] = mot['indice']
    return JsonResponse({
        'indice': mot['indice'],
        'message': "🔄 Nouveau mot généré !"
    })


def mini_jeu_maths(request):
    if 'score_maths' not in request.session:
        request.session['score_maths'] = 0

    # Création de la première addition
    if 'addition' not in request.session:
        a, b = randint(1, 10), randint(1, 10)
        request.session['addition'] = [a, b]

    score = request.session['score_maths']
    badge_gagne = False
    badges = []

    if request.user.is_authenticated:
        try:
            eleve = Eleve.objects.get(user=request.user)
            cours = Cours.objects.filter(classe=eleve.classe).first()
            badges = Badge.objects.filter(eleve=eleve)

            # Attribution du badge si score atteint
            if score >= 5:
                titre_badge = "Math Master"
                badge_existe = Badge.objects.filter(
                    eleve=eleve,
                    cours=cours,
                    titre=titre_badge
                ).exists()

                if not badge_existe:
                    Badge.objects.create(
                        eleve=eleve,
                        cours=cours,
                        titre=titre_badge
                    )
                    badge_gagne = True
        except Eleve.DoesNotExist:
            pass

    return render(request, 'mini_jeu_maths.html', {
        'a': request.session['addition'][0],
        'b': request.session['addition'][1],
        'score': score,
        'badge_gagne': badge_gagne,
        'badges': badges
    })


def verifier_addition(request):
   
    reponse = int(request.POST.get('reponse', 0))
    a, b = request.session.get('addition', [0, 0])
    resultat = a + b

    correct = reponse == resultat
    if correct:
        request.session['score_maths'] += 1

    # Générer une nouvelle addition à chaque soumission
    a_nouveau, b_nouveau = randint(1, 10), randint(1, 10)
    request.session['addition'] = [a_nouveau, b_nouveau]

    return JsonResponse({
        'correct': correct,
        'message': "✔️ Bravo !" if correct else "❌ Incorrect. Essaie encore !",
        'score': request.session['score_maths'],
        'a': a_nouveau,
        'b': b_nouveau
    })

def selection_jeu(request):
    eleve = get_object_or_404(Eleve, user=request.user)
    badges = Badge.objects.filter(eleve=eleve)

    titres_jeux = ['Chasseur de mots', 'Math Master', 'Problème illustré']
    total_jeux = len(titres_jeux)
    jeux_finis = sum(1 for titre in titres_jeux if badges.filter(titre__icontains=titre).exists())

    progression = (jeux_finis / total_jeux) * 100 if total_jeux > 0 else 0

    # ➕ Assistant IA simple
    if progression == 100:
        message_assistant = f"🎉 Bravo {eleve.prenom} ! Tu as complété tous les jeux. Tu es un vrai champion(ne) ! 🏆"
    elif progression >= 50:
        message_assistant = "🧠 Super progrès ! Continue comme ça, tu es sur la bonne voie. Essaie le jeu que tu n'as pas encore terminé !"
    else:
        message_assistant = "💪 Courage ! Commence par le jeu que tu préfères, chaque petit pas compte."

    return render(request, 'selection_jeu.html', {
        'eleve': eleve,
        'badges': badges,
        'progression': progression,
        'message_assistant': message_assistant,
    })
def chatbot_api(request):
    if request.method == "POST":
        question = request.POST.get("question")
        result = poser_question(question)

        try:
            # Essayer de parser en JSON (donc c'est un exercice)
            exercice = json.loads(result)
            return JsonResponse({
                'type': 'exercice',
                'data': exercice
            })
        except json.JSONDecodeError:
            # Sinon, réponse texte normale
            return JsonResponse({
                'type': 'réponse',
                'data': result
            })




  
def nouvelle_addition(request):
    a, b = randint(1, 10), randint(1, 10)
    request.session['addition'] = [a, b]
    return JsonResponse({
        'a': a,
        'b': b,
        'message': 'Nouvelle addition générée !'
        
    })
   
def jeu_probleme(request):
    niveau = request.GET.get('niveau', 'CE1')
    probleme = Probleme.objects.filter(niveau=niveau).order_by('?').first()
    message = ''
    correct = None

    if request.method == 'POST':
        user_reponse = request.POST.get('reponse', '').strip()
        probleme_id = request.POST.get('probleme_id')
        probleme = Probleme.objects.get(id=probleme_id)

        if user_reponse.lower() == probleme.reponse.lower():
            message = "✅ Bravo !"
            correct = True
        else:
            message = "❌ Mauvaise réponse. Essaie encore."
            correct = False

    return render(request, 'jeu_probleme.html', {
        'probleme': probleme,
        'message': message,
        'correct': correct,
        'niveau': niveau
    })
@login_required
def dashboard_admin(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'admin':
            return redirect('index')
    except Profile.DoesNotExist:
        return redirect('index')

    # Moyennes des notes par classe
    moyennes = (
        Note.objects.values('eleve__classe')
        .annotate(moyenne=Avg('note'))
        .order_by('eleve__classe')
    )

    # Données statistiques générales
    notifications = Notification.objects.select_related('user', 'eleve').order_by('-created_at')[:10]
    chart_classes_labels = [m['eleve__classe'] or '—' for m in moyennes]
    chart_classes_values = [float(m['moyenne'] or 0) for m in moyennes]
    chart_counts_labels = ['Élèves', 'Parents', 'Enseignants', 'Cours', 'Quiz']
    chart_counts_values = [
        Eleve.objects.count(),
        Parent.objects.count(),
        Enseignant.objects.count(),
        Cours.objects.count(),
        Quiz.objects.count(),
    ]

    context = {
        'nb_eleves': Eleve.objects.count(),
        'nb_parents': Parent.objects.count(),
        'nb_enseignants': Enseignant.objects.count(),
        'nb_cours': Cours.objects.count(),
        'nb_quiz': Quiz.objects.count(),
        'nb_notes': Note.objects.count(),
        'nb_absences': Absence.objects.count(),
        'nb_transports': Transport.objects.count(),
        'nb_notifications': Notification.objects.count(),
        'recent_notifications': notifications,
        'moyennes': list(moyennes),
        'chart_classes_labels': json.dumps(chart_classes_labels),
        'chart_classes_values': json.dumps(chart_classes_values),
        'chart_counts_labels': json.dumps(chart_counts_labels),
        'chart_counts_values': json.dumps(chart_counts_values),
    }

    return render(request, 'dashboards/dashboard_admin.html', context)

@login_required
def liste_parents(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('index')

    parents = Parent.objects.select_related('user', 'eleve').order_by('nom')
    return render(request, 'parents/liste_parents.html', {'parents': parents})
@login_required
def gerer_notes_admin(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return redirect('index')

    notes = Note.objects.all().select_related('eleve', 'enseignant')
    return render(request, 'notes/gerer_notes_admin.html', {
        'notes': notes,
    })
def paiements_eleves(request):
    paiements = PaiementEleve.objects.select_related('eleve').order_by('-date_paiement')
    return render(request, 'paiements/eleves.html', {'paiements': paiements})

def paiements_enseignants(request):
    paiements = PaiementEnseignant.objects.select_related('enseignant').order_by('-date_paiement')

    return render(request, 'paiements/enseignants.html', {'paiements': paiements})
def gestion_paiement(request):
    return render(request, 'paiements/gestion_paiement.html')

def ajouter_paiement_eleve(request):
    if request.method == "POST":
        form = PaiementEleveForm(request.POST)
        if form.is_valid():
            paiement = form.save()
            # Envoi de notification au parent
            envoyer_notification_paiement(
                paiement.eleve, paiement.montant, paiement.mois_concerne
            )
            return redirect('paiements_eleves')  # ou autre URL name
    else:
        form = PaiementEleveForm()
    return render(request, 'paiements/ajouter.html', {'form': form})
def ajouter_paiement_enseignant(request):
    if request.method == 'POST':
        form = PaiementEnseignantForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('paiements_enseignants')
    else:
        form = PaiementEnseignantForm()

    return render(request, 'paiements/ajouter_paiement_enseignant.html', {'form': form})

def carte_transport(request):
    return render(request, "transports/carte.html") 
def carte_transport_parent(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    return render(request, 'transports/carte_parent.html', {'eleve': eleve})

@login_required
def transport_position_parent(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    if eleve.parent_user != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    transport = getattr(eleve, 'transport', None)
    if not transport or transport.latitude is None or transport.longitude is None:
        return JsonResponse({'status': 'no_position'})

    return JsonResponse({
        'status': 'ok',
        'latitude': transport.latitude,
        'longitude': transport.longitude,
        'moyen': transport.moyen,
        'chauffeur': transport.chauffeur or '',
    })

@csrf_exempt
@require_http_methods(["POST"])
def transport_update_position(request):
    # Endpoint pour l'application qui envoie la position en temps réel
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
    else:
        data = request.POST

    eleve_id = data.get('eleve_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not (eleve_id and latitude and longitude):
        return JsonResponse({'error': 'missing_fields'}, status=400)

    eleve = get_object_or_404(Eleve, id=eleve_id)
    transport, _ = Transport.objects.get_or_create(eleve=eleve)
    transport.latitude = float(latitude)
    transport.longitude = float(longitude)
    transport.save(update_fields=['latitude', 'longitude'])

    return JsonResponse({'status': 'ok'})
def notifier_bus_arrive(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    sms_ok = notifier_parent_par_sms(eleve)
    email_ok = notifier_parent_par_email(eleve)
    app_ok = notifier_parent_par_app(eleve)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'status': 'ok',
            'sms': sms_ok,
            'email': email_ok,
            'app': app_ok,
        })

    messages.success(request, "Notifications envoyées au parent.")
    return redirect('dashboard_parent') 
