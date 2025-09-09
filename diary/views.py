from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count
from .models import UserRole, SchoolGroup, Subject, Lesson, Assignment, Grade, StudentSubjectAverage
from .serializers import (
    UserSerializer, UserCreateSerializer, UserRoleSerializer, SchoolGroupSerializer,
    SubjectSerializer, LessonSerializer, AssignmentSerializer, GradeSerializer,
    StudentSubjectAverageSerializer
)

User = get_user_model()


# ==================== ПОЛЬЗОВАТЕЛИ ====================
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def teachers(self, request):
        """Получить всех учителей"""
        teachers = User.objects.filter(roles__role_type='teacher', roles__is_active=True).distinct()
        serializer = self.get_serializer(teachers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def students(self, request):
        """Получить всех учеников"""
        students = User.objects.filter(
            Q(roles__role_type='student') | Q(roles__role_type='temp_student'),
            roles__is_active=True
        ).distinct()
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data)


# ==================== РОЛИ ====================
class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.all().order_by('-created_at')
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Фильтрация по пользователю если передан user_id"""
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset


# ==================== ГРУППЫ ====================
class SchoolGroupViewSet(viewsets.ModelViewSet):
    queryset = SchoolGroup.objects.all().order_by('name')
    serializer_class = SchoolGroupSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Статистика по группе"""
        group = self.get_object()
        students_count = group.students.count()
        lessons_count = group.lessons.count()

        return Response({
            'students_count': students_count,
            'lessons_count': lessons_count,
            'teacher': group.teacher.get_full_name() if group.teacher else None
        })


# ==================== ПРЕДМЕТЫ ====================
class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by('full_name')
    serializer_class = SubjectSerializer
    permission_classes = [permissions.AllowAny]


# ==================== УРОКИ ====================
class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all().order_by('-date')
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Фильтрация уроков по группе, предмету или учителю"""
        queryset = super().get_queryset()

        group_id = self.request.query_params.get('group_id')
        subject_id = self.request.query_params.get('subject_id')
        teacher_id = self.request.query_params.get('teacher_id')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if group_id:
            queryset = queryset.filter(group_id=group_id)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """Получить все задания урока"""
        lesson = self.get_object()
        assignments = lesson.assignments.all()
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)


# ==================== ЗАДАНИЯ ====================
class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all().order_by('-created_at')
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Фильтрация заданий по уроку или типу"""
        queryset = super().get_queryset()

        lesson_id = self.request.query_params.get('lesson_id')
        assignment_type = self.request.query_params.get('type')

        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        if assignment_type:
            queryset = queryset.filter(assignment_type=assignment_type)

        return queryset

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        """Получить все оценки задания"""
        assignment = self.get_object()
        grades = assignment.grades.all()
        serializer = GradeSerializer(grades, many=True)
        return Response(serializer.data)


# ==================== ОЦЕНКИ ====================
class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all().order_by('-graded_at')
    serializer_class = GradeSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Фильтрация оценок по студенту, заданию или предмету"""
        queryset = super().get_queryset()

        student_id = self.request.query_params.get('student_id')
        assignment_id = self.request.query_params.get('assignment_id')
        subject_id = self.request.query_params.get('subject_id')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if assignment_id:
            queryset = queryset.filter(assignment_id=assignment_id)
        if subject_id:
            queryset = queryset.filter(assignment__lesson__subject_id=subject_id)

        return queryset


# ==================== СРЕДНИЕ БАЛЛЫ ====================
class StudentSubjectAverageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StudentSubjectAverage.objects.all().order_by('-average_score')
    serializer_class = StudentSubjectAverageSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Фильтрация по студенту или предмету"""
        queryset = super().get_queryset()

        student_id = self.request.query_params.get('student_id')
        subject_id = self.request.query_params.get('subject_id')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        return queryset


# ==================== СТАТИСТИКА ====================
class StatisticsView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Общая статистика системы"""
        total_users = User.objects.count()
        total_students = User.objects.filter(roles__role_type__in=['student', 'temp_student']).distinct().count()
        total_teachers = User.objects.filter(roles__role_type='teacher').distinct().count()
        total_groups = SchoolGroup.objects.count()
        total_lessons = Lesson.objects.count()
        total_assignments = Assignment.objects.count()

        return Response({
            'total_users': total_users,
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_groups': total_groups,
            'total_lessons': total_lessons,
            'total_assignments': total_assignments,
        })


# ==================== ДОПОЛНИТЕЛЬНЫЕ ВЬЮШКИ ====================
class UserGradesView(generics.ListAPIView):
    """Все оценки конкретного пользователя"""
    serializer_class = GradeSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['pk']
        return Grade.objects.filter(student_id=user_id).order_by('-graded_at')


class UserAveragesView(generics.ListAPIView):
    """Все средние баллы конкретного пользователя"""
    serializer_class = StudentSubjectAverageSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['pk']
        return StudentSubjectAverage.objects.filter(student_id=user_id).order_by('-average_score')


class GroupLessonsView(generics.ListAPIView):
    """Все уроки конкретной группы"""
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        group_id = self.kwargs['pk']
        return Lesson.objects.filter(group_id=group_id).order_by('-date')


class TeacherLessonsView(generics.ListAPIView):
    """Все уроки конкретного учителя"""
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['pk']
        return Lesson.objects.filter(teacher_id=teacher_id).order_by('-date')