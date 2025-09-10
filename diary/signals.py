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
        print(f"Signal triggered for grade: {instance.id}")  # ← Для отладки

        # Обновляем средний балл
        StudentSubjectAverage.update_average(
            instance.student,
            instance.assignment.lesson.subject
        )

        print(f"Average updated for student: {instance.student.id}, subject: {instance.assignment.lesson.subject.id}")

    except Exception as e:
        print(f"Error in signal: {e}")