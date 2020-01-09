FROM jupyterhub/jupyterhub:1.1.dev
LABEL maintainer="Human Brain Project <platform@humanbrainproject.eu>"

RUN apt-get update \
 && apt-get install -yq --no-install-recommends \
        git-core \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*


COPY requirements.txt /tmp/
RUN python3 -m pip install --no-cache -r /tmp/requirements.txt
RUN chown 65534 /srv/jupyterhub

# nobody
USER 65534
