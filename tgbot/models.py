from django.db import models


class User(models.Model):
    user_id = models.IntegerField(verbose_name='Telegram id', blank=False, unique=True)
    name = models.CharField(verbose_name='Name from Telegram', max_length=300, blank=False)
    status = models.CharField(verbose_name="Status In Chat", max_length=2, blank=False, default="m")
    is_active = models.BooleanField(verbose_name='Active in Telegram', default=True)
    last_active = models.DateTimeField(verbose_name='Last Active', blank=False, auto_now=True)
    date_registered = models.DateTimeField(verbose_name='Registered', blank=False, auto_now_add=True)

    def __str__(self):
        return "%s(%i)" % (self.name, self.user_id)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
