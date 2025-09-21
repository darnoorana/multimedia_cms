# core/permissions.py

from django.contrib.auth.models import Permission, Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.apps import apps
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View
import json
import logging

logger = logging.getLogger(__name__)


class AdvancedPermissionManager:
    """مدير الصلاحيات المتقدم"""
    
    # أدوار النظام الأساسية
    SYSTEM_ROLES = {
        'super_admin': {
            'name': _('المدير العام'),
            'description': _('صلاحيات كاملة على النظام'),
            'permissions': ['*']  # جميع الصلاحيات
        },
        'content_manager': {
            'name': _('مدير المحتوى'),
            'description': _('إدارة المحتوى والوسائط'),
            'permissions': [
                'add_playlist', 'change_playlist', 'delete_playlist', 'view_playlist',
                'add_playlistitem', 'change_playlistitem', 'delete_playlistitem', 'view_playlistitem',
                'add_category', 'change_category', 'view_category',
                'add_comment', 'change_comment', 'delete_comment', 'view_comment',
                'add_tag', 'change_tag', 'delete_tag', 'view_tag',
                'upload_media', 'manage_media', 'publish_content'
            ]
        },
        'blog_editor': {
            'name': _('محرر المدونة'),
            'description': _('كتابة وتحرير مقالات المدونة'),
            'permissions': [
                'add_post', 'change_post', 'view_post',
                'add_category', 'view_category',
                'upload_media', 'publish_content'
            ]
        },
        'moderator': {
            'name': _('مشرف'),
            'description': _('إشراف على التعليقات والمحتوى'),
            'permissions': [
                'view_playlist', 'view_playlistitem',
                'change_comment', 'delete_comment', 'view_comment',
                'view_contactmessage', 'change_contactmessage',
                'moderate_content'
            ]
        },
        'analytics_viewer': {
            'name': _('مطالع التحليلات'),
            'description': _('عرض التقارير والإحصائيات فقط'),
            'permissions': [
                'view_analytics', 'view_reports',
                'view_playlist', 'view_playlistitem',
                'view_user', 'view_statistics'
            ]
        },
        'subscriber': {
            'name': _('مشترك'),
            'description': _('مستخدم عادي مع صلاحيات محدودة'),
            'permissions': [
                'view_playlist', 'view_playlistitem',
                'add_comment', 'change_own_comment'
            ]
        }
    }
    
    # صلاحيات مخصصة إضافية
    CUSTOM_PERMISSIONS = [
        ('upload_media', _('رفع الوسائط')),
        ('manage_media', _('إدارة الوسائط')),
        ('moderate_content', _('إشراف على المحتوى')),
        ('view_analytics', _('عرض التحليلات')),
        ('view_reports', _('عرض التقارير')),
        ('view_statistics', _('عرض الإحصائيات')),
        ('backup_restore', _('النسخ الاحتياطي والاستعادة')),
        ('system_settings', _('إعدادات النظام')),
        ('user_management', _('إدارة المستخدمين')),
        ('bulk_operations', _('العمليات المجمعة')),
        ('export_data', _('تصدير البيانات')),
        ('import_data', _('استيراد البيانات')),
        ('delete_bulk', _('الحذف المجمع')),
        ('publish_content', _('نشر المحتوى')),
        ('schedule_content', _('جدولة المحتوى')),
        ('change_own_comment', _('تعديل التعليق الخاص')),
        ('manage_subscriptions', _('إدارة الاشتراكات')),
        ('send_notifications', _('إرسال الإشعارات')),
        ('manage_themes', _('إدارة الثيمات')),
        ('manage_plugins', _('إدارة الإضافات'))
    ]
    
    @classmethod
    def create_custom_permissions(cls):
        """إنشاء الصلاحيات المخصصة"""
        content_type = ContentType.objects.get_for_model(User)
        
        created_permissions = []
        for codename, name in cls.CUSTOM_PERMISSIONS:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name}
            )
            if created:
                created_permissions.append(permission)
                logger.info(f'تم إنشاء صلاحية مخصصة: {name}')
        
        return created_permissions
    
    @classmethod
    def create_system_roles(cls):
        """إنشاء الأدوار النظام الأساسية"""
        created_groups = []
        
        for role_code, role_info in cls.SYSTEM_ROLES.items():
            group, created = Group.objects.get_or_create(
                name=role_info['name']
            )
            
            if created:
                created_groups.append(group)
                logger.info(f'تم إنشاء دور: {role_info["name"]}')
            
            # إضافة الصلاحيات للدور
            cls.assign_permissions_to_role(group, role_info['permissions'])
        
        return created_groups
    
    @classmethod
    def assign_permissions_to_role(cls, group, permission_codes):
        """تعيين الصلاحيات للدور"""
        if '*' in permission_codes:
            # جميع الصلاحيات
            all_permissions = Permission.objects.all()
            group.permissions.set(all_permissions)
            logger.info(f'تم تعيين جميع الصلاحيات للدور: {group.name}')
            return
        
        permissions = []
        for perm_code in permission_codes:
            try:
                # البحث في الصلاحيات الافتراضية أولاً
                permission = Permission.objects.filter(codename=perm_code).first()
                if permission:
                    permissions.append(permission)
                else:
                    logger.warning(f'الصلاحية غير موجودة: {perm_code}')
            except Exception as e:
                logger.error(f'خطأ في البحث عن الصلاحية {perm_code}: {str(e)}')
        
        if permissions:
            group.permissions.set(permissions)
            logger.info(f'تم تعيين {len(permissions)} صلاحية للدور: {group.name}')
    
    @classmethod
    def assign_role_to_user(cls, user, role_name):
        """تعيين دور للمستخدم"""
        try:
            group = Group.objects.get(name=role_name)
            user.groups.add(group)
            logger.info(f'تم تعيين الدور {role_name} للمستخدم {user.username}')
            return True
        except Group.DoesNotExist:
            logger.error(f'الدور غير موجود: {role_name}')
            return False
        except Exception as e:
            logger.error(f'خطأ في تعيين الدور: {str(e)}')
            return False
    
    @classmethod
    def remove_role_from_user(cls, user, role_name):
        """إزالة دور من المستخدم"""
        try:
            group = Group.objects.get(name=role_name)
            user.groups.remove(group)
            logger.info(f'تم إزالة الدور {role_name} من المستخدم {user.username}')
            return True
        except Group.DoesNotExist:
            logger.error(f'الدور غير موجود: {role_name}')
            return False
        except Exception as e:
            logger.error(f'خطأ في إزالة الدور: {str(e)}')
            return False
    
    @classmethod
    def user_has_permission(cls, user, permission_code):
        """التحقق من صلاحية المستخدم"""
        if not user.is_authenticated:
            return False
            
        if user.is_superuser:
            return True
        
        # البحث في الصلاحيات المباشرة
        if user.has_perm(f'auth.{permission_code}') or user.has_perm(permission_code):
            return True
        
        # البحث في صلاحيات الأدوار
        for group in user.groups.all():
            if group.permissions.filter(codename=permission_code).exists():
                return True
        
        return False
    
    @classmethod
    def get_user_roles(cls, user):
        """الحصول على أدوار المستخدم"""
        return [group.name for group in user.groups.all()]
    
    @classmethod
    def get_role_permissions(cls, role_name):
        """الحصول على صلاحيات الدور"""
        try:
            group = Group.objects.get(name=role_name)
            return [perm.codename for perm in group.permissions.all()]
        except Group.DoesNotExist:
            return []
    
    @classmethod
    def get_users_with_role(cls, role_name):
        """الحصول على المستخدمين الذين لديهم دور معين"""
        try:
            group = Group.objects.get(name=role_name)
            return group.user_set.all()
        except Group.DoesNotExist:
            return User.objects.none()
    
    @classmethod
    def bulk_assign_role(cls, users, role_name):
        """تعيين دور لعدة مستخدمين"""
        try:
            group = Group.objects.get(name=role_name)
            for user in users:
                user.groups.add(group)
            return True
        except Group.DoesNotExist:
            logger.error(f'الدور غير موجود: {role_name}')
            return False
        except Exception as e:
            logger.error(f'خطأ في التعيين المجمع: {str(e)}')
            return False


