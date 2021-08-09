from matcher.service import create_app, create_celery

app = create_app()
celery_app = create_celery(
    app, config_source="matcher.service.config.celery_config"
)
