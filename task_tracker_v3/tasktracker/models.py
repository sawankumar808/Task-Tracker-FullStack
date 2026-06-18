from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('team_leader', 'Team Leader'),
        ('hr', 'HR'),
        ('employee', 'Employee'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    team_leader = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='team_members'
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"

    def is_admin(self): return self.role == 'admin'
    def is_team_leader(self): return self.role == 'team_leader'
    def is_hr(self): return self.role == 'hr'
    def is_employee(self): return self.role == 'employee'


class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(User, related_name='projects', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def total_tasks(self):
        return self.tasks.count()

    @property
    def completed_tasks(self):
        return self.tasks.filter(status='approved').count()

    @property
    def progress(self):
        total = self.total_tasks
        if total == 0:
            return 0
        return round((self.completed_tasks / total) * 100)


class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('error', 'Error Flagged'),
    ]
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submission_note = models.TextField(blank=True)
    grammar_checked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} [{self.status}]"


class TaskError(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='errors')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Error: {self.task.title}"


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField(default=timezone.now)
    punch_in = models.DateTimeField(null=True, blank=True)
    punch_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'date')

    @property
    def hours_worked(self):
        if self.punch_in and self.punch_out:
            delta = self.punch_out - self.punch_in
            return round(delta.total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"{self.user.username} - {self.date}"