# Decorators للتحقق من الصلاحيات

def require_permission(permission_code, redirect_url=None):
    """decorator للتحقق من صلاحية معينة"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if not AdvancedPermissionManager.user_has_permission(request.user, permission_code):
                if redirect_url:
                    messages.error(request, _('ليس لديك الصلاحية للوصول لهذه الصفحة'))
                    return redirect(redirect_url)
                else:
                    return JsonResponse({
                        'error': _('ليس لديك الصلاحية لهذه العملية')
                    }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_role(role_name, redirect_url=None):
    """decorator للتحقق من دور معين"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            user_roles = AdvancedPermissionManager.get_user_roles(request.user)
            if role_name not in user_roles and not request.user.is_superuser:
                if redirect_url:
                    messages.error(request, _('ليس لديك الدور المطلوب للوصول لهذه الصفحة'))
                    return redirect(redirect_url)
                else:
                    return JsonResponse({
                        'error': _('ليس لديك الدور المطلوب لهذه العملية')
                    }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def staff_or_permission_required(permission_code=None):
    """decorator للتحقق من كون المستخدم staff أو لديه صلاحية معينة"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if request.user.is_staff or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            if permission_code and AdvancedPermissionManager.user_has_permission(request.user, permission_code):
                return view_func(request, *args, **kwargs)
            
            return JsonResponse({
                'error': _('ليس لديك الصلاحية لهذه العملية')
            }, status=403)
        
        return _wrapped_view
    return decorator


def superuser_required(redirect_url=None):
    """decorator للتحقق من كون المستخدم superuser"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if not request.user.is_superuser:
                if redirect_url:
                    messages.error(request, _('هذه الصفحة مخصصة للمديرين العموميين فقط'))
                    return redirect(redirect_url)
                else:
                    return JsonResponse({
                        'error': _('صلاحيات المدير العام مطلوبة')
                    }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# === Views لإدارة الصلاحيات ===

@method_decorator([staff_member_required], name='dispatch')
class PermissionsManagementView(TemplateView):
    """إدارة الصلاحيات والأدوار"""
    template_name = 'admin/permissions/management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['users'] = User.objects.select_related().prefetch_related('groups', 'user_permissions')
        context['groups'] = Group.objects.prefetch_related('permissions')
        context['permissions'] = Permission.objects.all().order_by('content_type', 'codename')
        context['system_roles'] = AdvancedPermissionManager.SYSTEM_ROLES
        context['custom_permissions'] = AdvancedPermissionManager.CUSTOM_PERMISSIONS
        
        return context


@method_decorator([staff_member_required], name='dispatch')
class UserPermissionsView(View):
    """إدارة صلاحيات المستخدم"""
    
    def get(self, request, user_id):
        """عرض صلاحيات المستخدم"""
        user = get_object_or_404(User, pk=user_id)
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name(),
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'roles': AdvancedPermissionManager.get_user_roles(user),
            'permissions': [
                {
                    'id': perm.id,
                    'codename': perm.codename,
                    'name': perm.name,
                    'content_type': perm.content_type.name
                }
                for perm in user.user_permissions.all()
            ],
            'group_permissions': []
        }
        
        # الحصول على صلاحيات الأدوار
        for group in user.groups.all():
            group_perms = []
            for perm in group.permissions.all():
                group_perms.append({
                    'id': perm.id,
                    'codename': perm.codename,
                    'name': perm.name,
                    'content_type': perm.content_type.name
                })
            
            user_data['group_permissions'].append({
                'group_id': group.id,
                'group_name': group.name,
                'permissions': group_perms
            })
        
        return JsonResponse(user_data)
    
    def post(self, request, user_id):
        """تحديث صلاحيات المستخدم"""
        user = get_object_or_404(User, pk=user_id)
        
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'assign_role':
                role_name = data.get('role_name')
                success = AdvancedPermissionManager.assign_role_to_user(user, role_name)
                
                return JsonResponse({
                    'success': success,
                    'message': _('تم تعيين الدور بنجاح') if success else _('فشل في تعيين الدور')
                })
            
            elif action == 'remove_role':
                role_name = data.get('role_name')
                success = AdvancedPermissionManager.remove_role_from_user(user, role_name)
                
                return JsonResponse({
                    'success': success,
                    'message': _('تم إزالة الدور بنجاح') if success else _('فشل في إزالة الدور')
                })
            
            elif action == 'assign_permission':
                permission_id = data.get('permission_id')
                permission = get_object_or_404(Permission, pk=permission_id)
                user.user_permissions.add(permission)
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم تعيين الصلاحية بنجاح')
                })
            
            elif action == 'remove_permission':
                permission_id = data.get('permission_id')
                permission = get_object_or_404(Permission, pk=permission_id)
                user.user_permissions.remove(permission)
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم إزالة الصلاحية بنجاح')
                })
            
            elif action == 'update_status':
                user.is_active = data.get('is_active', user.is_active)
                user.is_staff = data.get('is_staff', user.is_staff)
                if request.user.is_superuser:  # فقط المدير العام يمكنه تغيير صلاحيات superuser
                    user.is_superuser = data.get('is_superuser', user.is_superuser)
                user.save()
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم تحديث الحالة بنجاح')
                })
            
            elif action == 'bulk_assign_permissions':
                permission_ids = data.get('permission_ids', [])
                permissions = Permission.objects.filter(id__in=permission_ids)
                user.user_permissions.set(permissions)
                
                return JsonResponse({
                    'success': True,
                    'message': _(f'تم تعيين {len(permissions)} صلاحية بنجاح')
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': _('عملية غير مدعومة')
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': _('بيانات غير صالحة')
            }, status=400)
        except Exception as e:
            logger.error(f'خطأ في إدارة صلاحيات المستخدم: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': f'خطأ: {str(e)}'
            }, status=500)


