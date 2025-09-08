from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Регистрируем ViewSets
router.register(r'users', views.UserViewSet)
router.register(r'roles', views.UserRoleViewSet)
router.register(r'groups', views.SchoolGroupViewSet)
router.register(r'subjects', views.SubjectViewSet)
router.register(r'lessons', views.LessonViewSet)
router.register(r'assignments', views.AssignmentViewSet)
router.register(r'grades', views.GradeViewSet)
router.register(r'averages', views.StudentSubjectAverageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),

    # Дополнительные endpoints
    path('users/<uuid:pk>/grades/', views.UserGradesView.as_view(), name='user-grades'),
    path('users/<uuid:pk>/averages/', views.UserAveragesView.as_view(), name='user-averages'),
]