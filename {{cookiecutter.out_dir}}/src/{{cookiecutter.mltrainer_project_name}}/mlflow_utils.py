#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import json
import os
import re
import shutil
from enum import Enum
from pathlib import Path

from mlflow.tracking import MlflowClient
from tensorflow.keras.models import load_model

DATA_PATH = Path(os.environ.get("DATA_PATH", "../data"))

STATUS_FILE = DATA_PATH / "mlflow_status.json"

MODEL_URI_RE = re.compile("(?P<scheme>.*):/(?P<model>[^/]+)/(?P<stage>.*)$", flags=re.I)
SOURCE_RE = re.compile(
    "s3://(?P<bucket>[^/]+)/(?P<experimentid>[^/]+)/(?P<runid>["
    "^/]+)/artifacts/(?P<path>.*$)"
)


class ModelNotFound(Exception):
    """."""


def rm(*d):
    if not isinstance(d, (tuple, list)):
        d = [d]
    for c in d:
        if not os.path.exists(c):
            continue
        if os.path.isdir(c):
            shutil.rmtree(c)
        else:
            os.unlink(c)


def create_dirs(*d):
    if not isinstance(d, (tuple, list)):
        d = [d]
    for c in d:
        if not os.path.exists(c):
            os.makedirs(c)


def find_model(mlflowdir):
    found = False
    for i in ["tfmodel", "model"]:
        mdldir = os.path.join(mlflowdir, "model", i)
        if os.path.exists(mdldir):
            found = True
            break
    if not found:
        raise ModelNotFound(f"{mlflowdir}: model not found")
    return mdldir


def download_and_load_models(models, client=None, load=None, use_cached=False):
    """
    Load model from mlflow registry

    :param use_cached: if set, use cached downloaded model
    :param autoload: globally enable/disable model autoloading after download
    :param client: mlflow client instance or None
        model: loaded model
        :models: model descriptors to load from mlflow tracking server
         Await in parameters a list of dict:
           [{
             'uri': 'models:/uri/Stage'
             'use_cached': if set override global use_cached
             'path': '/local/path/to/Save/Downloadto'
             'load' if set: callable to load the model, default to keras
                    set to False to disable this specific model loading
           }]

    return the models dict with injected data:
        loaded: True if loading has been done
        model: model object if loaded
        downloaded: True if downloading has been done
        model_path: path from within the download that was considered as a model
    """
    if client is None:
        client = MlflowClient()
    for m in [a for a in models]:
        mdata = models[m]
        uri = mdata["uri"]
        mdata["model_path"] = None
        mdata["model"] = None
        mdata["loaded"] = False
        mdata["downloaded"] = False
        match = MODEL_URI_RE.search(uri)
        gr = match.groupdict()
        version = [
            v
            for v in client.search_registered_models(
                filter_string=f"name='{gr['model']}'"
            )[0].latest_versions
            if v.current_stage == gr["stage"]
        ][0]
        vmatch = SOURCE_RE.search(version.source)
        vgr = vmatch.groupdict()
        mlflowdir = mdata["path"]
        rm(mlflowdir)
        muse_cached = mdata.get("use_cached", use_cached)
        try:
            if not muse_cached:
                raise ModelNotFound("force download")
            mdata["model_path"] = find_model(mlflowdir)
        except ModelNotFound:
            create_dirs(mlflowdir)
            client.download_artifacts(vgr["runid"], vgr["path"], mlflowdir)
            mdata["model_path"] = find_model(mlflowdir)
            mdata["downloaded"] = True
        aload = mdata.get("load", load)
        if aload is None:
            aload = load_model
        if not aload:
            continue
        mdata["model"] = aload(mdata["model_path"])
        mdata["loaded"] = True
    return models


def config_cli(parser):
    parser.add_argument(
        "--model_name",
        type=str,
        default="brand_matching_trainer",
        help="which model to register to",
    )
    parser.add_argument(
        "--output_status",
        type=str,
        default="mlflow_status.json",
        help="output status path",
    )


class Status(Enum):
    FAILED = 0
    NOT_VALIDATED = 1
    VALIDATED = 2


def register_model(mlflow, model, model_path=None, validated=True):
    status, version = None, None
    if model_path is None:
        model_path = "model"
    model_path_uri = mlflow.get_artifact_uri(model_path)
    if validated:
        status = Status.VALIDATED
    else:
        status = Status.NOT_VALIDATED
    version = mlflow.register_model(model_path_uri, model)
    return status, version


def write(status_file=None, status=Status.NOT_VALIDATED, model_name=None, version=None):
    if not status_file:
        status_file = STATUS_FILE
    iversion = None
    if version is not None:
        iversion = version.version
    payload = {
        "status_name": status.name,
        "status_code": status.value,
        "status": status.name.lower(),
        "model_name": model_name,
        "version": iversion,
    }
    with open(status_file, "w") as fic:
        fic.write(json.dumps(payload))


#
# vim:set et sts=4 ts=4 tw=80:
