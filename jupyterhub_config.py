from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPClientError

DRIVE_URL = 'https://drive-dev.humanbrainproject.eu'
DRIVE_TOKEN_URL = DRIVE_URL + '/oauth/token'

c.JupyterHub.authenticator_class = 'oauthenticator.generic.GenericOAuthenticator'
c.Authenticator.enable_auth_state = True

c.KubeSpawner.extra_containers = [{
    "name": "seadrive-sidecar",
    "image": "docker.io/villemai/seadrive-sidecar:v0.0.4",
    "command": ["watch", "-n", "5", "date"],
    "env": [{'name': 'TERM', 'value': 'xterm'}],
    # "securityContext": {
    #     "capabilities": {
    #         "add": ["SYS_ADMIN"],
    #     },
    # },
    "volumeMounts": [
        {
            "name": "mnt-{username}",
            "mountPath": "/data/seafile",
            # "mountPropagation": "Bidirectional",
        },
        {
            "name": "seadrive-{username}-conf",
            "mountPath": "/mnt/secrets/",
            "readOnly": True,
        },
    ],
}]

c.KubeSpawner.volumes = [
    {
        "name": "mnt-{username}",
        "emptyDir": {},
    },
    {
        "name": "seadrive-{username}-conf",
        "secret":
        {
            "secretName": "seadrive-{username}-conf",
        },
    },
]
c.KubeSpawner.volume_mounts = [{
    "name": "mnt-{username}",
    "mountPath": "/mnt/user",
}]

c.KubeSpawner.environment = { 'JUPYTER_ENABLE_LAB': 'true' }

async def clb_pre_spawn(spawner):
    user = spawner.user
    spawner.log.error("clb_pre_spawn_start called for %s" % user.name)
    auth_state = await user.get_auth_state()
    spawner.log.error("clb_pre_spawn_start auth_state: %s, [ %s ]" % (repr(auth_state), str(auth_state)))
    drive_token = await get_drive_token(auth_state)
    secret = generate_drive_config(DRIVE_URL, user.name, drive_token)
    spawner.api.create_namespaced_secret('jupyterhub-dev', secret)
    spawner.log.error("Created secret for %s" % user.name)
    return user


async def get_drive_token(auth_state: dict) -> str:
    client = AsyncHTTPClient()
    request = HTTPRequest(DRIVE_TOKEN_URL,
                          headers={'Authorization': 'Bearer {token}'.format(
                              token=auth_state['access_token'])},
                          connect_timeout=2.0,
                          request_timeout=2.0
    )
    resp = await client.fetch(request)
    return resp.body

c.KubeSpawner.pre_spawn_hook = clb_pre_spawn

## Create secrets for drive parameters.
## https://github.com/jupyterhub/kubespawner/issues/110
from kubernetes.client.models import (
    V1ObjectMeta,
    V1Secret
)

SEADRIVE_CONF_TPL = '''\
[account]
server = {url}
username = {username}
token = {token}
is_pro = false

[cache]
size_limit = 5GB
clean_cache_interval = 4
'''

def generate_drive_config(url, username, token):
    data = {
        'seadrive.conf': SEADRIVE_CONF_TPL.format(url=url, username=username, token=token)
    }
    metadata = V1ObjectMeta(name='seadrive-{username}-conf'.format(username=username),
                            annotations={'username': username})
    secret = V1Secret(string_data=data, metadata=metadata)
    return secret
