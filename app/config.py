import os
import redis

REDIS_IP = os.environ.get('REDIS_HOST_PERSON_DETECTOR', 'redis')
REDIS_TASK_DB = {
    'host': REDIS_IP,
    'port': os.environ.get('REDIS_PORT_PERSON_DETECTOR', '6379'),
    'db': os.environ.get('REDIS_DB_PERSON_DETECTOR', '1')
}
REDIS_RESULT_DB = {
    'host': REDIS_IP,
    'port': os.environ.get('REDIS_PORT_PERSON_DETECTOR', '6379'),
    'db': os.environ.get('REDIS_DB_PERSON_DETECTOR', '1')
}
task_queue_conn_pool = redis.ConnectionPool (
    host=REDIS_TASK_DB['host'],
    port=REDIS_TASK_DB['port'],
    db=REDIS_TASK_DB['db'],
    socket_keepalive=True
)
TASK_LIST = os.environ.get('REDIS_INPUT_QUEUE_PERSON_DETECTOR', 'person_frames')
RESULT_LIST = os.environ.get('REDIS_OUTPUT_QUEUE_PERSON_DETECTOR', 'person_results')
LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH_PERSON_DETECTOR', '/root/jarvis-consumer/logs/person_detector.log')
PROCESSING_FPS = os.environ.get('PERSON_DETECTOR_FPS', 30)