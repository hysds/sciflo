from datetime import datetime
import json
import requests
import backoff
import logging

from hysds.celery import app
from hysds.utils import get_payload_hash
from hysds_commons.job_utils import resolve_hysds_job


# set logger and custom filter to handle being run from sciflo
log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)

class LogFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'id'): record.id = '--'
        return True

logger = logging.getLogger('test_sciflo_chain')
logger.setLevel(logging.INFO)
logger.addFilter(LogFilter())


# backoff settings
BACKOFF_MAX_VALUE = 64
BACKOFF_MAX_TRIES = 10


@backoff.on_exception(backoff.expo,
                      Exception,
                      max_tries=BACKOFF_MAX_TRIES,
                      max_value=BACKOFF_MAX_VALUE)
def run_query(url, idx, query):
    """Query OpenSearch index.
    Note: doc_type parameter removed in OpenSearch 3.0.
    search_type=scan is also deprecated; using scroll API directly.
    """

    query_url = "{}{}/_search?scroll=60s&size=100".format(url, idx)
    logger.info(f"url: {url}")
    logger.info(f"idx: {idx}")
    logger.info(f"query: {json.dumps(query, indent=2)}")
    r = requests.post(query_url, data=json.dumps(query))
    r.raise_for_status()
    scan_result = r.json()
    count = scan_result['hits']['total']
    scroll_id = scan_result['_scroll_id']
    hits = []
    while True:
        r = requests.post('%s/_search/scroll?scroll=60m' % url, data=scroll_id)
        res = r.json()
        scroll_id = res['_scroll_id']
        if len(res['hits']['hits']) == 0:
            break
        hits.extend(res['hits']['hits'])
    return hits


@backoff.on_exception(backoff.expo,
                      Exception,
                      max_tries=BACKOFF_MAX_TRIES,
                      max_value=BACKOFF_MAX_VALUE)
def job_done(url, idx, task_id):
    """Return True when job has transitioned away from 'job-started'."""

    query_status = {
        "query": {
            "term": {
                "task_id": task_id,
            }
        },
        "fields": [ "status" ],
    }
    logger.info(f"query_status: {json.dumps(query_status, indent=2)}")
    res = run_query(url, idx, query_status)
    logger.info(f"got res: {json.dumps(res, indent=2)}")
    status = res[0]['fields']['status'][0]
    logger.info(f"got status: {json.dumps(status, indent=2)}")
    if status == 'job-started':
        raise RuntimeError(f"Job with task ID {task_id} still in 'job-started' state.")
    return True


def create_job(arg, job_queue, wuid=None, job_num=None):
    """Test function for hello world job json creation."""

    if wuid is None or job_num is None:
        raise RuntimeError("Need to specify workunit id and job num.")

    # set job type and disk space reqs
    job_type = "job-hello_world:master"

    # resolve hysds job
    params = {
        "dt": datetime.utcnow().isoformat(),
    }
    job = resolve_hysds_job(job_type, job_queue, priority=0, params=params,
                            job_name="{}-{}".format(job_type, params['dt']),
                            payload_hash=get_payload_hash(params))

    # add workflow info
    job['payload']['_sciflo_wuid'] = wuid
    job['payload']['_sciflo_job_num'] = job_num
    logger.info(f"job: {json.dumps(job, indent=2)}")

    return job


def create_merge_job(arg1, arg2, job_queue, wuid=None, job_num=None):
    """Test function for hello world merge job json creation."""

    if wuid is None or job_num is None:
        raise RuntimeError("Need to specify workunit id and job num.")

    # set job type and disk space reqs
    job_type = "job-hello_world:master"

    # resolve hysds job
    params = {
        "dt": datetime.utcnow().isoformat(),
    }
    job = resolve_hysds_job(job_type, job_queue, priority=0, params=params,
                            job_name="{}-{}".format(job_type, params['dt']),
                            payload_hash=get_payload_hash(params))

    # add workflow info
    job['payload']['_sciflo_wuid'] = wuid
    job['payload']['_sciflo_job_num'] = job_num
    logger.info(f"job: {json.dumps(job, indent=2)}")

    return job


def get_result(result):
    """Evaluator function for processing a job result."""

    logger.info(f"got result: {json.dumps(result, indent=2)}")
    task_id = result[0]
    done = job_done(app.conf['JOBS_ES_URL'], 'job_status-current', task_id)
    query = {
        "query": {
            "term": {
                "task_id": task_id,
            }
        }
    }
    jobs = run_query(app.conf['JOBS_ES_URL'], 'job_status-current', query)
    logger.info(f"got job: {json.dumps(jobs[0], indent=2)}")
    dataset_id = jobs[0]['_source']['job']['job_info']['metrics']['products_staged'][0]['id']
    logger.info(f"got dataset_id: {dataset_id}")
    return dataset_id


def get_result_force_stoppage(result):
    """Evaluator function for processing a job result. Force stoppage."""

    dataset_id = get_result(result)
    raise RuntimeError("Stopping workflow.")
