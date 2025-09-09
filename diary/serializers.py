from psycopg2._psycopg import IntegrityError
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import ValidationError
from datetime import date, timedelta
import re
from .models import UserRole, SchoolGroup, Subject, Lesson, Assignment, Grade, StudentSubjectAverage

User = get_user_model()


# ==================== ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ====================
class UUIDField(serializers.Field):
    """Кастомное поле для UUID"""

    def to_representation(self, value):
        return str(value)

    def to_internal_value(self, data):
        import uuid
        try:
            return uuid.UUID(str(data))
        except (ValueError, TypeError):
            raise serializers.ValidationError("Неверный формат UUID")


# ==================== ПОЛЬЗОВАТЕЛИ ====================
class UserSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'birth_date', 'age', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_email(self, value):
        """Валидация email"""
        if self.instance and User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        elif not self.instance and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")

        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise serializers.ValidationError("Неверный формат email")
        return value

    def validate_phone_number(self, value):
        """Валидация номера телефона"""
        if value and not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError("Неверный формат номера телефона")
        return value

    def validate_birth_date(self, value):
        """Валидация даты рождения"""
        if value:
            if value > date.today():
                raise serializers.ValidationError("Дата рождения не может быть в будущем")

            age = date.today().year - value.year
            if age < 6:
                raise serializers.ValidationError("Пользователь должен быть старше 6 лет")
            if age > 100:
                raise serializers.ValidationError("Проверьте дату рождения")
        return value



class UserCreateSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['password', 'password_confirm']

    def validate(self, attrs):
        """Валидация паролей"""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)

        if password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают"})

        if len(password) < 8:
            raise serializers.ValidationError({"password": "Пароль должен содержать минимум 8 символов"})

        return attrs

    def create(self, validated_data):
        """Создание пользователя с хешированием пароля"""
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ==================== РОЛИ ====================
class UserRoleSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    role_type_display = serializers.CharField(source='get_role_type_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = UserRole
        fields = ['id', 'user', 'user_name', 'role_type', 'role_type_display', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """Проверка что пользователь не имеет дубликатов ролей"""
        user = attrs.get('user') or self.instance.user if self.instance else None
        role_type = attrs.get('role_type')

        if user and role_type:
            existing_role = UserRole.objects.filter(user=user, role_type=role_type)
            if self.instance:
                existing_role = existing_role.exclude(pk=self.instance.pk)

            if existing_role.exists():
                raise serializers.ValidationError(
                    {"role_type": f"Пользователь уже имеет роль '{role_type}'"}
                )

        return attrs


# ==================== ГРУППЫ (КЛАССЫ) ====================
class SchoolGroupSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    students_count = serializers.IntegerField(source='get_students_count', read_only=True)

    class Meta:
        model = SchoolGroup
        fields = [
            'id', 'name', 'teacher', 'teacher_name', 'students',
            'students_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Валидация названия класса"""
        if not re.match(r'^[1-9][0-9]?[А-ЯЁA-Z]$', value.upper()):
            raise serializers.ValidationError("Название класса должно быть в формате: '1А', '10Б' и т.д.")

        # Проверка уникальности (case insensitive)
        qs = SchoolGroup.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Класс с таким названием уже существует")

        return value.upper()  # Сохраняем в верхнем регистре

    def validate_teacher(self, value):
        """Проверка, что учитель имеет соответствующую роль"""
        if value and not value.roles.filter(role_type='teacher', is_active=True).exists():
            raise serializers.ValidationError("Выбранный пользователь не является учителем")
        return value

    def validate_students(self, value):
        """Проверка, что все студенты имеют соответствующую роль"""
        for student in value:
            if not student.roles.filter(role_type__in=['student', 'temp_student'], is_active=True).exists():
                raise serializers.ValidationError(
                    f"Пользователь {student.get_full_name()} не является учеником"
                )
        return value


# ==================== ПРЕДМЕТЫ ====================
class SubjectSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'short_name', 'full_name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_short_name(self, value):
        """Валидация короткого названия"""
        if len(value) > 20:
            raise serializers.ValidationError("Сокращенное название не должно превышать 20 символов")

        # Проверка уникальности
        qs = Subject.objects.filter(short_name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Предмет с таким сокращенным названием уже существует")

        return value

    def validate_full_name(self, value):
        """Валидация полного названия"""
        if len(value) > 100:
            raise serializers.ValidationError("Полное название не должно превышать 100 символов")

        # Проверка уникальности
        qs = Subject.objects.filter(full_name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Предмет с таким полным названием уже существует")

        return value


# ==================== УРОКИ ====================
class LessonSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    subject_name = serializers.CharField(source='subject.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'date', 'group', 'group_name', 'subject', 'subject_name',
            'teacher', 'teacher_name', 'topic', 'homework', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_date(self, value):
        """Валидация даты урока"""
        if value > date.today() + timedelta(days=365):
            raise serializers.ValidationError("Урок не может быть запланирован более чем на год вперед")
        if value < date.today() - timedelta(days=365):
            raise serializers.ValidationError("Урок не может быть старше года")
        return value

    def validate_teacher(self, value):
        """Проверка что учитель ведет этот предмет"""
        if value and not value.roles.filter(role_type='teacher', is_active=True).exists():
            raise serializers.ValidationError("Выбранный пользователь не является учителем")
        return value

    def validate(self, attrs):
        """Проверка что учитель и группа соответствуют"""
        teacher = attrs.get('teacher')
        group = attrs.get('group')

        if teacher and group and group.teacher != teacher:
            raise serializers.ValidationError(
                {"teacher": "Выбранный учитель не является классным руководителем этой группы"}
            )

        return attrs


# ==================== ЗАДАНИЯ ====================
class AssignmentSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    assignment_type_display = serializers.CharField(source='get_assignment_type_display', read_only=True)
    lesson_info = serializers.CharField(source='lesson.__str__', read_only=True)
    max_score = serializers.IntegerField(min_value=1, max_value=100)

    class Meta:
        model = Assignment
        fields = [
            'id', 'lesson', 'lesson_info', 'title', 'assignment_type',
            'assignment_type_display', 'description', 'max_score',
            'due_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_due_date(self, value):
        """Валидация срока выполнения"""
        if value:
            lesson_date = self.instance.lesson.date if self.instance else None
            if lesson_date and value.date() < lesson_date:
                raise serializers.ValidationError("Срок выполнения не может быть раньше даты урока")
        return value

    def validate_title(self, value):
        """Валидация названия задания"""
        if len(value) < 5:
            raise serializers.ValidationError("Название задания должно содержать минимум 5 символов")
        if len(value) > 200:
            raise serializers.ValidationError("Название задания не должно превышать 200 символов")
        return value


# ==================== ОЦЕНКИ ====================
class GradeSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    subject_name = serializers.CharField(source='assignment.lesson.subject.full_name', read_only=True)
    max_score = serializers.IntegerField(source='assignment.max_score', read_only=True)

    class Meta:
        model = Grade
        fields = [
            'id', 'assignment', 'assignment_title', 'student', 'student_name',
            'subject_name', 'score', 'max_score', 'comment', 'graded_at', 'created_at'
        ]
        read_only_fields = ['id', 'graded_at', 'created_at']

    def validate_score(self, value):
        """Валидация оценки"""
        assignment = self.context.get('assignment') or (self.instance.assignment if self.instance else None)

        if assignment and value > assignment.max_score:
            raise serializers.ValidationError(
                f"Оценка не может превышать максимальный балл задания ({assignment.max_score})"
            )

        if value < 0:
            raise serializers.ValidationError("Оценка не может быть отрицательной")

        return value

    def validate(self, attrs):
        """Проверка что студент относится к группе урока"""
        assignment = attrs.get('assignment') or self.instance.assignment
        student = attrs.get('student') or self.instance.student

        if assignment and student:
            lesson_group = assignment.lesson.group
            if student not in lesson_group.students.all():
                raise serializers.ValidationError(
                    {"student": "Ученик не принадлежит к группе этого урока"}
                )

        return attrs


# ==================== СРЕДНИЕ БАЛЛЫ ====================
class StudentSubjectAverageSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.full_name', read_only=True)

    class Meta:
        model = StudentSubjectAverage
        fields = [
            'id', 'student', 'student_name', 'subject', 'subject_name',
            'average_score', 'total_grades', 'last_updated', 'created_at'
        ]
        read_only_fields = ['id', 'average_score', 'total_grades', 'last_updated', 'created_at']

    def validate_average_score(self, value):
        """Валидация среднего балла"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Средний балл должен быть между 0 и 100")
        return round(value, 2)