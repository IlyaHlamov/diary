from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import CustomTokenObtainPairView, CustomTokenRefreshView, CustomTokenVerifyView

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
router.register(r'password-reset', views.PasswordResetViewSet, basename='password-reset')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),

    path('password-reset/request_reset/',views.PasswordResetViewSet.as_view({'post': 'request_reset'}),name='password-reset-request'),
    path('password-reset/verify_code/',views.PasswordResetViewSet.as_view({'post': 'verify_code'}),name='password-reset-verify'),

    # Дополнительные endpoints
    path('users/<uuid:pk>/grades/', views.UserGradesView.as_view(), name='user-grades'),
    path('users/<uuid:pk>/averages/', views.UserAveragesView.as_view(), name='user-averages'),

    # JWT endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
]