@method_decorator([staff_member_required], name='dispatch')
class RoleManagementView(View):
    """إدارة الأدوار"""
    
    def get(self, request, role_id=None):
        """عرض معلومات الدور"""
        if role_id:
            group = get_object_or_404(Group, pk=role_id)
            role_data = {
                'id': group.id,
                'name': group.name,
                'user_count': group.user_set.count(),
                'permissions': [
                    {
                        'id': perm.id,
                        'codename': perm.codename,
                        'name': perm.name,
                        'content_type': perm.content_type.name
                    }
                    for perm in group.permissions.all()
                ]
            }
            return JsonResponse(role_data)
        else:
            # عرض جميع الأدوار
            roles = []
            for group in Group.objects.prefetch_related('permissions', 'user_set'):
                roles.append({
                    'id': group.id,
                    'name': group.name,
                    'user_count': group.user_set.count(),
                    'permission_count': group.permissions.count()
                })
            return JsonResponse({'roles': roles})
    
    def post(self, request, role_id=None):
        """إنشاء أو تعديل دور"""
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'create_role':
                role_name = data.get('name', '').strip()
                if not role_name:
                    return JsonResponse({
                        'success': False,
                        'message': _('اسم الدور مطلوب')
                    }, status=400)
                
                role_description = data.get('description', '')
                permission_ids = data.get('permissions', [])
                
                # التحقق من عدم وجود الدور مسبقاً
                if Group.objects.filter(name=role_name).exists():
                    return JsonResponse({
                        'success': False,
                        'message': _('الدور موجود بالفعل')
                    }, status=400)
                
                # إنشاء الدور
                group = Group.objects.create(name=role_name)
                
                # إضافة الصلاحيات
                if permission_ids:
                    permissions = Permission.objects.filter(id__in=permission_ids)
                    group.permissions.set(permissions)
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم إنشاء الدور بنجاح'),
                    'role_id': group.id
                })
            
            elif action == 'update_role':
                if not role_id:
                    role_id = data.get('role_id')
                
                group = get_object_or_404(Group, pk=role_id)
                permission_ids = data.get('permissions', [])
                
                # تحديث الصلاحيات
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم تحديث الدور بنجاح')
                })
            
            elif action == 'delete_role':
                if not role_id:
                    role_id = data.get('role_id')
                
                group = get_object_or_404(Group, pk=role_id)
                
                # التحقق من عدم وجود مستخدمين بهذا الدور
                user_count = group.user_set.count()
                if user_count > 0:
                    return JsonResponse({
                        'success': False,
                        'message': _('لا يمكن حذف الدور لأنه مستخدم من قبل {} مستخدم').format(user_count)
                    }, status=400)
                
                group_name = group.name
                group.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم حذف الدور "{}" بنجاح').format(group_name)
                })
            
            elif action == 'clone_role':
                source_role_id = data.get('source_role_id')
                new_role_name = data.get('new_role_name', '').strip()
                
                if not new_role_name:
                    return JsonResponse({
                        'success': False,
                        'message': _('اسم الدور الجديد مطلوب')
                    }, status=400)
                
                source_group = get_object_or_404(Group, pk=source_role_id)
                
                # التحقق من عدم وجود الدور الجديد
                if Group.objects.filter(name=new_role_name).exists():
                    return JsonResponse({
                        'success': False,
                        'message': _('الدور الجديد موجود بالفعل')
                    }, status=400)
                
                # إنشاء دور جديد
                new_group = Group.objects.create(name=new_role_name)
                
                # نسخ الصلاحيات
                new_group.permissions.set(source_group.permissions.all())
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم نسخ الدور بنجاح'),
                    'role_id': new_group.id
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': _('عملية غير مدعومة')
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': _('بيانات غير صالحة')
            }, status=400)
        except Exception as e:
            logger.error(f'خطأ في إدارة الأدوار: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': f'خطأ: {str(e)}'
            }, status=500)
    
    def delete(self, request, role_id):
        """حذف دور"""
        try:
            group = get_object_or_404(Group, pk=role_id)
            
            # التحقق من عدم وجود مستخدمين بهذا الدور
            user_count = group.user_set.count()
            if user_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': _('لا يمكن حذف الدور لأنه مستخدم من قبل {} مستخدم').format(user_count)
                }, status=400)
            
            group_name = group.name
            group.delete()
            
            return JsonResponse({
                'success': True,
                'message': _('تم حذف الدور "{}" بنجاح').format(group_name)
            })
            
        except Exception as e:
            logger.error(f'خطأ في حذف الدور: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': f'خطأ: {str(e)}'
            }, status=500)


