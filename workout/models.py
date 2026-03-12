from django.db import models


# ── Constantes ────────────────────────────────────────────────────────────────

SESSION_TYPES = [
    ('weights_tue', 'Pesas — Martes (Pull/Press)'),
    ('weights_sat', 'Pesas — Sábado (Piernas)'),
    ('weights_sun', 'Pesas — Domingo (Hombros/Brazos)'),
    ('football',    'Fútbol'),
    ('rest',        'Descanso'),
]

ABSENCE_REASONS = [
    ('injury',   'Lesión'),
    ('work',     'Trabajo'),
    ('illness',  'Enfermedad'),
    ('travel',   'Viaje'),
    ('other',    'Otro'),
]

# Ejercicios fijos por día
EXERCISES = {
    'weights_tue': [
        'Wide Pull-Downs',
        'Narrow Pull-Downs',
        'Dumbbell Row',
        'Dumbbell Incline Press',
        'Dumbbell Bench Press',
        'Dumbbell Pec Flys',
        'Push-ups',
    ],
    'weights_sat': [
        'Lunges',
        'Squats',
        'RDL',
        'Standing Calf Raises',
    ],
    'weights_sun': [
        'Dumbbell Rear Delt Raise',
        'Dumbbell Side Rise',
        'Dumbbell Shoulder Press',
        'Seated Ext.',
        'Incline Ext.',
        'Flat Ext.',
        'Standing Alternating Pronate Curls',
        'Standing Alternating Hammer Curls',
    ],
}

# Series fijas: (set_number, reps)
SETS = [(1, 15), (2, 12), (3, 10), (4, 8)]

# Ejercicios que no usan pesas (solo reps)
BODYWEIGHT_EXERCISES = {'Push-ups', 'Lunges', 'Squats'}


# ── Modelos ───────────────────────────────────────────────────────────────────

class Session(models.Model):
    date         = models.DateField(unique=True)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    notes        = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} — {self.get_session_type_display()}"

    @property
    def is_weights(self):
        return self.session_type.startswith('weights')

    @property
    def is_football(self):
        return self.session_type == 'football'


class FootballSession(models.Model):
    session        = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='football')
    completed      = models.BooleanField(default=True)
    absence_reason = models.CharField(max_length=20, choices=ABSENCE_REASONS, blank=True)

    def __str__(self):
        return f"{self.session.date} — {'Completado' if self.completed else self.get_absence_reason_display()}"


class ExerciseLog(models.Model):
    session       = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='logs')
    exercise_name = models.CharField(max_length=100)
    set_number    = models.PositiveSmallIntegerField()
    reps          = models.PositiveSmallIntegerField()
    weight_kg     = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    class Meta:
        ordering = ['exercise_name', 'set_number']
        unique_together = ['session', 'exercise_name', 'set_number']

    def __str__(self):
        w = f"{self.weight_kg}kg" if self.weight_kg else "BW"
        return f"{self.session.date} | {self.exercise_name} | S{self.set_number}: {self.reps}r × {w}"


class BodyMetrics(models.Model):
    date      = models.DateField(unique=True)
    weight_kg = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} — {self.weight_kg} kg"

    @property
    def bmi(self):
        from decouple import config
        height_m = config('USER_HEIGHT_M', default=1.70, cast=float)
        return round(float(self.weight_kg) / (height_m ** 2), 1)
