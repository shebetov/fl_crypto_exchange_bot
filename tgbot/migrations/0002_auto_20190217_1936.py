# Generated by Django 2.1.7 on 2019-02-17 16:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tgbot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='lang',
            field=models.CharField(default='en', max_length=2, verbose_name='Language'),
        ),
        migrations.AlterField(
            model_name='user',
            name='status',
            field=models.CharField(default='m', max_length=2, verbose_name='Status In Chat'),
        ),
    ]
