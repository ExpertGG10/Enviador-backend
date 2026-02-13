"""
Django Admin configuration para models de email.
"""
from django.contrib import admin
from .models import Sender, Recipient, RecipientGroup, EmailLog


@admin.register(Sender)
class SenderAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_active', 'is_default', 'user', 'created_at')
    list_filter = ('is_active', 'is_default', 'created_at')
    search_fields = ('email', 'name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'email', 'name')
        }),
        ('Status', {
            'fields': ('is_active', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'user', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('email', 'name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'email', 'name')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RecipientGroup)
class RecipientGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'recipient_count', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('recipients',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'name')
        }),
        ('Contatos', {
            'fields': ('recipients',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def recipient_count(self, obj):
        return obj.recipients.count()
    recipient_count.short_description = 'Contatos'


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'subject', 'status', 'sender', 'attempts', 'sent_at')
    list_filter = ('status', 'created_at', 'sender')
    search_fields = ('recipient_email', 'subject', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'sender', 'recipient_email', 'subject')
        }),
        ('Status', {
            'fields': ('status', 'attempts', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
