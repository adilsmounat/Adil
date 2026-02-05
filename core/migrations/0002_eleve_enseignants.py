from django.db import migrations, models


def forwards_copy_enseignant(apps, schema_editor):
    Eleve = apps.get_model('core', 'Eleve')
    for eleve in Eleve.objects.exclude(enseignant__isnull=True).select_related('enseignant'):
        if eleve.enseignant_id:
            eleve.enseignants.add(eleve.enseignant_id)


def backwards_copy_enseignant(apps, schema_editor):
    Eleve = apps.get_model('core', 'Eleve')
    for eleve in Eleve.objects.all():
        premier = eleve.enseignants.first()
        if premier:
            eleve.enseignant = premier
            eleve.save(update_fields=['enseignant'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='eleve',
            name='enseignants',
            field=models.ManyToManyField(blank=True, related_name='eleves', to='core.enseignant'),
        ),
        migrations.RunPython(forwards_copy_enseignant, backwards_copy_enseignant),
        migrations.RemoveField(
            model_name='eleve',
            name='enseignant',
        ),
    ]
