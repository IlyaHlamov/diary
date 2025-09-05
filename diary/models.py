from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
import datetime
from uuid6 import uuid7


class UUIDField(models.UUIDField):
    def __init__(self, *args, **kwargs):
        kwargs['default'] = uuid7
        kwargs['editable'] = False
        super().__init__(*args, **kwargs)

class BaseModel(models.Model):
    id = UUIDField(primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# пользователи
class User(AbstractUser, BaseModel):
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,12}$',message="формат: '+999999999'. До 12 цифр.")

    email = models.EmailField(unique=True, verbose_name='Электронная почта')
    first_name = models.CharField(max_length=50, verbose_name='Имя')
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')
    phone_number = models.CharField(validators=[phone_regex],max_length=13,blank=True,verbose_name='Номер телефона')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')

    # Убираем стандартные поля groups и user_permissions
    groups = None
    user_permissions = None

    class Meta:
        swappable = 'AUTH_USER_MODEL'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def age(self):
        if self.birth_date:
            return timezone.now().year - self.birth_date.year
        return None


# роли
class RoleType(models.TextChoices):
    TEACHER = 'teacher', 'Учитель'
    STUDENT = 'student', 'Ученик'
    TEMP_STUDENT = 'temp_student', 'Временный ученик'
    DIRECTOR = 'director', 'Директор'


class UserRole(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='roles',
        verbose_name='Пользователь'
    )
    role_type = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        verbose_name='Тип роли'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Роль пользователя'
        verbose_name_plural = 'Роли пользователей'
        unique_together = ['user', 'role_type']

    def __str__(self):
        return f"{self.user} - {self.get_role_type_display()}"


# классы
class SchoolGroup(BaseModel):
    name = models.CharField(max_length=10, unique=True, verbose_name='Название класса')
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_groups',
        verbose_name='Классный руководитель'
    )
    students = models.ManyToManyField(
        User,
        related_name='student_groups',
        blank=True,
        verbose_name='Ученики'
    )

    class Meta:
        verbose_name = 'Класс'
        verbose_name_plural = 'Классы'

    def __str__(self):
        return self.name

    def get_students_count(self):
        return self.students.count()

    get_students_count.short_description = 'Количество учеников'


# предметы
class Subject(BaseModel):
    short_name = models.CharField(max_length=20, verbose_name='Сокращенное название')
    full_name = models.CharField(max_length=100, verbose_name='Полное название')
    description = models.TextField(blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['full_name']

    def __str__(self):
        return f"{self.short_name} - {self.full_name}"


# уроки
class Lesson(BaseModel):
    date = models.DateField(verbose_name='Дата урока')
    group = models.ForeignKey(
        SchoolGroup,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Класс'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Предмет'
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Учитель'
    )
    topic = models.CharField(max_length=200, blank=True, verbose_name='Тема урока')
    homework = models.TextField(blank=True, verbose_name='Домашнее задание')

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['-date', 'group']

    def __str__(self):
        return f"{self.date} - {self.group} - {self.subject}"


# задания
class AssignmentType(models.TextChoices):
    HOMEWORK = 'homework', 'Домашняя работа'
    TEST = 'test', 'Контрольная работа'
    INDEPENDENT = 'independent', 'Самостоятельная работа'
    CLASSWORK = 'classwork', 'Классная работа'


class Assignment(BaseModel):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='Урок'
    )
    title = models.CharField(max_length=200, verbose_name='Название задания')
    assignment_type = models.CharField(
        max_length=20,
        choices=AssignmentType.choices,
        verbose_name='Тип задания'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    max_score = models.PositiveIntegerField(default=5, verbose_name='Максимальный балл')
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='Срок выполнения')

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'
        ordering = ['-lesson__date', 'title']

    def __str__(self):
        return f"{self.title} - {self.lesson}"


# оценки
class Grade(BaseModel):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name='Задание'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name='Ученик'
    )
    score = models.PositiveIntegerField(verbose_name='Балл')
    comment = models.TextField(blank=True, verbose_name='Комментарий учителя')
    graded_at = models.DateTimeField(auto_now=True, verbose_name='Время оценки')

    class Meta:
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'
        unique_together = ['assignment', 'student']
        ordering = ['-graded_at']

    def __str__(self):
        return f"{self.student} - {self.assignment}: {self.score}"

    def save(self, *args, **kwargs):
        if self.score > self.assignment.max_score:
            self.score = self.assignment.max_score
        super().save(*args, **kwargs)
