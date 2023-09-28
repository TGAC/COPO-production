# Generated by Django 4.2.4 on 2023-09-19 13:48

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('copo_core', '0003_sequencingcenter_delete_sequencingcentergroup'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sequencingcenter',
            name='users',
        ),
        migrations.AddField(
            model_name='sequencingcenter',
            name='users',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
    ]