@method_decorator([superuser_required()], name='dispatch')
class BulkPermissionsView(View):
    """العمليات المجمعة للصلاحيات"""
    
    def post(self, request):
        """تنفيذ العمليات المجمعة"""
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'bulk_assign_role':
                user_ids = data.get('user_ids', [])
                role_name = data.get('role_name')
                
                users = User.objects.filter(id__in=user_ids)
                success = AdvancedPermissionManager.bulk_assign_role(users, role_name)
                
                return JsonResponse({
                    'success': success,
                    'message': _('تم تعيين الدور لـ {} مستخدم').format(len(users)) if success else _('فشل في التعيين المجمع')
                })
            
            elif action == 'bulk_remove_role':
                user_ids = data.get('user_ids', [])
                role_name = data.get('role_name')
                
                try:
                    group = Group.objects.get(name=role_name)
                    users = User.objects.filter(id__in=user_ids)
                    for user in users:
                        user.groups.remove(group)
                    
                    return JsonResponse({
                        'success': True,
                        'message': _('تم إزالة الدور من {} مستخدم').format(len(users))
                    })
                except Group.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': _('الدور غير موجود')
                    }, status=400)
            
            elif action == 'bulk_deactivate_users':
                user_ids = data.get('user_ids', [])
                users = User.objects.filter(id__in=user_ids)
                users.update(is_active=False)
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم إلغاء تفعيل {} مستخدم').format(len(users))
                })
            
            elif action == 'bulk_activate_users':
                user_ids = data.get('user_ids', [])
                users = User.objects.filter(id__in=user_ids)
                users.update(is_active=True)
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم تفعيل {} مستخدم').format(len(users))
                })
            
            elif action == 'bulk_delete_users':
                user_ids = data.get('user_ids', [])
                # التأكد من عدم حذف المستخدم الحالي
                if request.user.id in user_ids:
                    return JsonResponse({
                        'success': False,
                        'message': _('لا يمكن حذف المستخدم الحالي')
                    }, status=400)
                
                users = User.objects.filter(id__in=user_ids)
                user_count = users.count()
                users.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': _('تم حذف {} مستخدم').format(user_count)
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': _('عملية غير مدعومة')
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': _('بيانات غير صالحة')
            }, status=400)
        except Exception as e:
            logger.error(f'خطأ في العمليات المجمعة: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': f'خطأ: {str(e)}'
            }, status=500)


