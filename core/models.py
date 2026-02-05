from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Classes possibles
CLASSES = [
    ('CE1', 'CE1'),
    ('CE2', 'CE2'),
    ('CE3', 'CE3'),
    ('CE4', 'CE4'),
    ('CE5', 'CE5'),
    ('CE6', 'CE6'),
]

class Enseignant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialite = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username

class Eleve(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE, related_name='eleve_profile')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    naissance = models.DateField(null=True, blank=True)
    classe = models.CharField(max_length=3, choices=CLASSES, null=True, blank=True)
    parent_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfants')
    enseignants = models.ManyToManyField(Enseignant, blank=True, related_name='eleves')
    email_parent = models.EmailField(null=True, blank=True)

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.classe})"

class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    eleve = models.OneToOneField(Eleve, on_delete=models.CASCADE, related_name="parent_profile", null=True)

    def __str__(self):
        return self.nom

class Absence(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='absences')
    date = models.DateField()
    motif = models.TextField(blank=True)
    justifiee = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.eleve} - {self.date} - {'Justifiée' if self.justifiee else 'Non justifiée'}"

class Note(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes')
    matiere = models.CharField(max_length=100)
    note = models.FloatField()
    date = models.DateField()
    enseignant = models.ForeignKey(Enseignant, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')

    def __str__(self):
        return f"{self.eleve} - {self.matiere}: {self.note}"

class Transport(models.Model):
    MOYENS_TRANSPORT = [
        ('Bus', 'Bus'),
        ('Taxi', 'Taxi'),
        ('Pied', 'À pied'),
        ('Voiture', 'Voiture des parents'),
        ('Autre', 'Autre'),
    ]

    eleve = models.OneToOneField(Eleve, on_delete=models.CASCADE)
    moyen = models.CharField(max_length=50, choices=MOYENS_TRANSPORT, default='Bus')
    chauffeur = models.CharField(max_length=100, blank=True, null=True)
    numero_bus = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.eleve.nom} - {self.moyen}"

class Profile(models.Model):
    ROLE_CHOICES = [
        ('enseignant', 'Enseignant'),
        ('parent', 'Parent'),
        ('eleve', 'Élève'),
        ('admin', 'Administration'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class EmploiDuTemps(models.Model):
    JOURS_CHOICES = [
        ('lundi', 'Lundi'),
        ('mardi', 'Mardi'),
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'),
        ('vendredi', 'Vendredi'),
        ('samedi', 'Samedi'),
    ]

    jour = models.CharField(max_length=10, choices=JOURS_CHOICES)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    matiere = models.CharField(max_length=100)
    salle = models.CharField(max_length=50)
    enseignant = models.ForeignKey(Enseignant, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.jour} {self.heure_debut}-{self.heure_fin} : {self.matiere}"

class Cours(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    enseignant = models.ForeignKey(Enseignant, on_delete=models.CASCADE, related_name='cours')
    date_creation = models.DateTimeField(auto_now_add=True)
    classe = models.CharField(max_length=3, choices=CLASSES, null=True, blank=True)
    fichier_pdf = models.FileField(upload_to='cours_pdfs/', blank=True, null=True)

    def __str__(self):
        return f"{self.nom} - {self.classe}"

    def progression_pour(self, eleve):
        total = self.quizz.count()
        faits = eleve.soumissionquiz_set.filter(quiz__cours=self).count()
        return int((faits / total) * 100) if total > 0 else 0

class Quiz(models.Model):
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='quizz')
    titre = models.CharField(max_length=200, default='Sans titre')
    description = models.TextField(blank=True)
    duree_minutes = models.PositiveIntegerField(default=5)

    def __str__(self):
        return f"{self.titre} – {self.cours}"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    texte = models.CharField(max_length=255)
    choix_1 = models.CharField(max_length=100)
    choix_2 = models.CharField(max_length=100)
    choix_3 = models.CharField(max_length=100)
    bonne_reponse = models.CharField(max_length=100)

    def get_choix(self):
        return [self.choix_1, self.choix_2, self.choix_3]

    def __str__(self):
        return self.texte

class SoumissionQuiz(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

class Badge(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE)
    titre = models.CharField(max_length=100)
    date_attribue = models.DateTimeField(auto_now_add=True)

class Probleme(models.Model):
    question = models.TextField()
    image = models.ImageField(upload_to='problemes/', blank=True, null=True)
    reponse = models.CharField(max_length=100)
    niveau = models.CharField(max_length=10, choices=[('CE1', 'CE1'), ('CE2', 'CE2'), ('CM1', 'CM1'), ('CM2', 'CM2')])

    def __str__(self):
        return f"{self.niveau} - {self.question[:30]}"

class PaiementEleve(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=8, decimal_places=2)
    mois_concerne = models.CharField(max_length=20, default="janvier")
    date_paiement = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.eleve.nom} - {self.mois_concerne} - {self.montant}DH"

class PaiementEnseignant(models.Model):
    enseignant = models.ForeignKey(Enseignant, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=8, decimal_places=2)
    date_paiement = models.DateField(default=timezone.now)
    mois_concerne = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.enseignant.user.username} - {self.montant}€ pour {self.mois_concerne}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    eleve = models.ForeignKey(Eleve, null=True, blank=True, on_delete=models.SET_NULL)
    titre = models.CharField(max_length=120)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.titre}"
