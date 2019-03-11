import time
import uuid
import random
import os
import pickle
import logging
import traceback
import json
from collections import namedtuple

from rafiki.utils.auth import make_superadmin_client
from rafiki.model import load_model_class
from rafiki.meta_store import MetaStore
from rafiki.cache import Cache
from rafiki.config import INFERENCE_WORKER_SLEEP, INFERENCE_WORKER_PREDICT_BATCH_SIZE

logger = logging.getLogger(__name__)

class InvalidInferenceJobError(Exception): pass
class InvalidSubInferenceJobError(Exception): pass
class InvalidTrialError(Exception): pass
class InvalidModelError(Exception): pass

_SubInferenceJob = namedtuple('_SubInferenceJob', ['id'])
_InferenceJob = namedtuple('_InferenceJob', ['id'])
_Trial = namedtuple('_Trial', ['knobs', 'params_dir']) 
_Model = namedtuple('_Model', ['id', 'model_file_bytes', 'model_class']) 

class InferenceWorker(object):
    def __init__(self, service_id, cache=None, meta_store=None, param_store=None):
        if cache is None: 
            cache = Cache()

        if meta_store is None: 
            meta_store = MetaStore()

        self._cache = cache
        self._meta_store = meta_store
        self._param_store = param_store
        self._service_id = service_id
        self._model = None
        self._client = make_superadmin_client()
        
    def start(self):
        (sub_inference_job, inference_job, trial, model) = self._read_worker_info()
        self._sub_inference_job_id = sub_inference_job.id
        self._inference_job_id = inference_job.id
        logger.info('Worker is for sub inference job of ID "{}"'.format(sub_inference_job.id))
        self._client.send_event('sub_inference_job_worker_started', sub_inference_job_id=self._sub_inference_job_id)

        # Add to inference job's set of running workers
        self._cache.add_worker_of_inference_job(self._service_id, self._inference_job_id)
        self._model = self._load_model(trial, model)

        while True:
            (query_ids, queries) = \
                self._cache.pop_queries_of_worker(self._service_id, INFERENCE_WORKER_PREDICT_BATCH_SIZE)
            
            if len(queries) > 0:
                logger.info('Making predictions for queries...')
                logger.info(queries)

                predictions = None
                try:
                    predictions = self._model.predict(queries)
                except Exception:
                    logger.error('Error while making predictions:')
                    logger.error(traceback.format_exc())
                    
                if predictions is not None:
                    logger.info('Predictions:')
                    logger.info(predictions)

                    for (query_id, prediction) in zip(query_ids, predictions):
                        self._cache.add_prediction_of_worker(self._service_id, query_id, prediction)

            time.sleep(INFERENCE_WORKER_SLEEP)

    def stop(self):
        # Remove from inference job's set of running workers
        self._cache.delete_worker_of_inference_job(self._service_id, self._inference_job_id)
        self._client.send_event('sub_inference_job_worker_stopped', sub_inference_job_id=self._sub_inference_job_id)

    def _load_model(self, trial: _Trial, model: _Model):
        logger.info('Loading model class...')
        clazz = load_model_class(model.model_file_bytes, model.model_class)

        logger.info('Running model class setup...')
        clazz.setup()

        logger.info('Loading trained model...')
        model_inst = clazz(**trial.knobs)
        model_inst.load_parameters(trial.params_dir)

        return model_inst

    def _read_worker_info(self):
        logger.info('Reading info for worker...')
        with self._meta_store:
            sub_inference_job = self._meta_store.get_sub_inference_job_by_service(self._service_id)
            if sub_inference_job is None:
                raise InvalidSubInferenceJobError()

            inference_job = self._meta_store.get_inference_job(sub_inference_job.inference_job_id)
            if inference_job is None:
                raise InvalidInferenceJobError()

            trial = self._meta_store.get_trial(sub_inference_job.trial_id)
            if trial is None or trial.params_dir is None: # Must have model saved
                raise InvalidTrialError()
            
            model = self._meta_store.get_model(trial.model_id)
            if model is None:
                raise InvalidModelError()

            return (
                _SubInferenceJob(sub_inference_job.id),
                _InferenceJob(inference_job.id),
                _Trial(trial.knobs, trial.params_dir),
                _Model(model.id, model.model_file_bytes, model.model_class)
            )
