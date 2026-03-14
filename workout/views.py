import json
from datetime import date, timedelta
from decimal import Decimal

from decouple import config
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import (ABSENCE_REASONS, BODYWEIGHT_EXERCISES, EXERCISES, SETS,
                     SESSION_TYPES, BodyMetrics, ExerciseLog, FootballSession,
                     Session)

# ── Perfil usuario (desde .env) ───────────────────────────────────────────────

USER_WEIGHT_KG = config('USER_WEIGHT_KG', default=70.0, cast=float)
USER_HEIGHT_M  = config('USER_HEIGHT_M',  default=1.70, cast=float)
USER_AGE       = config('USER_AGE',       default=30,   cast=int)

# ── Schedule semanal ──────────────────────────────────────────────────────────

WEEKLY_SCHEDULE = {
    0: 'football',     # Lunes
    1: 'weights_tue',  # Martes
    2: 'rest',         # Miércoles
    3: 'football',     # Jueves
    4: 'rest',         # Viernes
    5: 'weights_sat',  # Sábado
    6: 'weights_sun',  # Domingo
}


def session_type_for_date(d):
    return WEEKLY_SCHEDULE[d.weekday()]


# ── Macros ────────────────────────────────────────────────────────────────────

def calculate_macros(session_type, weight_kg=USER_WEIGHT_KG):
    """
    Calcula macros diarios según tipo de entrenamiento.
    Basado en thefitness.wiki/improving-your-diet/ y ajustado para vegetarianos.
    BMR Mifflin-St Jeor (hombre): 10×kg + 6.25×cm - 5×edad + 5
    """
    bmr = 10 * weight_kg + 6.25 * (USER_HEIGHT_M * 100) - 5 * USER_AGE + 5

    multipliers = {
        'weights_tue': 1.375,
        'weights_sat': 1.375,
        'weights_sun': 1.375,
        'football':    1.55,
        'rest':        1.2,
    }
    tdee = round(bmr * multipliers.get(session_type, 1.2))

    weight_lb = weight_kg * 2.205
    protein_g = round(weight_lb * 0.9)   # 0.9g/lb — bueno para vegetarianos

    # Vegetariano: subir proteína un poco, grasas saludables importantes
    fat_g    = round(weight_lb * 0.35)   # 0.35g/lb (mínimo 0.3, algo más para vegetarianos)
    fat_cal  = fat_g * 9
    prot_cal = protein_g * 4
    carb_cal = tdee - fat_cal - prot_cal
    carb_g   = max(0, round(carb_cal / 4))

    # Fuentes vegetarianas de proteína para llegar al objetivo
    veg_sources = [
        {'food': 'Tofu firme',        'per_100g': 17, 'unit': '100g'},
        {'food': 'Tempeh',            'per_100g': 19, 'unit': '100g'},
        {'food': 'Lentejas cocidas',  'per_100g': 9,  'unit': '100g'},
        {'food': 'Garbanzos cocidos', 'per_100g': 9,  'unit': '100g'},
        {'food': 'Huevos',            'per_100g': 13, 'unit': '100g (2 huevos)'},
        {'food': 'Yogur griego',      'per_100g': 10, 'unit': '100g'},
        {'food': 'Queso cottage',     'per_100g': 11, 'unit': '100g'},
        {'food': 'Proteína vegetal en polvo', 'per_100g': 70, 'unit': '30g porción (~21g prot)'},
    ]

    return {
        'tdee': tdee,
        'protein_g': protein_g,
        'carb_g': carb_g,
        'fat_g': fat_g,
        'veg_sources': veg_sources,
        'note': 'Más carbos en días de fútbol para recuperación. Prioriza proteína en días de pesas.'
        if session_type in ('football', 'weights_tue', 'weights_sat', 'weights_sun')
        else 'Día de descanso: reduce carbos, mantén proteína.',
    }


# ── Vistas ────────────────────────────────────────────────────────────────────

def today(request):
    today_date = date.today()
    session_type = session_type_for_date(today_date)
    session = Session.objects.filter(date=today_date).first()

    # Últimos pesos registrados por ejercicio (para mostrar como referencia)
    last_weights = {}
    if session_type in EXERCISES:
        for exercise in EXERCISES[session_type]:
            last_log = (ExerciseLog.objects
                        .filter(exercise_name=exercise)
                        .exclude(session__date=today_date)
                        .order_by('-session__date')
                        .first())
            if last_log and last_log.weight_kg:
                last_weights[exercise] = float(last_log.weight_kg)

    macros = calculate_macros(session_type)
    metrics = BodyMetrics.objects.first()

    # Razones personalizadas previas (notas de sesiones saltadas con motivo "Otro")
    custom_skip_reasons = list(
        Session.objects
        .filter(skipped=True, skip_reason='other')
        .exclude(notes='')
        .values_list('notes', flat=True)
        .distinct()
        .order_by('-date')[:10]
    )

    return render(request, 'workout/today.html', {
        'active_tab': 'today',
        'today': today_date,
        'session_type': session_type,
        'session_type_display': dict(SESSION_TYPES).get(session_type, ''),
        'session': session,
        'exercises': EXERCISES.get(session_type, []),
        'sets': SETS,
        'bodyweight_exercises': BODYWEIGHT_EXERCISES,
        'last_weights': last_weights,
        'macros': macros,
        'metrics': metrics,
        'absence_reasons': ABSENCE_REASONS,
        'custom_skip_reasons': custom_skip_reasons,
    })


