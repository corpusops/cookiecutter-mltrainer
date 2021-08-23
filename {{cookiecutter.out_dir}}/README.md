# Initialise your development environment
- Only now launch pycharm and configure a project on this working directory

All following commands must be run only once at project installation.


## First clone

```sh
git clone --recursive {{cookiecutter.git_project_url}}
{%if cookiecutter.use_submodule_for_deploy_code-%}git submodule init # only the fist time
git submodule update --recursive{%endif%}
```

## Before using any ansible command: a note on sudo
If your user is ``sudoer`` but is asking for you to input a password before elavating privileges,
you will need to add ``--ask-sudo-pass`` and maybe ``--become`` to any of the following ``ansible alike`` commands.


## Install corpusops
If you want to use ansible, or ansible vault (see passwords) or install docker via automated script
```sh
.ansible/scripts/download_corpusops.sh
.ansible/scripts/setup_corpusops.sh
```

## Install docker and docker compose
if you are under debian/ubuntu/mint/centos you can do the following:
```sh
local/*/bin/cops_apply_role --become \
    local/*/*/corpusops.roles/services_virt_docker/role.yml
```

... or follow official procedures for
  [docker](https://docs.docker.com/install/#releases) and
  [docker-compose](https://docs.docker.com/compose/install/).


## Update corpusops
You may have to update corpusops time to time with

```
./control.sh up_corpusops
```

## Configuration

Use the wrapper to init configuration files from their ``.dist`` counterpart
and adapt them to your needs.

```bash
./control.sh init
```

**Hint**: You may have to add `0.0.0.0` to `ALLOWED_HOSTS` in `local.py`.

## Login to the app docker registry

You need to login to our docker registry to be able to use it:


```bash
docker login {{cookiecutter.docker_registry}}  # use your gitlab user
```

{%- if cookiecutter.registry_is_gitlab_registry %}
**⚠️ See also ⚠️** the
    [project docker registry]({{cookiecutter.git_project_url.replace('ssh://', 'https://').replace('git@', '')}}/container_registry)
{%- else %}
**⚠️ See also ⚠️** the makinacorpus doc in the docs/tools/dockerregistry section.
{%- endif%}

# Use your development environment

## Update submodules

Never forget to grab and update regulary the project submodules:

```sh
git pull
{% if cookiecutter.use_submodule_for_deploy_code %}
git submodule init # only the fist time
git submodule update --recursive
{%endif%}
```

## Control.sh helper

You may use the stack entry point helper which has some neat helpers but feel
free to use docker command if you know what your are doing.

```bash
./control.sh usage # Show all available commands
```

### Launch a full mlflow local server
- You need a full mlflow models server with logging and models registry up and running to use the models, don't panic, it's pretty easy.
- Clone berangere django app but do not install it, you just need the base code to install the registry
- The Registry should be available :
    - Without auth (direct access)
        - on your host : http://localhost:5000
        - Inside your containers: http://host.docker.internal:5000
    - With auth (default mlflow/mlflow but change it on prod)
        - on your host : http://localhost:5001
        - Inside your containers: http://host.docker.internal:5001
- You can override any configuration that is located inside `local/docker-mlflow/rootfs/docker-compose.yml` inside the bundled registry by editing the `local/docker-mlflow/rootfs/.env` and restarting the mlflow stack
- *(you should not do that as values are correct by default)* example :

    ```sh
    MLFLOW__PORT=5010
    MLFLOW__NGINX_PORT=5011
    ```
- launch it

    ```sh
    ./control.sh up_registry
    ```
- You will have a full mlflow server running under port 5000 without auth and with auth on port 5001.
- The artifacts are stored on minio (port 9000)
- Passwords are on the docker-compose.yml (mlflow/mlflow for mlflow and minio/minio123 for minio)
- stop it

    ```sh
    ./control.sh down_registry
    ```

## Build the train stack
After a last verification of the files, to run with docker, just type:

```bash
./control.sh build
```

or if the image is released, instead of building it, you can only download.

```bash
./control.sh pull
```

## train model
- Models to train are the one listed inside the `MODEL_PATHS` variable
- mlprojects run in an image where /code is not a volume, you may need to rebuild whatever is not in your `src` `tests` subdirectories each time you modify it !
- Assuming that you have a tracking server running on yourhost:5000 (by example on using the project bundle one)
- Run a train

    ```sh
    ./control.sh train
    ```

**⚠️ Remember ⚠️** to use `./control.sh up` to start the stack before.

## Start a shell inside the {{cookiecutter.app_type}} container

- for user shell

    ```sh
    ./control.sh usershell
    mlflow run --no-conda /code/src/{{cookiecutter.lname}}
    # or (equivalent)
    mlflow run --no-conda {{cookiecutter.lname}}
    ```
- for root shell

    ```sh
    ./control.sh shell
    ```

**⚠️ Remember ⚠️** to use `./control.sh up` to start the stack before.

## Run plain docker-compose commands

- Please remember that the ``CONTROL_COMPOSE_FILES`` env var controls which docker-compose configs are use (list of space separated files), by default it uses the dev set.

    ```sh
    ./control.sh dcompose <ARGS>
    ```
## Serve mlflow hosted tensorflow models

Add models on your `.env`

```sh
# comma separated list of models to serve
MLFLOW_MODELS=model1;model2
```

```sh
docker-compose -f docker-compose.serving.yml up -d
```

Read compose file if you want to edit more settings (everything is configurable via `.env`)

This will launch tensorflowserving and attack your models hosted on the mlflow s3 backend. By default, it should be available on ports 8500 (grpc) & 8501 (rest).


## Rebuild/Refresh local docker image in dev

```sh
./control.sh buildimages
```

## Running heavy session
Like for installing and testing packages without burning them right now in requirements.<br/>
You will need to add the network alias and maybe stop the mltrainer worker

```sh
./control.sh stop {{cookiecutter.app_type}}
services_ports=1 ./control.sh usershell
python dosomething.py
```

## Run tests

```sh
./control.sh tests
# also consider: linting|coverage
```

**⚠️ Remember ⚠️** to use `./control.sh up` to start the stack before.


Html output is available in `data/htmlcov`

## File permissions
If you get annoying file permissions problems on your host in development, you can use the following routine to (re)allow your host
user to use files in your working directory


```sh
./control.sh open_perms_valve
```

## Refresh Pipenv.lock

- Use

    ```
    ./control.sh usershell sh -ec "cd requirements && pipenv lock"
    ```

## Docker volumes

Your application extensivly use docker volumes. From times to times you may
need to erase them (eg: burn the db to start from fresh)

```sh
docker volume ls  # hint: |grep \$app
docker volume rm $id
```

## Reusing a precached image in dev to accelerate rebuilds
Once you have build once your image, you have two options to reuse your image as a base to future builds, mainly to accelerate buildout successive runs.

- Solution1: Use the current image as an incremental build: Put in your .env

    ```sh
    {{cookiecutter.app_type.upper()}}_BASE_IMAGE={{ cookiecutter.docker_image }}:latest-dev
    ```

- Solution2: Use a specific tag: Put in your .env

    ```sh
    {{cookiecutter.app_type.upper()}}_BASE_IMAGE=a tag
    # this <a_tag> will be done after issuing: docker tag registry.makina-corpus.net/mirabell/chanel:latest-dev a_tag
    ```

## Integrating an IDE
- <strong>DO NOT START YET YOUR IDE</strong>
- Start the stack, but specially stop the app container as you will
  have to separatly launch it wired to your ide

    ```sh
    ./control.sh up
    ./control.sh down {{cookiecutter.app_type}}
    ```

### Using pycharm

- Tips and tricks to know:
    - the python interpreter (or wrapper in our case) the pycharm glue needs should be named `python.*`
    - Paths mappings are needed, unless pycharm will execute in its own folder under `/opt` totally messing the setup
    - you should have the latest (2021-01-19) code of the common glue (`local/mltrainer-deploy-common`) for this to work
- Goto settings (CTRL-ALT-S)
    - Create a `docker-compose` python interpreter:
        - compose files: `docker-compose.yml`, `docker-compose-dev.yml`
        - python interpreter: `/code/sys/python-pycharm`
        - service: `mltrainer`
        - On project python interpreter settings page, set:
            - Path Mapping: Add with browsing your local:`src` , remote: `/code/src` <br/>
              (you should then see `<Project root>/src→/code/src`)
    - on language/frameworks → mltrainer
        - enable mltrainer support
        - set project root to `src` folder
        - browse to your `dev.py` settings file
    - Add a debug configuration
        - host: `0.0.0.0`


### Using VSCode

#### Get the completion and the code resolving for bundled dependencies wich are inside the container
- Whenever you rebuild the image, you need to refresh the files for your IDE to complete bundle dependencies

    ```sh
    ./control.sh get_container_code
    ```
#### IDE settings

- Add to your .env and re-run ``./control.sh build {{cookiecutter.app_type}}``

```sh
WITH VISUALCODE=1
```

```python
import pydevd_pycharm;pydevd_pycharm.settrace('host.docker.internal', port=12345, stdoutToServer=True, stderrToServer=True)
```
- if ``host.docker.internal`` does not work for you, you can replace it by the local IP of your machine.
- Remember this rules to insert your breakpoint:  If the file reside on your host, you can directly insert it, but on the other side, you will need to run a usershell session and debug from there.<br/>
  Eg: if  you want to put a pdb in ``../venv/*/*/*/foo/__init__.py``
    - <strong>DO NOT DO IT in ``local/code/venv/*/*/*/foo/__init__.py`` </strong>
    - do:

- You must launch VSCode using ``./control.sh vscode`` as vscode needs to have the ``PYTHONPATH`` variable preset to make linters work

    ```sh
    ./control.sh vscode
    ```
    - In other words, this add ``local/**/site-packages`` to vscode sys.path.


Additionnaly, adding this to ``.vscode/settings.json`` would help to give you a smooth editing experience

  ```json
  {
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/node_modules/*/**": true,
        "**/local/*/**": true,
        "**/local/code/venv/lib/**/site-packages/**": false

      }
  }
  ```

#### Debugging with VSCode
- [vendor documentation link](https://code.visualstudio.com/docs/python/debugging#_remote-debugging)
- The VSCode process will connect to your running docker container, using a network tcp connection, eg on port ``5678``.
- ``5678`` can be changed but of course adapt the commands, this port must be reachable from within the container and in the ``docker-compose-dev.yml`` file.
- Ensure you added ``WITH_VSCODE`` in your ``.env`` and that ``VSCODE_VERSION`` is tied to your VSCODE installation and start from a fresh build if it was not (pip will mess to update it correctly, sorry).
- Wherever you have the need to break, insert in your code the following snippet after imports (and certainly before wherever you want your import):

    import ptvsd;ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True);ptvsd.wait_for_attach()
    ```
- Remember this rules to insert your breakpoint:  If the file reside on your host, you can directly insert it, but on the other side, you will need to run a usershell session and debug from there.<br/>
  Eg: if  you want to put a pdb in ``venv/*/*/*/foo/__init__.py``
    - <strong>DO NOT DO IT in ``local/code/venv/*/*/*/foo/__init__.py`` </strong>
    - do:

        ```sh
        ./control.sh down {{cookiecutter.app_type}}
        services_ports=1 ./control.sh usershell
        apt install -y vim
        vim ../venv/*/*/*/foo/__init__.py
        # insert: import ptvsd;ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True);ptvsd.wait_for_attach()
        ./manage.py runserver 0.0.0.0:8000
        ```
- toggle a breakpoint on the left side of your text editor on VSCode.
- Switch to Debug View in VS Code, select the Python: Attach configuration, and select the settings (gear) icon to open launch.json to that configuration.<br/>
  Duplicate the remote attach part and edit it as the following

  ```json
  {
    "name": "Python Docker Attach",
    "type": "python",
    "request": "attach",
    "pathMappings": [
      {
        "localRoot": "${workspaceFolder}",
        "remoteRoot": "/code"
      }
    ],
    "port": 5678,
    "host": "localhost"
  }
  ```
- With VSCode and your configured debugging session, attach to the session and it should work

## Doc for deployment on environments
- [See here](./docs/README.md)

