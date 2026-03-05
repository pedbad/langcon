from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
import pytest

from assessments.models import Assessment, AssessmentEvaluation
from profiles.models import Profile

User = get_user_model()


@pytest.mark.django_db
def test_students_page_requires_login(client):
    resp = client.get(reverse("assessor:students"))
    assert resp.status_code in (302, 303)


@pytest.mark.django_db
def test_students_page_admin_can_view_all_students(client):
    admin = User.objects.create_user(
        email="admin-students@example.com",
        password="adminpass",
        role="admin",
        is_staff=True,
    )
    s1 = User.objects.create_user(
        email="student1@example.com",
        password="pass1234",
        role="student",
        first_name="One",
        last_name="Student",
    )
    User.objects.create_user(
        email="student2@example.com",
        password="pass1234",
        role="student",
        first_name="Two",
        last_name="Student",
    )
    Profile.objects.create(user=s1, phone="", student_number="300000011")

    client.force_login(admin)
    resp = client.get(reverse("assessor:students"))

    assert resp.status_code == 200
    assert b"All students" in resp.content
    assert b"student1@example.com" in resp.content
    assert b"student2@example.com" in resp.content


@pytest.mark.django_db
def test_students_page_teacher_is_denied(client):
    teacher = User.objects.create_user(
        email="teacher-students@example.com",
        password="teachpass",
        role="teacher",
        is_staff=True,
    )
    client.force_login(teacher)
    resp = client.get(reverse("assessor:students"))
    assert resp.status_code in (302, 303)


@pytest.mark.django_db
def test_students_page_filters_by_year(client):
    admin = User.objects.create_user(
        email="admin-years@example.com",
        password="adminpass",
        role="admin",
        is_staff=True,
    )
    s_old = User.objects.create_user(
        email="oldyear@example.com",
        password="pass1234",
        role="student",
    )
    s_new = User.objects.create_user(
        email="newyear@example.com",
        password="pass1234",
        role="student",
    )

    old_dt = timezone.make_aware(datetime(2025, 1, 10, 9, 0, 0))
    new_dt = timezone.make_aware(datetime(2026, 3, 1, 9, 0, 0))
    User.objects.filter(id=s_old.id).update(date_joined=old_dt)
    User.objects.filter(id=s_new.id).update(date_joined=new_dt)

    client.force_login(admin)
    resp = client.get(reverse("assessor:students"), {"year": "2025"})

    assert resp.status_code == 200
    assert b"oldyear@example.com" in resp.content
    assert b"newyear@example.com" not in resp.content


@pytest.mark.django_db
def test_dashboard_uses_profile_usn_when_evaluation_snapshot_is_blank(client):
    teacher = User.objects.create_user(
        email="teacher-dashboard@example.com",
        password="teachpass",
        role="teacher",
        is_staff=True,
    )
    student = User.objects.create_user(
        email="student-usn@example.com",
        password="pass1234",
        role="student",
        first_name="USN",
        last_name="Fallback",
    )
    Profile.objects.create(user=student, phone="", student_number="300009999")
    assessment = Assessment.objects.create(user=student)
    AssessmentEvaluation.objects.create(
        assessment=assessment,
        student_email=student.email,
        student_usn="",
        submitted_at=timezone.now(),
        completion_duration=timedelta(minutes=10),
    )

    client.force_login(teacher)
    resp = client.get(reverse("assessor:teacher_home"))

    assert resp.status_code == 200
    assert b"300009999" in resp.content
