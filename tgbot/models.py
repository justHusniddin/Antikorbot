from django.db import models
from django.utils.translation import gettext_lazy as _

class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(
        unique=True,
        verbose_name=_("Telegram ID")
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Username")
    )
    first_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("First Name")
    )
    last_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Last Name")
    )
    language = models.CharField(
        max_length=2,
        choices=[('ru', 'Russian'), ('uz', 'Uzbek')],
        # default='ru',
        verbose_name=_("Language")
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name=_("Is Blocked")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        verbose_name = _("Telegram User")
        verbose_name_plural = _("Telegram Users")
        ordering = ['-created_at']

    def __str__(self):
        return f"@{self.username}" if self.username else str(self.telegram_id)


class Complaint(models.Model):
    """Complaint model for corruption reports"""

    STATUS_CHOICES = [
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('resolved', _('Resolved')),
        ('rejected', _('Rejected')),
    ]

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='complaints',
        verbose_name=_("User")
    )
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name=_("Is Anonymous")
    )

    # Contact details (if not anonymous)
    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Full Name")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("Phone Number")
    )
    telegram_username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Telegram Username")
    )

    region_id = models.IntegerField(
        verbose_name=_("Region ID")
    )
    region_name = models.CharField(
        max_length=255,
        verbose_name=_("Region Name")
    )
    district_id = models.IntegerField(
        verbose_name=_("District ID")
    )
    district_name = models.CharField(
        max_length=255,
        verbose_name=_("District Name")
    )
    street_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Street/Mahalla ID")
    )
    street_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Street/Mahalla Name")
    )

    target_full_name = models.CharField(
        max_length=255,
        verbose_name=_("Target Full Name")
    )
    target_position = models.CharField(
        max_length=255,
        verbose_name=_("Target Position")
    )
    target_organization = models.CharField(
        max_length=500,
        verbose_name=_("Target Organization")
    )

    complaint_text = models.TextField(
        verbose_name=_("Complaint Text")
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name=_("Status")
    )

    admin_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Admin Notes")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Resolved At")
    )

    class Meta:
        verbose_name = _("Complaint")
        verbose_name_plural = _("Complaints")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['region_id', '-created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Complaint #{self.id} - {self.get_status_display()}"

    def get_full_address(self):
        """Get formatted full address"""
        parts = [self.region_name, self.district_name]
        if self.street_name:
            parts.append(self.street_name)
        return ', '.join(parts)


class ComplaintMedia(models.Model):

    FILE_TYPE_CHOICES = [
        ('photo', _('Photo')),
        ('video', _('Video')),
        ('document', _('Document')),
    ]

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='media_files',
        verbose_name=_("Complaint")
    )
    file_id = models.CharField(
        max_length=255,
        verbose_name=_("Telegram File ID")
    )
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        verbose_name=_("File Type")
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("File Name")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    class Meta:
        verbose_name = _("Complaint Media")
        verbose_name_plural = _("Complaint Media")
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_file_type_display()} for Complaint #{self.complaint.id}"


class BroadcastMessage(models.Model):

    text = models.TextField(
        verbose_name=_("Message Text")
    )
    sent_count = models.IntegerField(
        default=0,
        verbose_name=_("Sent Count")
    )
    failed_count = models.IntegerField(
        default=0,
        verbose_name=_("Failed Count")
    )
    created_by = models.CharField(
        max_length=255,
        verbose_name=_("Created By")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Completed At")
    )

    class Meta:
        verbose_name = _("Broadcast Message")
        verbose_name_plural = _("Broadcast Messages")
        ordering = ['-created_at']

    def __str__(self):
        return f"Broadcast #{self.id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
