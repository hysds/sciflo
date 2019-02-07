import uuid, time, types, json, hashlib
from datetime import timedelta
from pprint import pprint
from urllib.request import urlopen
from celery.result import AsyncResult, GroupResult

from sciflo.utils.timeUtils import getDatetimeFromString


def date_segmenter(startdate, enddate, segmentBy):
    """
    Return date segments between startdate and enddate segmented by
    the number of days.
    """

    start = getDatetimeFromString(startdate)
    end = getDatetimeFromString(enddate)

    start_segments = []
    end_segments = []
    day_segments = []
    t1 = start
    td = timedelta(days=segmentBy)
    while t1 <= end:
        t2 = t1 + td
        start_segments.append(t1.isoformat())
        if t2 > end:
            end_segments.append(end.isoformat())
        else:
            end_segments.append(t2.isoformat())
        day_segments.append(segmentBy)
        t1 = t2
    return start_segments, end_segments, day_segments


def create_map_job(startdate, enddate, segmentBy, arg1, arg2, wuid=None, job_num=None):
    """Test function for map job json creation."""

    if wuid is None or job_num is None:
        raise RuntimeError("Need to specify workunit id and job num.")

    start = getDatetimeFromString(startdate)

    return {
        "job_type": "job:parpython_map_job", 
        "job_queue": "factotum-job_worker-small",
        "payload": {
            # sciflo tracking info
            "_sciflo_wuid": wuid,
            "_sciflo_job_num": job_num,
            "_command": "/usr/bin/echo {} {} {} {}".format(start.year, start.month, arg1, arg2),

            # job params
            "year": start.year,
            "month": start.month,
            "arg1": arg1,
            "arg2": arg2
        }
    }


def create_reduce_job(results, wuid=None, job_num=None):
    """Test function for reduce job json creation."""

    if wuid is None or job_num is None:
        raise RuntimeError("Need to specify workunit id and job num.")

    args = [ result['payload_id'] for result in results ]
    return {
        "job_type": "job:parpython_reduce_job", 
        "job_queue": "factotum-job_worker-large",
        "payload": {
            # sciflo tracking info
            "_sciflo_wuid": wuid,
            "_sciflo_job_num": job_num,
            "_command": "/usr/bin/echo {}".format(' '.join(args)),

            # job params
            "results": ' '.join(args),
        }
    }


def get_reduce_job_result(result):
    """Test function for processing a reduced job result."""

    print(("got result: {}".format(json.dumps(result, indent=2))))
    return result['payload_id']


def join_map_jobs(task_ids):
    """Test reduce function that manually joins all mapped jobs."""

    print(("task_ids: {}".format(json.dumps(task_ids, indent=2))))
    res = GroupResult(id=uuid.uuid4(), results=[AsyncResult(id[0]) for id in task_ids])
    while True:
        ready = res.ready()
        if ready: break
        time.sleep(5)
    results = []
    for r in res.join(timeout=10.):
        # deduped job?
        if isinstance(r, (list, tuple)):
            # build resolvable result
            task_id = r[0]
            results.append({ 'uuid': task_id,
                             'job_id': task_id,
                             'payload_id': task_id,
                             'status': 'job-deduped' })
        else: results.append(r)
    args = [ result['payload_id'] for result in results ]
    return args


def reduce_map_jobs(results):
    """Test reduce function."""

    return hashlib.md5(" ".join(results)).hexdigest()
