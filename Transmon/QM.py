import ipywidgets as widgets
from IPython.display import HTML
import time
import threading
import os
import importlib
from qm import QuantumMachinesManager
import zmq

QM_Router_IP = "129.175.113.167"
cluster_name = "Cluster_1"

# QM address
QM_Router_IP = "129.175.113.167"
cluster_name = "Cluster_1"
qmm = QuantumMachinesManager(host=QM_Router_IP, cluster_name=cluster_name, log_level="ERROR", octave_calibration_db_path=os.getcwd()) 

# Local address for queue monitoring
host = "127.0.0.1"
port1 = "5556"
port2 = "5557"
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.connect(f"tcp://{host}:{port1}")

class Job(threading.Thread):
    def __init__(self, qmprog):
        self.output = widgets.Output()
        qm_list =  qmm.list_open_qms()
        qm = qmm.get_qm(qm_list[0])
        self.output.append_stdout(f"Sending job to {qm.id}...")
        self.job = qm.queue.add(qmprog)
        while self.job.status=="loading":
            time.sleep(0.1)
        super().__init__()
        self.output.append_stdout("loaded\n")
        self.qm = qm
        self.button_abort = widgets.Button(description='Abort')
        self.button_abort.on_click(self.abort_clicked)
        self.job_table = widgets.HTML(value = "")
        self.layout = [self.button_abort, self.output, self.job_table]
        self.abort = False

    def abort_clicked(self, button):
        self.abort = True

    def __getattr__(self, attr):
        return getattr(self.job,attr)

    def display(self, table):
        out = "<table>"
        for job in table:
            waiting_time = f"{time.time()-job["time"]:.0f}" if job["time"] else "--"
            if job["id"]==self.job.id:
                out += f"""<tr><td><b>{job["status"].capitalize()}</b></td><td><b>{job["id"]}</b></td><td><b>{job["user"] or os.environ["JUPYTERHUB_USER"]}</td><td><b>{waiting_time}s</b></td></tr>"""
            else:
                out += f"""<tr><td>{job["status"].capitalize()}</td><td>{job["id"]}</td><td>{job["user"] or "unknown"}</td><td>{waiting_time}s</td></tr>"""
        out += "</table>"
        self.job_table.value = out

    def run(self):
        poller = zmq.Poller()
        socket_info = context.socket(zmq.SUB)
        socket_info.connect(f"tcp://{host}:{port2}")
        socket_info.subscribe("JOBTABLE")
        poller.register(socket_info, zmq.POLLIN)
        if self.job.status=="pending"
            status = {"status":"pending", "time": time.time(), "user":os.environ["JUPYTERHUB_USER"], "id":self.job.id, "qm_id":self.qm.id}
            socket.send_string("JOB", flags=zmq.SNDMORE)
            socket.send_json(status)
        while self.job.status=="pending":
            self.output.append_stdout(f"Position in queue {self.job.position_in_queue()} \r")
            evts = dict(poller.poll(timeout=200))
            if socket_info in evts:
                topic = socket_info.recv_string()
                jobtable = socket_info.recv_json()
                self.display(jobtable)
            if self.abort:
                self.job.cancel()
                self.output.append_stdout("Job has been canceled\n")
                self.job_table.value = ""
                return
        self.job = self.job.wait_for_execution()
        if self.job.status=="running"
            self.output.append_stdout("Job is running...\n")
            status = {"status":"running", "time": time.time(), "user":os.environ["JUPYTERHUB_USER"], "id":self.job.id, "qm_id":self.qm.id}
            socket.send_string("JOB", flags=zmq.SNDMORE)
            socket.send_json(status)
        while self.job.status=="running":
            evts = dict(poller.poll(timeout=200))
            if socket_info in evts:
                topic = socket_info.recv_string()
                jobtable = socket_info.recv_json()
                self.display(jobtable)
            if self.abort:
                self.job.halt()
                self.output.append_stdout("Job has been halted\n")
                self.job_table.value = ""
                return
        self.output.append_stdout("Job has finished\n")
        self.job_table.value = ""

        
        
def addjob(qmprog):
    qm_list =  qmm.list_open_qms()
    qm = qmm.get_qm(qm_list[0])
    print(f"Sending job to {qm.id}")
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