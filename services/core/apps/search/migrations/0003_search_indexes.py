from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0001_enable_pg_trgm"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_search_project_name_trgm
            ON projects_project USING gin (name gin_trgm_ops);
            CREATE INDEX IF NOT EXISTS idx_search_project_desc_trgm
            ON projects_project USING gin (description gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_search_task_title_trgm
            ON projects_task USING gin (title gin_trgm_ops);
            CREATE INDEX IF NOT EXISTS idx_search_task_desc_trgm
            ON projects_task USING gin (description gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_search_ks_name_trgm
            ON knowledge_spaces USING gin (name gin_trgm_ops);
            CREATE INDEX IF NOT EXISTS idx_search_ks_desc_trgm
            ON knowledge_spaces USING gin (description gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_search_asset_filename_trgm
            ON knowledge_assets USING gin (file_name gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_search_repo_name_trgm
            ON repositories USING gin (github_repo gin_trgm_ops);
            CREATE INDEX IF NOT EXISTS idx_search_repo_desc_trgm
            ON repositories USING gin (description gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_search_notif_title_trgm
            ON notifications USING gin (title gin_trgm_ops);
            CREATE INDEX IF NOT EXISTS idx_search_notif_body_trgm
            ON notifications USING gin (body gin_trgm_ops);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_search_project_name_trgm;
            DROP INDEX IF EXISTS idx_search_project_desc_trgm;
            DROP INDEX IF EXISTS idx_search_task_title_trgm;
            DROP INDEX IF EXISTS idx_search_task_desc_trgm;
            DROP INDEX IF EXISTS idx_search_ks_name_trgm;
            DROP INDEX IF EXISTS idx_search_ks_desc_trgm;
            DROP INDEX IF EXISTS idx_search_asset_filename_trgm;
            DROP INDEX IF EXISTS idx_search_repo_name_trgm;
            DROP INDEX IF EXISTS idx_search_repo_desc_trgm;
            DROP INDEX IF EXISTS idx_search_notif_title_trgm;
            DROP INDEX IF EXISTS idx_search_notif_body_trgm;
            """,
        ),
    ]
