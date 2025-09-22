
# Create your views here.

# projects/views.py

from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import F
from .models import Project

class ProjectListView(ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 12
    
    def get_queryset(self):
        return Project.objects.filter(is_published=True).order_by('-is_featured', '-created_at')

class ProjectDetailView(DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def get_object(self):
        obj = get_object_or_404(Project, slug=self.kwargs['slug'], is_published=True)
        Project.objects.filter(pk=obj.pk).update(views_count=F('views_count') + 1)
        return obj
class ProjectDetailView(DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Project.objects.filter(is_published=True).prefetch_related('technologies')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get related projects (same category, excluding current)
        if hasattr(self.object, 'category'):
            context['related_projects'] = Project.objects.filter(
                category=self.object.category,
                is_published=True
            ).exclude(id=self.object.id)[:3]
        return context
