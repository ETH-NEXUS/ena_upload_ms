# Generated by Django 4.2.7 on 2023-11-27 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_alter_analysisjob_raw_result_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysisjob',
            name='data',
            field=models.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='analysisjob',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'DRAFT'), ('QUEUED', 'QUEUED'), ('SUBMITTED', 'SUBMITTED'), ('ERROR', 'ERROR')], default='DRAFT', max_length=20),
        ),
        migrations.AlterField(
            model_name='job',
            name='action',
            field=models.TextField(choices=[('ADD', 'ADD'), ('MODIFY', 'MODIFY'), ('CANCEL', 'CANCEL'), ('RELEASE', 'RELEASE')], default='ADD'),
        ),
        migrations.AlterField(
            model_name='job',
            name='data',
            field=models.JSONField(default={}),
        ),
    ]