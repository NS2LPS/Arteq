import importlib
import threading

def reload_qm(output,config):
    with output:
        importlib.reload(config)
        qm = qmm.open_qm(config.config)
        print(f'{time.asctime()} QM is ready with id {qm.id}')

def calibrate_qm(output,config,cal_qubit=True,cal_resonator=True):
    with output:
        importlib.reload(config)
        qm = qmm.open_qm(config.config)
        if cal_qubit:
            caldict = {config.qubit_LO: [config.qubit_IF,]}
            print(f'Calibrating qubit at {config.qubit_LO/1e6:.1f} + {config.qubit_IF/1e6:.1f} MHz')
            qm.calibrate_element('qubit',caldict)
            print('Done')
        if cal_resonator:
            caldict = {config.resonator_LO: [config.resonator_IF,]}
            print(f'Calibrating resonator at {config.resonator_LO/1e6:.1f} + {config.resonator_IF/1e6:.1f} MHz')
            qm.calibrate_element('resonator',caldict)
            print('Done')
        qm = qmm.open_qm(config.config)
        print(f'{time.asctime()} QM is ready with id {qm.id}')

class QueueMonitor(threading.Thread):
    def __init__(self, output, QM_label, job_table):
        super().__init__()
        self.output = output
        self.job_table = job_table
        self.QM_label = QM_label
        self.keeprunning = True
    def run(self):
        while self.keeprunning:
            self.parse_queue()
            time.sleep(0.1)
        self.output.append_stdout("Done\n")
    def stop(self):
        self.keeprunning = False
    def kill(self):
        try:
            qm_list = qmm.list_open_qms()
            qm = qmm.get_qm(qm_list[0])
        except:
            qm = None
        if qm:
            job = qm.get_running_job()
            if job:
                job.halt()
    def parse_queue(self):
        try:
            qm_list = qmm.list_open_qms()
            qm = qmm.get_qm(qm_list[0])
        except:
            qm = None
        if qm:
            try:
                self.QM_label.value = f"Jobs on {qm.id}"
                table = []
                for job in qm.queue.pending_jobs:
                    table.append(f"""<tr><td>Pending</td><td>{job.id}</td></tr>""")
                job = qm.get_running_job()
                if job:
                    table.append(f"""<tr><td>Running</td><td>{job.id}</td></tr>""")
                rows = " ".join(table)
                self.job_table.value = f"<table>{rows}</table>"
            except:
                self.job_table.value = "<p>Error while parsing the queue</p>"
        else:
            self.QM_label.value = "No QM running"