# === Management Command لتهيئة الصلاحيات ===

class PermissionsSetupCommand(BaseCommand):
    """أمر إعداد نظام الصلاحيات المتقدم"""
    help = 'إعداد نظام الصلاحيات المتقدم'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='إعادة تعيين جميع الأدوار والصلاحيات'
        )
        
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='إنشاء مستخدم مدير عام'
        )
        
        parser.add_argument(
            '--admin-username',
            type=str,
            default='admin',
            help='اسم المستخدم للمدير العام'
        )
        
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@example.com',
            help='البريد الإلكتروني للمدير العام'
        )
        
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='كلمة المرور للمدير العام'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('بدء إعداد نظام الصلاحيات المتقدم...')
        )
        
        if options['reset']:
            self.stdout.write('إعادة تعيين الأدوار والصلاحيات...')
            # حذف الأدوار الموجودة (ما عدا المدراء العموميين)
            Group.objects.exclude(
                user__is_superuser=True
            ).delete()
        
        # إنشاء الصلاحيات المخصصة
        created_permissions = AdvancedPermissionManager.create_custom_permissions()
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {len(created_permissions)} صلاحية مخصصة')
        )
        
        # إنشاء الأدوار
        created_groups = AdvancedPermissionManager.create_system_roles()
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {len(created_groups)} دور')
        )
        
        # إنشاء مستخدم مدير عام إذا لم يكن موجوداً
        if options['create_admin'] or not User.objects.filter(is_superuser=True).exists():
            self.create_super_admin(options)
        
        # عرض إحصائيات
        self.display_statistics()
        
        self.stdout.write(
            self.style.SUCCESS('تم إعداد نظام الصلاحيات بنجاح!')
        )
    
    def create_super_admin(self, options):
        """إنشاء مستخدم مدير عام"""
        username = options.get('admin_username', 'admin')
        email = options.get('admin_email', 'admin@example.com')
        password = options.get('admin_password', 'admin123')
        
        # التحقق من عدم وجود المستخدم
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'المستخدم {username} موجود بالفعل')
            )
            return
        
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء المدير العام: {username}')
        )
        self.stdout.write(
            self.style.WARNING(f'كلمة المرور: {password}')
        )
        self.stdout.write(
            self.style.WARNING('يرجى تغيير كلمة المرور فوراً!')
        )
    
    def display_statistics(self):
        """عرض إحصائيات النظام"""
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        superusers = User.objects.filter(is_superuser=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        total_groups = Group.objects.count()
        total_permissions = Permission.objects.count()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('إحصائيات النظام:'))
        self.stdout.write(f'إجمالي المستخدمين: {total_users}')
        self.stdout.write(f'المستخدمين النشطين: {active_users}')
        self.stdout.write(f'المديرين العموميين: {superusers}')
        self.stdout.write(f'الموظفين: {staff_users}')
        self.stdout.write(f'إجمالي الأدوار: {total_groups}')
        self.stdout.write(f'إجمالي الصلاحيات: {total_permissions}')
        self.stdout.write('='*50)


