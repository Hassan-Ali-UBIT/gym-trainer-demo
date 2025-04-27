# serializers.py
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from common.exception_utils import CustomAPIException
from common.serializer_utils import get_serialized_or_none

from .models import (
    User, UserProfile, OTP, Role
)
from .services import LoginService, RoleService, UserService, OTPService

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name')

    def create(self, validated_data):
        
        user = UserService.register_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
        )

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email

        if hasattr(user, 'userprofile'):
            token['full_name'] = user.userprofile.full_name

        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)

        # Add extra data to the response body (not just JWT payload)
        data['user'] = {}
        data['user']['id'] = self.user.id
        data['user']['email'] = self.user.email

        if hasattr(self.user, 'userprofile'):
            data['profile'] = {}
            data['profile']['id'] = self.user.userprofile.id
            data['profile']['full_name'] = self.user.userprofile.full_name

        return data

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        return {'user': user}

class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = ('user', 'otp', 'type')

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.IntegerField()

    def validate(self, data):
        user, otp_type = OTPService.validate_otp(
            email=data['email'],
            otp=data['otp'],
        )
        return user, otp_type

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise CustomAPIException("Old password is incorrect")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['user']

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['role'] = get_serialized_or_none(RoleSerializer, instance.role)

        return representation

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(source='userprofile', required=False)

    class Meta:
        model = User
        fields = ('id', 'email', 'created_at', 'updated_at', 'profile')

    def update(self, instance, validated_data):
        # Update the user fields (email, etc.)
        return UserService.update_user(instance, validated_data)

class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField()  
    email = serializers.EmailField()
    new_password = serializers.CharField()

    def validate(self, data):
        try:
            user = User.objects.get(email=data['email'])
            
            UserService.validate_password_reset_token(user, data['reset_token'])
            
            data['user'] = user
            return data
        except User.DoesNotExist:
            raise CustomAPIException("User not found", 404)

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()
