"""Modelos da app de Autenticação - usando User do Django."""

from uuid import uuid4
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from shared.utils.crypto import decrypt_password, encrypt_password

# Usamos o modelo User padrão do Django
# Sem modelos adicionais necessários nesta app


class GmailSender(models.Model):
	"""Remetente de Gmail por usuário."""

	id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='gmail_senders'
	)
	sender_email = models.EmailField()
	app_password_encrypted = models.TextField(blank=True, default='')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = [('user', 'sender_email')]
		ordering = ['-created_at']

	def __str__(self):
		return f"GmailSender({self.sender_email})"

	def set_app_password(self, plain_password: str):
		if not plain_password:
			self.app_password_encrypted = ''
			return
		self.app_password_encrypted = encrypt_password(plain_password)

	def get_app_password(self) -> str:
		if not self.app_password_encrypted:
			return ''
		return decrypt_password(self.app_password_encrypted)


class GmailTemplate(models.Model):
	"""Template de mensagem vinculado ao remetente Gmail."""

	id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
	sender = models.ForeignKey(
		GmailSender,
		on_delete=models.CASCADE,
		related_name='templates'
	)
	title = models.CharField(max_length=120)
	subject = models.CharField(max_length=255)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = [('sender', 'title')]
		ordering = ['title']

	def __str__(self):
		return f"GmailTemplate({self.title})"


class WhatsAppSender(models.Model):
	"""Remetente de WhatsApp por usuário."""

	id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='whatsapp_senders'
	)
	phone_number = models.CharField(max_length=30)
	access_token_encrypted = models.TextField(blank=True, default='')
	phone_number_id = models.CharField(max_length=120)
	business_id = models.CharField(max_length=120)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"WhatsAppSender({self.phone_number})"

	def set_access_token(self, plain_token: str):
		if not plain_token:
			self.access_token_encrypted = ''
			return
		self.access_token_encrypted = encrypt_password(plain_token)

	def get_access_token(self) -> str:
		if not self.access_token_encrypted:
			return ''
		return decrypt_password(self.access_token_encrypted)


class WhatsAppTemplate(models.Model):
	"""Template de mensagem vinculado ao remetente de WhatsApp."""

	id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
	sender = models.ForeignKey(
		WhatsAppSender,
		on_delete=models.CASCADE,
		related_name='templates'
	)
	title = models.CharField(max_length=120)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = [('sender', 'title')]
		ordering = ['title']

	def __str__(self):
		return f"WhatsAppTemplate({self.title})"
