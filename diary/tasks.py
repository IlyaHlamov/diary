from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


@shared_task
def send_password_reset_email(email, code):
    """Асинхронная отправка email с кодом сброса"""
    subject = '🔐 Сброс пароля - Образовательная система'

    # HTML шаблон письма
    html_message = render_to_string('email/password_reset.html', {
        'code': code,
        'email': email
    })

    # Текстовая версия
    text_message = f'''
    Код для сброса пароля: {code}

    Введите этот код в форме сброса пароля.

    Если вы не запрашивали сброс, проигнорируйте это письмо.
    Код действителен 1 час.
    '''

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"✅ Email отправлен на {email}"
    except Exception as e:
        return f"❌ Ошибка отправки: {str(e)}"