# === Context Processors ===

def permissions_context(request):
    """إضافة معلومات الصلاحيات للسياق"""
    if not request.user.is_authenticated:
        return {}
    
    user_roles = AdvancedPermissionManager.get_user_roles(request.user)
    
    # صلاحيات مهمة للتحقق منها في القوالب
    important_permissions = [
        'upload_media', 'manage_media', 'moderate_content',
        'view_analytics', 'user_management', 'system_settings'
    ]
    
    user_permissions = {}
    for perm in important_permissions:
        user_permissions[perm] = AdvancedPermissionManager.user_has_permission(
            request.user, perm
        )
    
    return {
        'user_roles': user_roles,
        'user_permissions': user_permissions,
        'is_content_manager': _('مدير المحتوى') in user_roles,
        'is_blog_editor': _('محرر المدونة') in user_roles,
        'is_moderator': _('مشرف') in user_roles,
        'can_manage_users': user_permissions.get('user_management', False) or request.user.is_staff,
        'can_view_analytics': user_permissions.get('view_analytics', False) or request.user.is_staff
    }


# === Utility Functions ===

def get_permission_tree():
    """الحصول على شجرة الصلاحيات مرتبة حسب التطبيق"""
    permissions_tree = {}
    
    for permission in Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename'):
        app_label = permission.content_type.app_label
        model_name = permission.content_type.model
        
        if app_label not in permissions_tree:
            permissions_tree[app_label] = {}
        
        if model_name not in permissions_tree[app_label]:
            permissions_tree[app_label][model_name] = []
        
        permissions_tree[app_label][model_name].append({
            'id': permission.id,
            'codename': permission.codename,
            'name': permission.name
        })
    
    return permissions_tree


