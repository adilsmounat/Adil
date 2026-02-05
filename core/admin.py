from django.contrib import admin
from .models import (
    Eleve, Absence, Note, Transport, Profile,
    Enseignant, Parent, Cours, Quiz, Question, Probleme
)

# Enregistrements simples
admin.site.register(Probleme)
admin.site.register(Absence)
admin.site.register(Note)
admin.site.register(Transport)
admin.site.register(Profile)
admin.site.register(Quiz)
admin.site.register(Question)

@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = ("user_username", "specialite")
    search_fields = ("user__username", "specialite")

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = "Utilisateur"

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("nom", "user_username", "telephone", "email", "eleve")
    search_fields = ("nom", "user__username", "telephone", "email")

    def user_username(self, obj):
        return obj.user.username if obj.user else "—"
    user_username.short_description = "Utilisateur"

@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ("prenom", "nom", "classe", "get_parent", "get_enseignants")
    search_fields = ("nom", "prenom", "classe")
    list_filter = ("classe",)

    def get_parent(self, obj):
        # 1) Si Eleve.parent_user (User)
        if getattr(obj, "parent_user", None):
            return obj.parent_user.get_full_name() or obj.parent_user.username
        # 2) Si Parent OneToOne lié via related_name="parent_profile"
        if hasattr(obj, "parent_profile") and obj.parent_profile:
            return obj.parent_profile.nom
        return "—"
    get_parent.short_description = "Parent"

    def get_enseignants(self, obj):
        enseignants = obj.enseignants.all()
        if not enseignants:
            return "—"
        return ", ".join(
            e.user.get_full_name() or e.user.username
            for e in enseignants
        )
    get_enseignants.short_description = "Enseignants"

@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ("nom", "enseignant", "classe", "date_creation")
    search_fields = ("nom", "enseignant__user__username")
    list_filter = ("classe", "date_creation")
