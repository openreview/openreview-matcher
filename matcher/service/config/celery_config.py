from kombu import Exchange, Queue
from kombu.serialization import registry

task_default_queue = 'default'
task_queues = (
    Queue('matching', routing_key='matcher.service.celery_tasks.run_matching'),
    Queue('deployment', routing_key='matcher.service.celery_tasks.run_deployment')
)
# CELERY_IMPORTS = ('tasks')
task_ignore_result = False
# broker_url = 'redis://localhost:6379/0'
broker_url = 'amqp://openreview:openreview@localhost:5672/localhost'
result_backend = 'redis://localhost:6379/0'
# CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
task_serializer = 'pickle'
result_serializer = 'pickle'
accept_content = ['pickle', 'application/x-python-serialize']
task_create_missing_queues = True
# result_backend = 'redis://localhost:6379/0'

registry.enable('pickle')
registry.enable('application/x-python-serialize')
