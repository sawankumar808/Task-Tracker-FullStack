from django.contrib import admin
from .models import UserProfile, Task, TaskError, Attendance

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'team_leader']
    list_filter = ['role']
    search_fields = ['user__username', 'user__first_name']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'assigned_to', 'assigned_by', 'status', 'priority', 'due_date', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['title', 'assigned_to__username']

@admin.register(TaskError)
class TaskErrorAdmin(admin.ModelAdmin):
    list_display = ['task', 'reported_by', 'created_at']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'punch_in', 'punch_out']
    list_filter = ['date']
