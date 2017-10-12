import uuid, time
from datetime import timedelta
from pprint import pprint
from urllib import urlopen
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


def test_map(startdate, enddate, segmentBy, arg1, arg2, wuid=None, job_num=None):
    """Test function for map job json creation."""

    if wuid is None or job_num is None:
        raise RuntimeError("Need to specify workunit id and job num.")

    start = getDatetimeFromString(startdate)

    return {
        "job_type": "job:parpython_map_job", 
        "payload": {
            # sciflo tracking info
            "_sciflo_wuid": wuid,
            "_sciflo_job_num": job_num,

            # job params
            "year": start.year,
            "month": start.month,
            "arg1": arg1,
            "arg2": arg2
        }
    }

def test_reduce(results):
    """Test reduce function."""

    reduced_result = []
    for result in results:
        job_url = result['job_url']
        result = urlopen('%s/_stdout.txt' % job_url).read().strip()
        reduced_result.append(result)
    return '\n'.join(reduced_result)

def test_reduce_async(task_ids):
    """Test reduce function."""

    res = GroupResult(id=uuid.uuid4(), results=[AsyncResult(id[0]) for id in task_ids])
    while True:
        ready = res.ready()
        if ready: break
        time.sleep(5)
    return [i for i in res.join(timeout=10.)]

def test_reduce_job(results, wuid=None, job_num=None):
    """Test function for reduce job json creation."""

    if wuid is None or job_num is None:
        raise RuntimeError("Need to specify workunit id and job num.")

    args = []
    for result in results:
        job_url = result['job_url']
        result = urlopen('%s/_stdout.txt' % job_url).read().strip()
        args.append("'%s'" % result)
    
    return {
        "job_type": "job:parpython_reduce_job", 
        "payload": {
            # sciflo tracking info
            "_sciflo_wuid": wuid,
            "_sciflo_job_num": job_num,

            # job params
            "results": ' '.join(args),
        }
    }

def get_reduce_result(result):
    """Test function for processing a reduced job result."""

    job_url = result['job_url']
    job_res = urlopen('%s/_stdout.txt' % job_url).read().strip()
    return job_res
