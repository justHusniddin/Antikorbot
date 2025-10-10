from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Complaint
import openpyxl
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
import csv
from datetime import datetime
from .models import TelegramUser, Complaint, ComplaintMedia, BroadcastMessage
import zipfile
import io
import os

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):

    list_display = ['telegram_id', 'username', 'full_name_display', 'language', 'is_blocked', 'created_at']
    list_filter = ['language', 'is_blocked', 'created_at']
    search_fields = ['telegram_id', 'username', 'first_name', 'last_name']
    readonly_fields = ['telegram_id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def full_name_display(self, obj):
        """Display full name"""
        parts = []
        if obj.first_name:
            parts.append(obj.first_name)
        if obj.last_name:
            parts.append(obj.last_name)
        return ' '.join(parts) if parts else '-'
    full_name_display.short_description = _('Full Name')


class ComplaintMediaInline(admin.TabularInline):
    model = ComplaintMedia
    extra = 0
    readonly_fields = ['file_type', 'file_id', 'file_name', 'created_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'created_at',
        'status_badge',
        'user_display',
        'is_anonymous',
        'region_name',
        'district_name',
        'target_full_name',
        'view_details_link'
    ]
    list_filter = [
        'status',
        'is_anonymous',
        'created_at',
        'region_name',
    ]
    search_fields = [
        'id',
        'full_name',
        'phone_number',
        'target_full_name',
        'target_organization',
        'complaint_text'
    ]
    readonly_fields = [
        'user',
        'created_at',
        'updated_at',
        'full_address_display',
        'media_files_display'
    ]

    fieldsets = (
        (_('Status'), {
            'fields': ('status', 'admin_notes')
        }),
        (_('Reporter Information'), {
            'fields': ('user', 'is_anonymous', 'full_name', 'phone_number', 'telegram_username')
        }),
        (_('Location'), {
            'fields': ('full_address_display', 'region_name', 'district_name', 'street_name')
        }),
        (_('Target Person'), {
            'fields': ('target_full_name', 'target_position', 'target_organization')
        }),
        (_('Complaint Details'), {
            'fields': ('complaint_text', 'media_files_display')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ComplaintMediaInline]
    actions = ['export_to_csv', 'mark_in_progress', 'mark_resolved', 'mark_rejected']

    def status_badge(self, obj):
        colors = {
            'new': '#3498db',
            'in_progress': '#f39c12',
            'resolved': '#27ae60',
            'rejected': '#e74c3c'
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')

    def user_display(self, obj):
        if obj.is_anonymous:
            return format_html('<em style="color: #7f8c8d;">Anonymous</em>')
        if obj.user:
            return f"@{obj.user.username}" if obj.user.username else str(obj.user.telegram_id)
        return '-'
    user_display.short_description = _('User')

    def view_details_link(self, obj):
        """Link to view complaint details"""
        url = reverse('admin:tgbot_complaint_change', args=[obj.id])
        return format_html('<a href="{}" class="button">View Details</a>', url)
    view_details_link.short_description = _('Actions')

    def full_address_display(self, obj):
        return obj.get_full_address()
    full_address_display.short_description = _('Full Address')

    def media_files_display(self, obj):
        media = obj.media_files.all()
        if not media:
            return _('No media files')

        html = '<ul style="margin: 0; padding-left: 20px;">'
        for item in media:
            html += f'<li>{item.get_file_type_display()}: {item.file_id}</li>'
        html += '</ul>'
        return format_html(html)
    media_files_display.short_description = _('Media Files')

    def export_to_csv(self, request, queryset):
        """Export selected complaints to CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="complaints_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Created At', 'Status', 'Is Anonymous', 'Full Name', 'Phone',
            'Region', 'District', 'Mahalla', 'Target Name', 'Target Position',
            'Target Organization', 'Complaint Text'
        ])

        for complaint in queryset:
            writer.writerow([
                complaint.id,
                complaint.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                complaint.get_status_display(),
                'Yes' if complaint.is_anonymous else 'No',
                complaint.full_name or '-',
                complaint.phone_number or '-',
                complaint.region_name,
                complaint.district_name,
                complaint.street_name or '-',
                complaint.target_full_name,
                complaint.target_position,
                complaint.target_organization,
                complaint.complaint_text
            ])

        return response
    export_to_csv.short_description = _('Export selected complaints to CSV')

    def mark_in_progress(self, request, queryset):
        """Mark selected complaints as in progress"""
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} complaint(s) marked as in progress.')
    mark_in_progress.short_description = _('Mark as In Progress')

    def mark_resolved(self, request, queryset):
        """Mark selected complaints as resolved"""
        updated = queryset.update(status='resolved', resolved_at=datetime.now())
        self.message_user(request, f'{updated} complaint(s) marked as resolved.')
    mark_resolved.short_description = _('Mark as Resolved')

    def mark_rejected(self, request, queryset):
        """Mark selected complaints as rejected"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} complaint(s) marked as rejected.')
    mark_rejected.short_description = _('Mark as Rejected')


@admin.register(ComplaintMedia)
class ComplaintMediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'complaint_link', 'file_type', 'file_name', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['complaint__id', 'file_id', 'file_name']
    readonly_fields = ['complaint', 'file_id', 'file_type', 'file_name', 'created_at']
    actions = ['download_selected_as_zip']

    def complaint_link(self, obj):
        url = reverse('admin:tgbot_complaint_change', args=[obj.complaint.id])
        return format_html('<a href="{}">Complaint #{}</a>', url, obj.complaint.id)
    complaint_link.short_description = _('Complaint')

    def download_selected_as_zip(self, request, queryset):
        zip_buffer = io.BytesIO()
        added_files = 0
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for media in queryset:
                for field_name in ['file', 'media_file', 'attachment', 'uploaded_file']:
                    if hasattr(media, field_name):
                        file_field = getattr(media, field_name)
                        if file_field and hasattr(file_field, 'path') and os.path.exists(file_field.path):
                            zip_file.write(file_field.path, os.path.basename(file_field.path))
                            added_files += 1
                            break  

        if added_files == 0:
            self.message_user(request, "Hech qanday haqiqiy fayl topilmadi!", level='warning')

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="complaint_media.zip"'
        return response

    download_selected_as_zip.short_description = _("Download selected Complaint Media as ZIP")
@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):

    list_display = ['id', 'created_at', 'created_by', 'sent_count', 'failed_count', 'status_display']
    list_filter = ['created_at']
    search_fields = ['text', 'created_by']
    readonly_fields = ['sent_count', 'failed_count', 'created_at', 'completed_at']

    def status_display(self, obj):
        """Display broadcast status"""
        if obj.completed_at:
            return format_html(
                '<span style="color: green;">✓ Completed</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ In Progress</span>'
        )
    status_display.short_description = _('Status')
@admin.action(description="Tanlangan shikoyatlarni Excel faylga yuklab olish")
def export_to_excel(modeladmin, request, queryset):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Complaints"

    # 2. Sarlavhalar (ustun nomlari)
    columns = [
        'ID', 'To‘liq ism', 'Telefon raqami', 'Viloyat', 'Tuman', 'Mahalla',
        'Kimga qarshi', 'Lavozimi', 'Tashkiloti', 'Shikoyat matni', 'Yaratilgan sana'
    ]
    worksheet.append(columns)

    # 3. Har bir yozuvni jadvalga yozish
    for obj in queryset:
        worksheet.append([
            obj.id,
            obj.full_name,
            obj.phone_number,
            obj.region,
            obj.district,
            obj.mahalla,
            obj.target_full_name,
            obj.target_position,
            obj.target_organization,
            obj.complaint_text,
            obj.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename=complaints.xlsx'
    workbook.save(response)
    return response