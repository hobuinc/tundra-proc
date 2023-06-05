import boto3
import json
import os
import time
import shlex
import uuid

from subprocess import run

LINE_UP = '\033[1A'
LINE_CLEAR = '\x1b[2K'

client = boto3.client('batch')

def get_environment_variables() -> json:
    command = [ "terraform", "output", "--json", "--state", "../../terraform/terraform.tfstate" ]
    return json.loads(run(command, capture_output=True).stdout.decode())

def submit_job(scan_path: str, batch_queue: str, batch_def: str, memory: int) -> None:

    command = f"{scan_path}  s3://grid-dev-lidarscans/Fairbanks-A-TLS/"

    command = shlex.split(command)

    tmpdir = uuid.uuid4()
    return client.submit_job(
        jobName = 'job-test',
        jobQueue = batch_queue,
        jobDefinition = batch_def,

        containerOverrides = {
            'command': command,
            'memory': memory,
            'environment':[
                {
                    "name": "TMPDIR",
                    "value": f"/local/{tmpdir}"
                }
            ]
        }
    )

def wait_for_job(job_id):
    # TODO Get compute env resource info and print

    # TODO get job info and print job status
    while(True):
        statuses = [ { 'id': job['jobId'], 'status': job['status'] } for job in client.describe_jobs(jobs=[job_id])['jobs'] ]
        fin = True
        for s in statuses:
            print(f'| id: {s["id"]} | status: {s["status"]} |')
            if s["status"] in ['RUNNABLE', 'STARTING', 'RUNNING', 'SUBMITTED']:
                fin = False
        if fin == True:
            return
        print(LINE_UP, end=LINE_CLEAR)
        time.sleep(5)

    # TODO print job logs when done
    # from logStreamName in jobInfo?

os.chdir(os.path.dirname(os.path.abspath(__file__)))
env = get_environment_variables()
batch_queue = env['batchJobQueueName']['value']
batch_def = env['batchJobDefinitionArn']['value']


from s3pathlib import S3Path

bucket = S3Path.from_s3_uri('s3://grid-dev-lidarscans/Fairbanks-A-TLS/lasz/')


pivox_pc_output_dir = "pivox-laz-classified"
pivox_raster_output_dir = "pivox-dtm"


def exists(s3path, output_dir, extension):
    name = '.'.join(s3path.basename.split('.')[:-2]) + extension
    path = S3Path.from_s3_uri(f"s3://{bucket.bucket}/Fairbanks-A-TLS/{output_dir}/{name}")

    return path.exists()


for p in bucket.iter_objects().filter(S3Path.ext == ".gz"):

    if 'PIVOX' not in str(p):
        continue
    if not exists(p, pivox_pc_output_dir, '.copc.laz'):

        memory = 2000
        if 'MAIN' in p.basename:
            memory = 15000
        job_id = submit_job(str(p.uri), batch_queue, batch_def, memory)['jobId']

        print(f'Submitting {p.basename}')
