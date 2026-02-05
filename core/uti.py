# core/utils.py

from .models import Note, SoumissionQuiz, Absence, Badge

def analyse_apprentissage(eleve):
    recommandations = []
    stats = {}

    # --- Notes ---
    notes = Note.objects.filter(eleve=eleve)
    if notes.exists():
        moyenne = sum(n.note for n in notes) / notes.count()
        stats['moyenne_notes'] = round(moyenne, 2)

        if moyenne < 10:
            recommandations.append("📚 Renforce les bases : recommence les exercices simples.")
        elif moyenne < 14:
            recommandations.append("📝 Bon niveau ! Continue les exercices intermédiaires.")
        else:
            recommandations.append("🌟 Excellent ! Tu peux passer à des exercices avancés.")
    else:
        recommandations.append("⚠️ Aucune note trouvée. Commence par les évaluations du professeur.")

    # --- Quiz ---
    quiz_scores = SoumissionQuiz.objects.filter(eleve=eleve)
    if quiz_scores.exists():
        moy_quiz = sum(q.score for q in quiz_scores if q.score is not None) / quiz_scores.count()
        stats['moyenne_quiz'] = round(moy_quiz, 2)

        if moy_quiz < 5:
            recommandations.append("❗ Les quiz sont encore difficiles, revois les cours avant de les refaire.")
        elif moy_quiz < 8:
            recommandations.append("👍 Bon début ! Refais les quiz où tu as eu un score faible.")
        else:
            recommandations.append("🏆 Tu maîtrises bien les quiz, bravo !")

    # --- Badges / jeux ---
    badges = Badge.objects.filter(eleve=eleve)
    stats['badges_total'] = badges.count()

    if badges.count() == 0:
        recommandations.append("🎮 Essaie les mini-jeux pour t’entraîner en t’amusant.")
    elif badges.count() == 1:
        recommandations.append("💡 Tu as déjà un badge, continue pour en débloquer d’autres.")
    else:
        recommandations.append("🔥 Super, tu cumules les badges ! Continue sur cette lancée.")

    # --- Absences ---
    nb_abs = Absence.objects.filter(eleve=eleve).count()
    stats['absences'] = nb_abs

    if nb_abs >= 3:
        recommandations.append("⚠️ Tu as plusieurs absences, pense à revoir les cours manqués.")

    return {
        "statistiques": stats,
        "recommandations": recommandations,
    }
