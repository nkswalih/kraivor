import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("chat", "0003_rename_chat_rooms_workspa_cb_8f1b_idx_chat_rooms_workspa_74753b_idx_and_more")]

    operations = [
        migrations.AddField(
            model_name="chatroom",
            name="last_message_content",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="chatroom",
            name="last_message_sender_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.CreateModel(
            name="ChatRoomParticipant",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("user_id", models.UUIDField()),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="participants",
                        to="chat.chatroom",
                    ),
                ),
            ],
            options={
                "verbose_name": "Chat Room Participant",
                "verbose_name_plural": "Chat Room Participants",
                "db_table": "chat_room_participants",
                "unique_together": {("room", "user_id")},
            },
        ),
        migrations.AddIndex(
            model_name="chatroomparticipant",
            index=models.Index(fields=["user_id", "room"], name="chat_room_pa_user_id_2376ee_idx"),
        ),
    ]
