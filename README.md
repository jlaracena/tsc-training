# tsc-training

A local web app to track your weekly training sessions — weights and football — with automatic macro calculations tailored for vegetarians.

Designed to run on a home server (Mac Mini, Raspberry Pi, etc.) and be accessible from any device via [Tailscale](https://tailscale.com/).

---

## Features

### Today's session (`/`)
The app automatically detects what day it is and shows the corresponding workout:

| Day | Session |
|---|---|
| Monday | Football ⚽ |
| Tuesday | Weights — Pull/Press 💪 |
| Wednesday | Rest 😴 |
| Thursday | Football ⚽ |
| Friday | Rest 😴 |
| Saturday | Weights — Legs 💪 |
| Sunday | Weights — Shoulders/Arms 💪 |

- **Weights**: fixed pyramid sets (15 / 12 / 10 / 8 reps), enter weight per set. Shows last weight used per exercise as reference.
- **Football**: mark as completed or log absence reason (injury, work, illness, travel, other)
- **Rest**: daily macros and recovery tips

### Macro calculator
Daily nutrition targets adjust automatically based on training type:

| Session | TDEE multiplier |
|---|---|
| Weights | ×1.375 |
| Football | ×1.55 |
| Rest | ×1.2 |

BMR calculated via **Mifflin-St Jeor** formula. Targets follow recommendations from [thefitness.wiki](https://thefitness.wiki/improving-your-diet/):
- **Protein**: 0.9g per lb of bodyweight (adjusted up slightly for vegetarians)
- **Fat**: 0.35g per lb (above minimum to support vegetarian diet quality)
- **Carbs**: remaining calories — higher on football days for recovery

Includes a collapsible panel with **vegetarian protein sources** and how much protein each provides.

### Body weight tracking
Log your daily weight. IMC/BMI calculated automatically.

### History (`/history/`)
- **Body weight chart** — trend over time
- **Exercise progression** — select any weighted exercise, see max weight per session as a line chart
- **Session log** — table of last 12 weeks with type and summary

---

## Setup

### Requirements
- Python 3.10+

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/tsc-training.git
cd tsc-training

python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env
# Edit .env with your profile data
```

### Environment variables (`.env`)

```
DJANGO_SECRET_KEY=generate-a-random-key
USER_WEIGHT_KG=70.0
USER_HEIGHT_M=1.70
USER_AGE=30
```

To generate a Django secret key:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Run

```bash
venv/bin/python manage.py migrate
venv/bin/python manage.py runserver 0.0.0.0:8767
```

Open `http://localhost:8767` — or `http://<server-ip>:8767` from other devices on your network.

---

## Run on system startup (macOS with launchd)

Create `com.tsc-training.plist` (not included in repo — contains local paths):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.tsc-training</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/venv/bin/python</string>
    <string>/path/to/tsc-training/manage.py</string>
    <string>runserver</string>
    <string>0.0.0.0:8767</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/path/to/tsc-training</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/tsc-training.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/tsc-training.log</string>
</dict>
</plist>
```

```bash
cp com.tsc-training.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tsc-training.plist
```

---

## Remote access

Use [Tailscale](https://tailscale.com/) to access the app from anywhere (after football, on mobile, etc.):

1. Install Tailscale on the server and your phone
2. Connect both to the same Tailscale network
3. Access via `http://<tailscale-ip>:8767`

No port forwarding required. Free for personal use.

---

## Customizing the workout schedule

Edit `workout/models.py` to change exercises, and `workout/views.py` to change the weekly schedule:

```python
WEEKLY_SCHEDULE = {
    0: 'football',     # Monday
    1: 'weights_tue',  # Tuesday
    2: 'rest',         # Wednesday
    3: 'football',     # Thursday
    4: 'rest',         # Friday
    5: 'weights_sat',  # Saturday
    6: 'weights_sun',  # Sunday
}
```

---

## Nutrition approach

Macro targets are based on guidelines from [thefitness.wiki/improving-your-diet/](https://thefitness.wiki/improving-your-diet/), adapted for vegetarian athletes:

- Prioritize protein on weights days — harder to hit on a vegetarian diet
- Prioritize carbs on football/cardio days for glycogen recovery
- Keep fat above minimum (0.35g/lb) to support hormones and absorption of fat-soluble vitamins
- Track bodyweight weekly to calibrate TDEE estimates over time

---

## Tech stack

- **Django 4.2** — web framework
- **Bootstrap 5** — frontend
- **Chart.js** — progress charts
- **SQLite** — local database
- **python-decouple** — environment variable management
