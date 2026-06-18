# Task Tracker System

Full-stack Django project with 4 roles: Admin, Team Leader, HR, Employee.

## Features
- Punch In / Punch Out with hours tracking
- Task management with status flow: Pending → In Review → Approved / Error Flagged
- Grammar check (LanguageTool AI) required before task submission
- Error reporting by Admin/Team Leader
- Role-based dashboards
- Light & Dark theme toggle

## Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py makemigrations
python manage.py migrate

# 3. Create superuser (Admin)
python manage.py createsuperuser

# 4. Run server
python manage.py runserver
```

## Create Users with Roles

Go to Django Admin at `/admin` and:
1. Create users (first name, last name, password)
2. Go to **User Profiles** → assign roles:
   - `admin` → full access
   - `team_leader` → manage team tasks
   - `hr` → view attendance
   - `employee` → own tasks, punch in/out
3. For employees, set their `team_leader` in UserProfile

## Railway Deploy

Push to GitHub, connect to Railway.
Add env variable:
```
SECRET_KEY = your-secret-key-here
DEBUG = False
```

The Procfile handles collectstatic + migrate + gunicorn automatically.

## Project Structure

```
task_tracker_system/
├── manage.py
├── requirements.txt
├── Procfile
├── tts/                  ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── tasktracker/          ← Main app
    ├── models.py         (UserProfile, Task, TaskError, Attendance)
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── signals.py        (auto-create UserProfile on new user)
    └── templates/tasktracker/
        ├── base.html         (sidebar + theme toggle)
        ├── login.html
        ├── employee_dashboard.html
        ├── admin_dashboard.html
        ├── tl_dashboard.html
        ├── hr_dashboard.html
        ├── task_detail.html
        ├── submit_task.html  ← grammar check here
        ├── create_task.html
        └── attendance_report.html
```
