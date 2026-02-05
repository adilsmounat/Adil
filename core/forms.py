from django import forms
from .models import Eleve
from .models import Transport
from django.contrib.auth.models import User
from .models import Enseignant,Absence,Note,Cours
from .models import PaiementEleve,PaiementEnseignant
from .models import Transport

class EleveForm(forms.ModelForm):
    class Meta:
        model = Eleve
        fields = ['nom', 'prenom', 'naissance', 'classe']


class ContactEnseignantForm(forms.Form):
    sujet = forms.CharField(max_length=120, label="Sujet", widget=forms.TextInput(attrs={'class': 'form-control'}))
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'rows': 6, 'class': 'form-control'})
    )
    email_parent = forms.EmailField(
        required=False,
        label="Votre email (optionnel)",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ['eleve', 'chauffeur', 'numero_bus']

class EnseignantForm(forms.ModelForm):
    username = forms.CharField(label="Nom d'user")
    password = forms.CharField(widget=forms.PasswordInput)
    email = forms.EmailField()

    class Meta:
        model = Enseignant
        fields = ['specialite']

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email']
        )
        enseignant = super().save(commit=False)
        enseignant.user = user
        if commit:
            enseignant.save()
        return enseignant


class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = ['eleve', 'date', 'motif', 'justifiee']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['eleve', 'matiere', 'note', 'date']
# forms.py


class CoursForm(forms.ModelForm):
    class Meta:
        model = Cours
        fields = ['nom', 'description', 'fichier_pdf']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du cours'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description'}),
        }


class PaiementEleveForm(forms.ModelForm):
    class Meta:
        model = PaiementEleve
        fields = ['eleve', 'montant', 'mois_concerne']
class PaiementEnseignantForm(forms.ModelForm):
    class Meta:
        model = PaiementEnseignant
        fields = ['enseignant', 'montant', 'date_paiement', 'mois_concerne']


class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ['eleve', 'moyen', 'chauffeur', 'numero_bus', 'latitude', 'longitude']
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }


