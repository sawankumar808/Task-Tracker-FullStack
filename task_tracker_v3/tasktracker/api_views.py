from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile, Project, Task, TaskError, Attendance
from .serializers import (
    ProjectSerializer, TaskSerializer, TaskErrorSerializer,
    AttendanceSerializer, SignupSerializer, UserSerializer
)


# ── Auth APIs ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'message': 'Account created successfully!',
            'token': token.key,
            'user': {'username': user.username, 'role': user.profile.role}
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'username': user.username,
                'full_name': user.get_full_name(),
                'role': user.profile.role
            }
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
def api_me(request):
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'full_name': user.get_full_name(),
        'email': user.email,
        'role': user.profile.role,
    })


# ── Project APIs ──────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
def api_projects(request):
    profile = request.user.profile

    if request.method == 'GET':
        if profile.role == 'admin':
            projects = Project.objects.all().order_by('-created_at')
        else:
            projects = Project.objects.filter(members=request.user).order_by('-created_at')
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        if profile.role not in ['admin', 'team_leader']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def api_project_detail(request, pk):
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ProjectSerializer(project)
        return Response(serializer.data)

    if request.user.profile.role not in ['admin', 'team_leader']:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        project.delete()
        return Response({'message': 'Project deleted'}, status=status.HTTP_204_NO_CONTENT)


# ── Task APIs ─────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
def api_tasks(request):
    profile = request.user.profile

    if request.method == 'GET':
        if profile.role == 'admin':
            tasks = Task.objects.all().order_by('-created_at')
        elif profile.role == 'team_leader':
            team = [p.user for p in UserProfile.objects.filter(team_leader=profile)]
            tasks = Task.objects.filter(assigned_to__in=team).order_by('-created_at')
        else:
            tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        # Filter by project
        project_filter = request.query_params.get('project')
        if project_filter:
            tasks = tasks.filter(project_id=project_filter)

        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        if profile.role not in ['admin', 'team_leader', 'hr']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(assigned_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def api_task_detail(request, pk):
    try:
        task = Task.objects.get(pk=pk)
    except Task.DoesNotExist:
        return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    if request.method == 'PUT':
        profile = request.user.profile
        allowed = profile.role in ['admin', 'team_leader'] or task.assigned_to == request.user
        if not allowed:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # If error status, create error record
            if request.data.get('status') == 'error' and request.data.get('error_message'):
                TaskError.objects.create(
                    task=task,
                    reported_by=request.user,
                    error_message=request.data.get('error_message')
                )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if request.user.profile.role != 'admin':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        task.delete()
        return Response({'message': 'Task deleted'}, status=status.HTTP_204_NO_CONTENT)


# ── Dashboard API ─────────────────────────────────────────────────────────────

@api_view(['GET'])
def api_dashboard(request):
    profile = request.user.profile
    today = timezone.localdate()

    if profile.role == 'admin':
        tasks = Task.objects.all()
        total_users = User.objects.count()
    elif profile.role == 'team_leader':
        team = [p.user for p in UserProfile.objects.filter(team_leader=profile)]
        tasks = Task.objects.filter(assigned_to__in=team)
        total_users = len(team)
    else:
        tasks = Task.objects.filter(assigned_to=request.user)
        total_users = None

    # Attendance
    try:
        att = Attendance.objects.get(user=request.user, date=today)
        attendance = {
            'punched_in': att.punch_in is not None,
            'punch_in': att.punch_in,
            'punch_out': att.punch_out,
            'hours_worked': att.hours_worked,
        }
    except Attendance.DoesNotExist:
        attendance = {'punched_in': False}

    data = {
        'role': profile.role,
        'total_tasks': tasks.count(),
        'pending': tasks.filter(status='pending').count(),
        'in_review': tasks.filter(status='in_review').count(),
        'approved': tasks.filter(status='approved').count(),
        'errors': tasks.filter(status='error').count(),
        'attendance': attendance,
    }

    if total_users is not None:
        data['total_users'] = total_users

    return Response(data)


# ── Attendance APIs ───────────────────────────────────────────────────────────

@api_view(['GET'])
def api_attendance(request):
    profile = request.user.profile
    if profile.role in ['admin', 'hr']:
        records = Attendance.objects.all().order_by('-date')[:100]
    else:
        records = Attendance.objects.filter(user=request.user).order_by('-date')
    serializer = AttendanceSerializer(records, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def api_punch_in(request):
    today = timezone.localdate()
    att, _ = Attendance.objects.get_or_create(user=request.user, date=today)
    if not att.punch_in:
        att.punch_in = timezone.now()
        att.save()
        return Response({'message': f'Punched in at {att.punch_in.strftime("%I:%M %p")}', 'punch_in': att.punch_in})
    return Response({'error': 'Already punched in today'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def api_punch_out(request):
    today = timezone.localdate()
    try:
        att = Attendance.objects.get(user=request.user, date=today)
        if att.punch_in and not att.punch_out:
            att.punch_out = timezone.now()
            att.save()
            return Response({'message': f'Punched out. Hours worked: {att.hours_worked}h', 'hours_worked': att.hours_worked})
        return Response({'error': 'Not punched in or already punched out'}, status=status.HTTP_400_BAD_REQUEST)
    except Attendance.DoesNotExist:
        return Response({'error': 'Punch in first'}, status=status.HTTP_400_BAD_REQUEST)
