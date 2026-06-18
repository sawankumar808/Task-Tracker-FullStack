from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Project, Task, TaskError, Attendance


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'full_name', 'role']


class ProjectSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.get_full_name', read_only=True)
    members = UserSerializer(many=True, read_only=True)
    total_tasks = serializers.ReadOnlyField()
    completed_tasks = serializers.ReadOnlyField()
    progress = serializers.ReadOnlyField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'created_by',
                  'members', 'due_date', 'created_at', 'total_tasks',
                  'completed_tasks', 'progress']
        read_only_fields = ['created_by', 'created_at']


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'priority',
                  'assigned_to', 'assigned_to_name', 'assigned_by_name',
                  'project', 'project_name', 'due_date', 'submission_note',
                  'grammar_checked', 'created_at', 'updated_at']
        read_only_fields = ['assigned_by', 'created_at', 'updated_at']


class TaskErrorSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.CharField(source='reported_by.get_full_name', read_only=True)

    class Meta:
        model = TaskError
        fields = ['id', 'task', 'error_message', 'reported_by_name', 'created_at']


class AttendanceSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.get_full_name', read_only=True)
    hours_worked = serializers.ReadOnlyField()

    class Meta:
        model = Attendance
        fields = ['id', 'username', 'date', 'punch_in', 'punch_out', 'hours_worked']


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user
