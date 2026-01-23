import time
import config_00 as config
import zmq
import os

host = "127.0.0.1"
port = "5555"

ctx = zmq.Context()
socket = ctx.socket(zmq.PUB)
socket.connect(f"tcp://{host}:{port}")

def addjob(qmprog, qm):
    # Send the QUA program to the OPX, which compiles and executes it
    job = qm.queue.add(qmprog)
    # Wait for job to be loaded
    while job.status=="loading":
        print("Job is loading...")
        time.sleep(0.1)
    # Wait until job is running
    time.sleep(0.1)
    status = {"status":"pending", "time": time.time(), "user":os.environ["JUPYTERHUB_USER"], "id":job.id, "qm_id":qm.id}
    socket.send_string("JOB", flags=zmq.SNDMORE)
    socket.send_json(status)
    while job.status=="pending":
        q = job.position_in_queue()
        if q>0:
            print(job.id,"Position in queue",q,end='\r')
        time.sleep(0.1)
    job=job.wait_for_execution()
    print(f"\nJob {job.id} is running")
    status = {"status":"running", "time": time.time(), "user":os.environ["JUPYTERHUB_USER"], "id":job.id, "qm_id":qm.id}
    socket.send_string("JOB", flags=zmq.SNDMORE)
    socket.send_json(status)
    return job
    