def save_session(request):
    if request.method != 'POST':
        return redirect('today')

    today_date = date.today()
    session_type = session_type_for_date(today_date)
    session, _ = Session.objects.get_or_create(date=today_date, defaults={'session_type': session_type})

    if session_type == 'football':
        completed = request.POST.get('completed') == '1'
        absence_reason = '' if completed else request.POST.get('absence_reason', '')
        FootballSession.objects.update_or_create(
            session=session,
            defaults={'completed': completed, 'absence_reason': absence_reason}
        )

    elif session_type in EXERCISES:
        skipped = request.POST.get('skipped') == '1'
        session.skipped        = skipped
        session.skip_reason    = request.POST.get('skip_reason', '') if skipped else ''
        session.notes          = request.POST.get('notes', '').strip() if skipped else ''
        session.warm_up_done   = request.POST.get('warm_up_done') == '1'
        session.cool_down_done = request.POST.get('cool_down_done') == '1'
        session.save()

        if not skipped:
            for exercise in EXERCISES[session_type]:
                for set_num, default_reps in SETS:
                    is_bw = exercise in BODYWEIGHT_EXERCISES
                    if is_bw:
                        reps_done = request.POST.get(f'reps_{exercise}_{set_num}')
                        weight_val = None
                        if not reps_done:
                            continue
                        try:
                            reps_val = int(reps_done)
                        except (ValueError, TypeError):
                            continue
                    else:
                        weight = request.POST.get(f'weight_{exercise}_{set_num}')
                        reps_val = default_reps
                        if not weight:
                            continue
                        try:
                            weight_val = Decimal(weight)
                        except (ValueError, TypeError):
                            continue

                    ExerciseLog.objects.update_or_create(
                        session=session,
                        exercise_name=exercise,
                        set_number=set_num,
                        defaults={'reps': reps_val, 'weight_kg': weight_val}
                    )

    return redirect('today')


def save_metrics(request):
    if request.method != 'POST':
        return redirect('today')
    try:
        weight = Decimal(request.POST.get('weight_kg', ''))
        BodyMetrics.objects.update_or_create(
            date=date.today(),
            defaults={'weight_kg': weight}
        )
    except Exception:
        pass
    return redirect('today')


def history(request):
    # Últimas 12 semanas de sesiones
    since = date.today() - timedelta(weeks=12)
    sessions = Session.objects.filter(date__gte=since).prefetch_related('logs', 'football')

    # Datos para gráficos de peso corporal
    metrics = list(BodyMetrics.objects.order_by('date').values('date', 'weight_kg'))
    metrics_json = json.dumps([
        {'date': str(m['date']), 'weight': float(m['weight_kg'])} for m in metrics
    ])

    # Ejercicios disponibles para gráfico de progresión
    all_exercises = []
    for exs in EXERCISES.values():
        all_exercises.extend(exs)
    all_exercises = [e for e in all_exercises if e not in BODYWEIGHT_EXERCISES]

    return render(request, 'workout/history.html', {
        'active_tab': 'history',
        'sessions': sessions,
        'metrics_json': metrics_json,
        'all_exercises': sorted(set(all_exercises)),
    })


def exercise_progress_api(request, exercise_name):
    logs = (ExerciseLog.objects
            .filter(exercise_name=exercise_name, weight_kg__isnull=False)
            .order_by('session__date', 'set_number')
            .values('session__date', 'set_number', 'reps', 'weight_kg'))

    data = {}
    for log in logs:
        d = str(log['session__date'])
        if d not in data:
            data[d] = []
        data[d].append({
            'set': log['set_number'],
            'reps': log['reps'],
            'weight': float(log['weight_kg']),
        })

    # Para la línea de progresión: peso máximo por sesión
    trend = [
        {'date': d, 'max_weight': max(s['weight'] for s in sets)}
        for d, sets in sorted(data.items())
    ]

    return JsonResponse({'data': data, 'trend': trend})
