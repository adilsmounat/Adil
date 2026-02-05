from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'



def ready(self):
        # ⚠️ Import ici seulement !
        import core.signals 
        from django.contrib.auth.models import Group
        from django.db.utils import OperationalError, ProgrammingError

        try:
            for name in ['Enseignants', 'Administration']:
                Group.objects.get_or_create(name=name)
        except (OperationalError, ProgrammingError):
            # La DB n'est pas encore prête (ex: migrations en cours)
            pass