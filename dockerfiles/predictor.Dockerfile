FROM ubuntu:16.04

RUN apt-get update && apt-get -y upgrade

# Install conda with pip and python 3.6
ARG CONDA_ENVIORNMENT
RUN apt-get -y install curl bzip2 \
  && curl -sSL https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh \
  && bash /tmp/miniconda.sh -bfp /usr/local \
  && rm -rf /tmp/miniconda.sh \
  && conda create -y --name $CONDA_ENVIORNMENT python=3.6 \
  && conda clean --all --yes
ENV PATH /usr/local/envs/$CONDA_ENVIORNMENT/bin:$PATH
RUN pip install --upgrade pip
ENV PYTHONUNBUFFERED 1

ARG DOCKER_WORKDIR_PATH
RUN mkdir -p $DOCKER_WORKDIR_PATH
WORKDIR $DOCKER_WORKDIR_PATH
ENV PYTHONPATH $DOCKER_WORKDIR_PATH

# Install python dependencies
COPY rafiki/utils/requirements.txt rafiki/utils/requirements.txt
RUN pip install -r rafiki/utils/requirements.txt
COPY rafiki/meta_store/requirements.txt rafiki/meta_store/requirements.txt
RUN pip install -r rafiki/meta_store/requirements.txt
COPY rafiki/client/requirements.txt rafiki/client/requirements.txt
RUN pip install -r rafiki/client/requirements.txt
COPY rafiki/cache/requirements.txt rafiki/cache/requirements.txt
RUN pip install -r rafiki/cache/requirements.txt
COPY rafiki/predictor/requirements.txt rafiki/predictor/requirements.txt
RUN pip install -r rafiki/predictor/requirements.txt

COPY rafiki/ rafiki/
COPY scripts/ scripts/

EXPOSE 3003

CMD ["python", "scripts/start_predictor.py"]