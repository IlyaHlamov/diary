from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Grade, StudentSubjectAverage

@receiver(post_save, sender=Grade)
@receiver(post_delete, sender=Grade)
def update_student_average(sender, instance, **kwargs):
    """
    Автоматически обновляет средний балл ученика по предмету
    при создании, изменении или удалении оценки
    """
    try:
        StudentSubjectAverage.update_average(
            instance.student,
            instance.assignment.lesson.subject
        )
    except Exception as e:
        # Обработка ошибок (например, если связь не установлена)
        print(f"Error updating average: {e}")