from IPython.display import display
import ipywidgets as widgets
import time
from matplotlib import pyplot as plt
import numpy as np
import config_qubit as config

import zmq
import os

host = "127.0.0.1"
port = "5555"

ctx = zmq.Context()
socket = ctx.socket(zmq.PUB)
socket.connect(f"tcp://{host}:{port}")

phase_delay = 290e-9

# Real time monitoring and plotting function
def update(pp, n_avg, job, dfs, results, ax, l_modulous, l_phase):
    while results.is_processing():
        # Fetch results
        I, Q, iteration = results.fetch_all()
        theta = dfs*phase_delay*2*np.pi
        Ir = 1e4*(np.cos(theta)*I-np.sin(theta)*Q)
        Qr = 1e4*(np.sin(theta)*I+np.cos(theta)*Q)
        S = Ir + 1j * Qr
        R = 20*np.log10(np.abs(S))-25  # Amplitude
        phase = np.unwrap(np.angle(S))*180/np.pi  # Phase
        # Update plot
        l_modulous.set_ydata(R)
        rescale(ax[0],R)
        l_phase.set_ydata(phase)
        rescale(ax[1],phase)
        # Progress bar
        pp.update(iteration, n_avg)
        # Stop if requested
        if not pp.keeprunning:
            break
    job.halt()

# Real time monitoring and plotting function
def updateIQ(pp, n_avg, job, results, ax, l_I, l_Q):
    while results.is_processing():
        # Fetch results
        I, Q, iteration = results.fetch_all()
        # Update plot
        theta = config.resonator_IF*phase_delay*2*np.pi # TOF correction
        Ir = 1e4*(np.cos(theta)*I-np.sin(theta)*Q)
        Qr = 1e4*(np.sin(theta)*I+np.cos(theta)*Q)
        l_I.set_ydata(Ir)
        rescale(ax[0], Ir)
        l_Q.set_ydata(Qr)
        rescale(ax[1], Qr)
        # Progress bar
        pp.update(iteration, n_avg)
        # Stop if requested
        if not pp.keeprunning:
            break
    job.halt()

    
def rot(I,Q):
    theta = -292*np.pi/180
    return I*np.cos(theta)-Q*np.sin(theta) , I*np.sin(theta)+Q*np.cos(theta)


# Real time monitoring and plotting function
def updatehist(pp, n_avg, job, results, ax, l_IQ0, l_IQ1):
    while results.is_processing():
        # Fetch results
        I0, Q0, I1, Q1, iteration = results.fetch_all()
        # Update plot
        nm = min(len(I0),len(I1),len(Q0),len(Q1))
        I0r, Q0r = rot(I0[:nm]*1e4,Q0[:nm]*1e4)
        I1r, Q1r = rot(I1[:nm]*1e4,Q1[:nm]*1e4)
        l_IQ0.set_data(I0r,Q0r)
        l_IQ1.set_data(I1r,Q1r)
        # Progress bar
        pp.update(iteration, n_avg)
        # Stop if requested
        if not pp.keeprunning:
            break
    job.halt()    

def addjob(qmprog, qm):
    # Send the QUA program to the OPX, which compiles and executes it
    job = qm.queue.add(qmprog)
    # Wait for job to be loaded
    while job.status=="loading":
        print("Job is loading...")
        time.sleep(0.1)
    # Wait until job is running
    time.sleep(0.1)
    status = {"status":"pending", "time": time.time(), "user":os.environ["JUPYTERHUB_USER"], "id":job.id,}
    socket.send_string("JOB", flags=zmq.SNDMORE)
    socket.send_json(status)
    while job.status=="pending":
        q = job.position_in_queue()
        if q>0:
            print("Position in queue",q,end='\r')
        time.sleep(0.1)
    job=job.wait_for_execution()
    print("\nJob is running")
    status = {"status":"running", "time": time.time(), "user":os.environ["JUPYTERHUB_USER"], "id":job.id,}
    socket.send_string("JOB", flags=zmq.SNDMORE)
    socket.send_json(status)
    return job
    
def rescale(ax,data):
    ymin,ymax=ax.get_ylim()
    dmin = data.min()
    dmax = data.max()
    delta = dmax-dmin
    if dmin<ymin or dmax>ymax:
        ax.set_ylim(dmin-0.05*delta, dmax+0.05*delta)
        
class ProgressPlot:
    def __init__(self):
        self.progress = widgets.FloatProgress(value=0.0, min=0.0, max=1.0)
        self.progress_label = widgets.Label(value="??/??")
        self.button = widgets.Button(description='Abort',)
        self.button.on_click(self.stop)
        self.keeprunning = True
        with plt.ioff():
            self.fig = plt.figure()
    def stop(self,b):
        self.keeprunning = False
    def update(self,i,total):
        self.progress.value = float(i+1)/total
        self.progress_label.value = f"{i+1}/{total}"
        self.fig.canvas.draw_idle()
    def show(self):
        display(self.fig.canvas,widgets.HBox([self.button,self.progress,self.progress_label]))