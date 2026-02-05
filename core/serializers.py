from rest_framework import serializers
from .models import Eleve
from .models import Absence
from .models import Note
from .models import Transport



class AbsenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Absence
        fields = '__all__'

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = '__all__'

class TransportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transport
        fields = '__all__'

class EleveSerializer(serializers.ModelSerializer):
    absences = AbsenceSerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    transports = TransportSerializer(many=True, read_only=True)

    class Meta:
        model = Eleve
        fields = '__all__'
