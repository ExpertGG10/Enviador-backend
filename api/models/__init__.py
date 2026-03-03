from django.db import models
import uuid


class BackgroundJob(models.Model):
	STATE_CHOICES = [
		('queued', 'Queued'),
		('running', 'Running'),
		('done', 'Done'),
		('error', 'Error'),
	]

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	owner_email = models.EmailField()
	state = models.CharField(max_length=20, choices=STATE_CHOICES, default='queued')
	total = models.IntegerField(default=0)
	processed = models.IntegerField(default=0)
	success = models.IntegerField(default=0)
	failed = models.IntegerField(default=0)
	items = models.JSONField(default=list, blank=True)
	error = models.TextField(null=True, blank=True)
	cancel = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'api'
		db_table = 'api_backgroundjob'
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['owner_email', '-created_at']),
			models.Index(fields=['state', '-updated_at']),
		]

	def __str__(self):
		return f"[{self.state}] {self.id}"
