from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from tasktracker.models import UserProfile, Project, Task, TaskError, Attendance


class Command(BaseCommand):
    help = 'Creates demo users, projects, tasks, and attendance'

    def handle(self, *args, **kwargs):
        if User.objects.filter(username='admin_demo').exists():
            self.stdout.write('Demo data already exists! Skipping...')
            return

        self.stdout.write('Setting up demo data...')

        # ── Users ─────────────────────────────────────────────────────────────
        users_data = [
            ('admin_demo',    'admin123',  'Rahul',  'Kumar',  'admin'),
            ('teamlead_demo', 'lead123',   'Priya',  'Sharma', 'team_leader'),
            ('hr_demo',       'hr123',     'Sneha',  'Verma',  'hr'),
            ('emp1_demo',     'emp123',    'Amit',   'Singh',  'employee'),
            ('emp2_demo',     'emp123',    'Neha',   'Gupta',  'employee'),
        ]

        created = {}
        for username, password, first, last, role in users_data:
            u, _ = User.objects.get_or_create(username=username)
            u.set_password(password)
            u.first_name = first
            u.last_name = last
            u.save()
            p, _ = UserProfile.objects.get_or_create(user=u)
            p.role = role
            p.save()
            created[role] = u
            self.stdout.write(f'  ✓ {username} ({role})')

        # Assign employees to TL
        tl_p = UserProfile.objects.get(user=created['team_leader'])
        emp2 = User.objects.get(username='emp2_demo')
        for uname in ['emp1_demo', 'emp2_demo']:
            ep = UserProfile.objects.get(user=User.objects.get(username=uname))
            ep.team_leader = tl_p
            ep.save()

        admin = created['admin']
        tl = created['team_leader']
        emp1 = created['employee']
        today = date.today()

        # ── Projects ──────────────────────────────────────────────────────────
        p1, _ = Project.objects.get_or_create(
            name='E-commerce Website Redesign',
            defaults={
                'description': 'Complete redesign of the company e-commerce platform with modern UI/UX.',
                'created_by': admin,
                'status': 'active',
                'due_date': today + timedelta(days=30),
            }
        )
        p1.members.add(admin, tl, emp1, emp2)

        p2, _ = Project.objects.get_or_create(
            name='Mobile App Development',
            defaults={
                'description': 'Build a cross-platform mobile application for iOS and Android.',
                'created_by': tl,
                'status': 'active',
                'due_date': today + timedelta(days=60),
            }
        )
        p2.members.add(tl, emp1, emp2)

        self.stdout.write('  ✓ Projects created')

        # ── Tasks ─────────────────────────────────────────────────────────────
        tasks_data = [
            ('Fix login page validation bug', 'Fix validation errors on the login form.', emp1, admin, p1, 'error', 'high', today+timedelta(days=1), 'Fixed validation logic in views.py.', True),
            ('Write user onboarding docs', 'Create detailed onboarding guide for new employees.', emp1, tl, p1, 'in_review', 'medium', today+timedelta(days=3), 'Documentation completed with screenshots.', True),
            ('Prepare monthly attendance report', 'Compile attendance data for current month.', emp2, admin, p2, 'approved', 'medium', today-timedelta(days=2), 'Report prepared and verified.', True),
            ('Update employee records', 'Review and update all employee profile information.', emp2, tl, p2, 'pending', 'low', today+timedelta(days=5), '', False),
            ('Design dashboard UI mockup', 'Create wireframes for the new dashboard.', emp1, admin, p1, 'pending', 'high', today+timedelta(days=2), '', False),
            ('Test payment gateway', 'End-to-end testing of payment gateway.', emp2, tl, p2, 'in_review', 'high', today+timedelta(days=1), 'All test cases executed. 2 minor issues found.', True),
        ]

        for title, desc, ato, aby, proj, st, priority, due, note, gc in tasks_data:
            t, _ = Task.objects.get_or_create(
                title=title,
                defaults={
                    'description': desc, 'assigned_to': ato, 'assigned_by': aby,
                    'project': proj, 'status': st, 'priority': priority,
                    'due_date': due, 'submission_note': note, 'grammar_checked': gc,
                }
            )
            self.stdout.write(f'  ✓ Task: {title[:40]} [{st}]')

        # Error report
        err_task = Task.objects.get(title='Fix login page validation bug')
        TaskError.objects.get_or_create(
            task=err_task, reported_by=admin,
            defaults={'error_message': 'Fix incomplete. Errors not showing on mobile devices.'}
        )

        # ── Attendance ────────────────────────────────────────────────────────
        all_users = [admin, tl, created['hr'], emp1, emp2]
        for i, u in enumerate(all_users):
            pin = timezone.now().replace(hour=9, minute=i*5, second=0, microsecond=0)
            pout = timezone.now().replace(hour=17, minute=30, second=0, microsecond=0) if i < 3 else None
            Attendance.objects.update_or_create(user=u, date=today, defaults={'punch_in': pin, 'punch_out': pout})
            yesterday = today - timedelta(days=1)
            Attendance.objects.update_or_create(
                user=u, date=yesterday,
                defaults={'punch_in': pin-timedelta(days=1), 'punch_out': (pout-timedelta(days=1)) if pout else None}
            )

        self.stdout.write(self.style.SUCCESS('''
╔══════════════════════════════════════════════════════╗
║           DEMO SETUP COMPLETE ✓                      ║
╠══════════════════════════════════════════════════════╣
║  Admin:        admin_demo     / admin123             ║
║  Team Leader:  teamlead_demo  / lead123              ║
║  HR:           hr_demo        / hr123                ║
║  Employee 1:   emp1_demo      / emp123               ║
║  Employee 2:   emp2_demo      / emp123               ║
╚══════════════════════════════════════════════════════╝
'''))
