# Generated manually for Phase 1 chat REST API

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='last_message_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatroom',
            name='topic',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(fields=['workspace', 'created_by'], name='chat_rooms_workspa_cb_8f1b_idx'),
        ),
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(fields=['is_active', '-last_message_at'], name='chat_rooms_active_9a7e_idx'),
        ),
    ]
