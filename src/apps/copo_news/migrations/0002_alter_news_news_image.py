# Generated by Django 4.2.4 on 2024-07-29 13:44

from django.db import migrations, models
import src.apps.copo_news.models
import src.apps.copo_news.storage


class Migration(migrations.Migration):

    dependencies = [
        ('copo_news', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='news_image',
            field=models.ImageField(blank=True, null=True, storage=src.apps.copo_news.storage.OverwriteStorage(), upload_to=src.apps.copo_news.models.news_image_upload_path),
        ),
    ]