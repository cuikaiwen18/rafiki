import os
from rafiki.utils.service import run_service
from rafiki.meta_store import MetaStore
from rafiki.constants import ServiceType

# Run install command
install_command = os.environ.get('WORKER_INSTALL_COMMAND', '')
exit_code = os.system(install_command)
if exit_code != 0: 
    raise Exception('Install command gave non-zero exit code: "{}"'.format(install_command))

worker = None

def start_service(service_id, service_type):
    global worker

    if service_type == ServiceType.TRAIN:
        from rafiki.worker.train import TrainWorker
        worker = TrainWorker(service_id)
        worker.start()
    elif service_type == ServiceType.INFERENCE:
        from rafiki.worker.inference import InferenceWorker
        worker = InferenceWorker(service_id)
        worker.start()
    else:
        raise Exception('Invalid service type: {}'.format(service_type))

def end_service(service_id, service_type):
    global worker
    if worker is not None:
        worker.stop()    

meta_store = MetaStore()
run_service(meta_store, start_service, end_service)
