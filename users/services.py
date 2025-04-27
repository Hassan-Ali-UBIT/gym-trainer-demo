import random
import requests

from user_agents import parse as parse_user_agent

from datetime import timedelta

from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator

from common.exception_utils import CustomAPIException

from .models import (
    Role, User, UserProfile, OTP,
)

class RoleService:

    @staticmethod
    def get_admin_role():
        admin_role, created = Role.objects.get_or_create(
            name="admin", 
            defaults={"name": "admin"}
        )
        return admin_role
    
    @staticmethod
    def get_user_role():
        user_role, created = Role.objects.get_or_create(
            name="user", 
            defaults={"name": "user"}
        )
        return user_role
    
    @staticmethod
    def get_trainer_role():
        trainer_role, created = Role.objects.get_or_create(
            name="trainer", 
            defaults={"name": "trainer"}
        )
        return trainer_role

class UserService:

    @staticmethod
    def register_user(email, password, full_name, role):
        try:
            with transaction.atomic():
            # Create the user
                user = User.objects.create_user(email=email, username=full_name, password=password, is_active=False)
                
                # Create UserProfile
                UserProfile.objects.create(user=user, full_name=full_name, role=role)

                otp_type = "sign_up"
                otp_code, otp_minutes = OTPService.create_otp(user, otp_type)
                EmailService.send_register_mail(user.email, otp_code, otp_minutes)

                return user

        except Exception as e:
            raise CustomAPIException(message="An error occurred during registration", status_code=500, data=str(e))

    @staticmethod    
    def create_inactive_user(email, full_name, profile_data):
        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': full_name,
                'email': email,
                'password': make_password(None),
                'is_active': False,
            }
        )

        user_role = RoleService.get_user_role()

        user_profile, profile_created = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": user_role,
                **profile_data
            }
        )

        return user, user_profile


    @staticmethod
    def update_user(instance, validated_data):
        from .serializers import UserProfileSerializer

        try:
            # Extract profile data
            with transaction.atomic():
                profile_data = validated_data.pop('userprofile', None)

                # Update the user fields (email, etc.)
                instance.email = validated_data.get('email', instance.email)
                instance.save()

                # If profile data exists, update or create the UserProfile
                if profile_data:
                    profile_serializer = UserProfileSerializer(instance.userprofile, data=profile_data, partial=True)

                    if not profile_serializer.is_valid():
                        raise CustomAPIException(f"Error updating user: {str(e)}", status_code=400)
                    
                    profile_serializer.save()

                return instance

        except Exception as e:
            raise CustomAPIException(f"Error updating user: {str(e)}", status_code=500)

    @staticmethod
    def generate_password_reset_token(user):
        token = default_token_generator.make_token(user)
        return token
    
    @staticmethod
    def validate_password_reset_token(user, token):
        if not default_token_generator.check_token(user, token):
            raise CustomAPIException("Invalid or expired token.")

class OTPService:
    OTP_EXPIRY_MINUTES = 5

    @staticmethod
    def generate_otp():
        return random.randint(100000, 999999)

    @staticmethod
    def create_otp(user, otp_type: str):
        # Invalidate existing unused OTPs of the same type
        OTP.objects.filter(user=user, type=otp_type, used=False).delete()

        otp_code = OTPService.generate_otp()
        expire_time = timezone.now() + timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES)

        OTP.objects.create(
            user=user,
            otp=otp_code,
            type=otp_type,
            expire_at=expire_time
        )

        return (otp_code, OTPService.OTP_EXPIRY_MINUTES)
    
    @staticmethod
    def validate_otp(email: str, otp: int):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CustomAPIException("User not found")

        otp_instance = OTP.objects.filter(
            user=user, otp=otp, used=False
        ).last()

        if not otp_instance:
            raise CustomAPIException("Invalid OTP")
        if otp_instance.expire_at < timezone.now():
            raise CustomAPIException("OTP expired")

        otp_instance.used = True
        otp_instance.save()
        return user, otp_instance.type

class EmailService:
    @staticmethod
    def send_otp_email(to_email, otp, expire_minutes):
        subject = 'Your OTP Code'
        message = f'Your One-Time Password (OTP) is: {otp}. It will expire in {expire_minutes} minutes.'
        from_email = settings.DEFAULT_FROM_EMAIL

        try:
            send_mail(subject, message, from_email, [to_email])
        except Exception as e:
            raise CustomAPIException("Failed to send OTP email. Please try again.")

    @staticmethod
    def send_register_mail(to_email, otp, expire_minutes):
        subject = 'Welcome to Gym Trainer'
        message = f'Your One-Time Password (OTP) is: {otp}. It will expire in {expire_minutes} minutes.'
        from_email = settings.DEFAULT_FROM_EMAIL
        html_message = render_to_string("users/register_email.html", context={"otp_code": otp})
        image_list = [('gym-logo.webp', 'image1')]

        EmailService.send_mail_with_image_file(
            subject, message, from_email,
            to_email, html_message, image_list
        )

    @staticmethod
    def send_forget_password_mail(to_email, otp, expire_minutes):
        subject = 'Forget Password @Gym Trainer'
        message = f'Your One-Time Password (OTP) is: {otp}. It will expire in {expire_minutes} minutes.'
        from_email = settings.DEFAULT_FROM_EMAIL
        html_message = render_to_string("users/forget_password_email.html", context={"otp_code": otp})
        image_list = [('gym-logo.webp', 'image1')]

        EmailService.send_mail_with_image_file(
            subject, message, from_email,
            to_email, html_message, image_list
        )

    @staticmethod
    def send_mail_with_image_file(subject, message, from_email,
                                to_email, html_message, image_list, 
                                document_list=[]):
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=message,  # Plain-text fallback
            from_email=from_email,
            to=[to_email]
        )

        msg.attach_alternative(html_message, "text/html")

        for image_filename, image_cid in image_list:
            image_path = finders.find(image_filename)
            if image_path:  # Check if image exists
                with open(image_path, 'rb') as fp:
                    image = MIMEImage(fp.read())
                    image.add_header('Content-ID', f'<{image_cid}>')
                    image.add_header('Content-Disposition', 'inline', filename=image_filename)
                    msg.attach(image)

        for document_filename in document_list:
            document_path = finders.find(document_filename)
            if document_path:
                with open(document_path, 'rb') as f:
                    doc = MIMEApplication(f.read())
                    doc.add_header('Content-Disposition', 'attachment', filename=document_filename)
                    msg.attach(doc)

        msg.send()

class LoginService:
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def get_device_info(request):
        user_agent = parse_user_agent(request.META.get('HTTP_USER_AGENT', ''))
        device = f"{user_agent.browser.family} on {user_agent.os.family}"
        return device
    
    @staticmethod
    def get_location(ip):
        try:
            response = requests.get(f'https://ipapi.co/{ip}/json/')
            data = response.json()
            print("data =========== ", data)
            return f"{data.get('city')}, {data.get('country_name')}"
        except:
            return "Unknown Location"
        
    @staticmethod
    def get_login_info(request):
        ip = LoginService.get_client_ip(request)
        device = LoginService.get_device_info(request)
        login_time = timezone.localtime().strftime("%B %d, %Y - %I:%M %p")

        return {
            "ip": ip,
            "device": device,
            "login_time": login_time
        }