def check_user_ownership(user, obj, field_name='user'):
    """التحقق من ملكية المستخدم للكائن"""
    try:
        return getattr(obj, field_name) == user
    except AttributeError:
        return False


def can_edit_comment(user, comment):
    """التحقق من إمكانية تعديل التعليق"""
    # المالك يمكنه التعديل دائماً
    if comment.user == user:
        return True
    
    # المشرفين يمكنهم التعديل
    if AdvancedPermissionManager.user_has_permission(user, 'moderate_content'):
        return True
    
    # المديرين والموظفين يمكنهم التعديل
    if user.is_staff or user.is_superuser:
        return True
    
    return False


def can_delete_content(user, content):
    """التحقق من إمكانية حذف المحتوى"""
    # المالك يمكنه الحذف
    if hasattr(content, 'user') and content.user == user:
        return True
    
    # مدير المحتوى يمكنه الحذف
    user_roles = AdvancedPermissionManager.get_user_roles(user)
    if _('مدير المحتوى') in user_roles:
        return True
    
    # المديرين والموظفين يمكنهم الحذف
    if user.is_staff or user.is_superuser:
        return True
    
    return False


def log_permission_change(user, target_user, action, details=''):
    """تسجيل تغييرات الصلاحيات"""
    logger.info(
        f'تغيير صلاحيات - المستخدم: {user.username}, '
        f'المستهدف: {target_user.username if target_user else "N/A"}, '
        f'العملية: {action}, التفاصيل: {details}'
    )


# === Template Tags Helper Functions ===

def user_can(user, permission_code):
    """دالة مساعدة للقوالب للتحقق من الصلاحيات"""
    return AdvancedPermissionManager.user_has_permission(user, permission_code)


def user_has_role(user, role_name):
    """دالة مساعدة للقوالب للتحقق من الأدوار"""
    user_roles = AdvancedPermissionManager.get_user_roles(user)
    return role_name in user_roles


def is_owner_or_staff(user, obj, field_name='user'):
    """التحقق من الملكية أو كون المستخدم موظف"""
    return check_user_ownership(user, obj, field_name) or user.is_staff


