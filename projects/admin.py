
# Register your models here.


# projects/admin.py

from django.contrib import admin
from .models import Project, ProjectParticipant

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'progress', 'is_published', 'participants_count', 'created_at']
    list_filter = ['status', 'is_published', 'is_featured', 'created_at']
    list_editable = ['status', 'is_published', 'progress']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(ProjectParticipant)
class ProjectParticipantAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'email', 'is_approved', 'joined_at']
    list_filter = ['is_approved', 'project', 'joined_at']
    list_editable = ['is_approved']

