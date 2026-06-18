from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json, requests

from .models import UserProfile, Task, TaskError, Attendance, Project


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request,
            username=request.POST.get('username'),
            password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'tasktracker/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ── Dashboard (role-based) ────────────────────────────────────────────────────

@login_required
def dashboard(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    today = timezone.localdate()
    attendance, _ = Attendance.objects.get_or_create(user=request.user, date=today)

    if profile.role == 'admin':
        tasks = Task.objects.all().order_by('-created_at')
        all_users = User.objects.select_related('profile').all()
        error_tasks = Task.objects.filter(status='error')
        return render(request, 'tasktracker/admin_dashboard.html', {
            'profile': profile, 'tasks': tasks, 'all_users': all_users,
            'error_tasks': error_tasks, 'attendance': attendance,
            'total': tasks.count(),
            'pending': tasks.filter(status='pending').count(),
            'in_review': tasks.filter(status='in_review').count(),
            'approved': tasks.filter(status='approved').count(),
            'errors': tasks.filter(status='error').count(),
        })

    elif profile.role == 'team_leader':
        my_team = UserProfile.objects.filter(team_leader=profile).select_related('user')
        team_users = [p.user for p in my_team]
        status_filter = request.GET.get('status')
        tasks = Task.objects.filter(assigned_to__in=team_users).order_by('-created_at')
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        error_tasks = Task.objects.filter(assigned_to__in=team_users, status='error')
        team_attendance = Attendance.objects.filter(user__in=team_users, date=today).select_related('user')
        return render(request, 'tasktracker/tl_dashboard.html', {
            'profile': profile, 'tasks': tasks, 'my_team': my_team,
            'attendance': attendance, 'error_tasks': error_tasks,
            'team_attendance': team_attendance,
            'total': Task.objects.filter(assigned_to__in=team_users).count(),
            'pending': Task.objects.filter(assigned_to__in=team_users, status='pending').count(),
            'in_review': Task.objects.filter(assigned_to__in=team_users, status='in_review').count(),
            'approved': Task.objects.filter(assigned_to__in=team_users, status='approved').count(),
            'errors': Task.objects.filter(assigned_to__in=team_users, status='error').count(),
        })

    elif profile.role == 'hr':
        all_att = Attendance.objects.filter(date=today).select_related('user__profile')
        all_users = User.objects.select_related('profile').all()
        # Task report per user
        task_report = []
        for u in all_users:
            utasks = Task.objects.filter(assigned_to=u)
            if utasks.exists():
                task_report.append({
                    'name': u.get_full_name() or u.username,
                    'total': utasks.count(),
                    'approved': utasks.filter(status='approved').count(),
                    'pending': utasks.filter(status='pending').count(),
                    'errors': utasks.filter(status='error').count(),
                })
        return render(request, 'tasktracker/hr_dashboard.html', {
            'profile': profile, 'all_att': all_att,
            'all_users': all_users, 'attendance': attendance,
            'task_report': task_report,
            'total_users': all_users.count(),
            'present_today': all_att.exclude(punch_in=None).count(),
            'total_tasks': Task.objects.count(),
            'approved_tasks': Task.objects.filter(status='approved').count(),
        })

    else:  # employee
        my_tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')
        return render(request, 'tasktracker/employee_dashboard.html', {
            'profile': profile, 'tasks': my_tasks, 'attendance': attendance,
            'pending': my_tasks.filter(status='pending').count(),
            'approved': my_tasks.filter(status='approved').count(),
            'errors': my_tasks.filter(status='error').count(),
        })


# ── Attendance ────────────────────────────────────────────────────────────────

@login_required
@require_POST
def punch_in(request):
    today = timezone.localdate()
    att, _ = Attendance.objects.get_or_create(user=request.user, date=today)
    if not att.punch_in:
        att.punch_in = timezone.now()
        att.save()
        messages.success(request, f'Punched in at {att.punch_in.strftime("%I:%M %p")} ✓')
    else:
        messages.warning(request, 'Already punched in today.')
    return redirect('dashboard')


@login_required
@require_POST
def punch_out(request):
    today = timezone.localdate()
    att, _ = Attendance.objects.get_or_create(user=request.user, date=today)
    if att.punch_in and not att.punch_out:
        att.punch_out = timezone.now()
        att.save()
        messages.success(request, f'Punched out at {att.punch_out.strftime("%I:%M %p")}. Total: {att.hours_worked}h ✓')
    elif not att.punch_in:
        messages.error(request, 'Punch in first!')
    else:
        messages.warning(request, 'Already punched out today.')
    return redirect('dashboard')


@login_required
def attendance_report(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role not in ['admin', 'hr']:
        return redirect('dashboard')
    records = Attendance.objects.select_related('user').order_by('-date', 'user__first_name')[:200]
    return render(request, 'tasktracker/attendance_report.html', {'records': records, 'profile': profile})


# ── Tasks ─────────────────────────────────────────────────────────────────────

@login_required
def create_task(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role not in ['admin', 'team_leader', 'hr']:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    if profile.role == 'team_leader':
        assignable = [p.user for p in UserProfile.objects.filter(team_leader=profile).select_related('user')]
    else:
        assignable = User.objects.select_related('profile').all()

    if request.method == 'POST':
        Task.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            assigned_to_id=request.POST.get('assigned_to'),
            assigned_by=request.user,
            priority=request.POST.get('priority', 'medium'),
            due_date=request.POST.get('due_date') or None,
        )
        messages.success(request, 'Task created and assigned successfully!')
        return redirect('dashboard')

    return render(request, 'tasktracker/create_task.html', {'assignable': assignable, 'profile': profile})


@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    profile = get_object_or_404(UserProfile, user=request.user)
    errors = task.errors.all().order_by('-created_at')
    can_manage = profile.role in ['admin', 'team_leader']
    is_owner = task.assigned_to == request.user
    return render(request, 'tasktracker/task_detail.html', {
        'task': task, 'errors': errors,
        'can_manage': can_manage, 'is_owner': is_owner, 'profile': profile,
    })


@login_required
def submit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
    if task.status not in ['pending', 'error']:
        messages.warning(request, 'This task cannot be submitted right now.')
        return redirect('task_detail', task_id=task_id)

    if request.method == 'POST':
        task.submission_note = request.POST.get('submission_note', '')
        task.status = 'in_review'
        task.grammar_checked = True
        task.save()
        messages.success(request, 'Task submitted for review! ✓')
        return redirect('dashboard')

    return render(request, 'tasktracker/submit_task.html', {'task': task})


@login_required
@require_POST
def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role not in ['admin', 'team_leader']:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    new_status = request.POST.get('status')
    if new_status in ['approved', 'in_review', 'pending', 'error']:
        task.status = new_status
        task.save()
        if new_status == 'error':
            TaskError.objects.create(
                task=task,
                reported_by=request.user,
                error_message=request.POST.get('error_message', 'Error flagged by reviewer.')
            )
        messages.success(request, f'Task status updated to "{task.get_status_display()}".')

    return redirect('task_detail', task_id=task_id)


# ── Grammar Check API ─────────────────────────────────────────────────────────

@login_required
def grammar_check(request):
    if request.method == 'POST':
        try:
            text = json.loads(request.body).get('text', '').strip()
        except Exception:
            return JsonResponse({'error': 'Invalid request'}, status=400)

        if not text:
            return JsonResponse({'matches': []})

        try:
            resp = requests.post(
                'https://api.languagetool.org/v2/check',
                data={'text': text, 'language': 'en-US'},
                timeout=12
            )
            data = resp.json()
            matches = [{
                'message': m['message'],
                'context': m['context']['text'],
                'offset': m['offset'],
                'length': m['length'],
                'replacements': [r['value'] for r in m.get('replacements', [])[:3]],
            } for m in data.get('matches', [])]
            return JsonResponse({'matches': matches})
        except Exception as e:
            return JsonResponse({'matches': [], 'api_error': str(e)})

    return JsonResponse({'error': 'POST only'}, status=405)


# ── Signup ────────────────────────────────────────────────────────────────────

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            role = request.POST.get('role', 'employee')
            if role not in ['employee', 'team_leader', 'hr']:
                role = 'employee'
            user = User.objects.create_user(
                username=username, password=password,
                first_name=first_name, last_name=last_name, email=email
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            login(request, user)
            messages.success(request, f'Welcome, {first_name or username}! Role: {profile.get_role_display()}')
            return redirect('dashboard')
    return render(request, 'tasktracker/signup.html')


# ── Projects ──────────────────────────────────────────────────────────────────

@login_required
def projects_view(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role == 'admin':
        projects = Project.objects.all().order_by('-created_at')
    else:
        projects = Project.objects.filter(members=request.user).order_by('-created_at')
    return render(request, 'tasktracker/projects.html', {'projects': projects, 'profile': profile})


@login_required
def create_project(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role not in ['admin', 'team_leader']:
        messages.error(request, 'Permission denied.')
        return redirect('projects')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        due_date = request.POST.get('due_date') or None
        member_ids = request.POST.getlist('members')

        project = Project.objects.create(
            name=name, description=description,
            due_date=due_date, created_by=request.user
        )
        if member_ids:
            project.members.set(member_ids)
        project.members.add(request.user)
        messages.success(request, 'Project created!')
        return redirect('projects')

    all_users = User.objects.select_related('profile').all()
    return render(request, 'tasktracker/create_project.html', {'all_users': all_users, 'profile': profile})


@login_required
def project_detail_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    profile = get_object_or_404(UserProfile, user=request.user)
    tasks = project.tasks.all().order_by('-created_at')
    return render(request, 'tasktracker/project_detail.html', {
        'project': project, 'tasks': tasks, 'profile': profile
    })