# === Middleware ===

class PermissionsMiddleware:
    """Middleware لمراقبة الصلاحيات"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # تسجيل محاولات الوصول للمسارات الحساسة
        sensitive_paths = ['/admin/', '/api/', '/dashboard/']
        
        if request.user.is_authenticated and any(
            request.path.startswith(path) for path in sensitive_paths
        ):
            logger.info(
                f'وصول للمسار الحساس - المستخدم: {request.user.username}, '
                f'المسار: {request.path}, IP: {self.get_client_ip(request)}'
            )
        
        response = self.get_response(request)
        
        # تسجيل الوصول المرفوض
        if response.status_code == 403:
            logger.warning(
                f'وصول مرفوض - المستخدم: {request.user.username if request.user.is_authenticated else "Anonymous"}, '
                f'المسار: {request.path}, IP: {self.get_client_ip(request)}'
            )
        
        return response
    
    def get_client_ip(self, request):
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# === Signals ===

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """معالج إنشاء مستخدم جديد"""
    if created:
        # تعيين دور المشترك افتراضياً للمستخدمين الجدد
        default_role = _('مشترك')
        AdvancedPermissionManager.assign_role_to_user(instance, default_role)
        
        logger.info(f'تم إنشاء مستخدم جديد: {instance.username} وتعيين الدور الافتراضي')


@receiver(post_save, sender=Group)
def group_created_handler(sender, instance, created, **kwargs):
    """معالج إنشاء دور جديد"""
    if created:
        logger.info(f'تم إنشاء دور جديد: {instance.name}')


@receiver(post_delete, sender=Group)
def group_deleted_handler(sender, instance, **kwargs):
    """معالج حذف دور"""
    logger.info(f'تم حذف الدور: {instance.name}')


# === Export/Import Functions ===

def export_permissions_config():
    """تصدير إعدادات الصلاحيات"""
    config = {
        'groups': [],
        'users': [],
        'permissions': []
    }
    
    # تصدير الأدوار
    for group in Group.objects.prefetch_related('permissions'):
        config['groups'].append({
            'name': group.name,
            'permissions': [perm.codename for perm in group.permissions.all()]
        })
    
    # تصدير المستخدمين وأدوارهم
    for user in User.objects.prefetch_related('groups', 'user_permissions'):
        if not user.is_superuser:  # استبعاد المديرين العموميين
            config['users'].append({
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'groups': [group.name for group in user.groups.all()],
                'permissions': [perm.codename for perm in user.user_permissions.all()]
            })
    
    return config


def import_permissions_config(config):
    """استيراد إعدادات الصلاحيات"""
    try:
        # استيراد الأدوار
        for group_data in config.get('groups', []):
            group, created = Group.objects.get_or_create(name=group_data['name'])
            
            # تعيين الصلاحيات
            permission_codes = group_data.get('permissions', [])
            permissions = Permission.objects.filter(codename__in=permission_codes)
            group.permissions.set(permissions)
            
            if created:
                logger.info(f'تم استيراد الدور: {group.name}')
        
        # استيراد المستخدمين
        for user_data in config.get('users', []):
            username = user_data['username']
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                logger.warning(f'المستخدم غير موجود: {username}')
                continue
            
            # تحديث الحالة
            user.is_active = user_data.get('is_active', True)
            user.is_staff = user_data.get('is_staff', False)
            user.save()
            
            # تعيين الأدوار
            group_names = user_data.get('groups', [])
            groups = Group.objects.filter(name__in=group_names)
            user.groups.set(groups)
            
            # تعيين الصلاحيات المباشرة
            permission_codes = user_data.get('permissions', [])
            permissions = Permission.objects.filter(codename__in=permission_codes)
            user.user_permissions.set(permissions)
            
            logger.info(f'تم استيراد بيانات المستخدم: {username}')
        
        return True
    except Exception as e:
        logger.error(f'خطأ في استيراد إعدادات الصلاحيات: {str(e)}')
        return False
