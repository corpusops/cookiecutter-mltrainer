#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from distutils.dir_util import remove_tree
import os
import subprocess


DEPLOY_BR = os.environ.get('DEPLOY_BR', 'stable')
use_submodule_for_deploy_code = bool(
    '{{cookiecutter.use_submodule_for_deploy_code}}'.strip())

# Workaround cookiecutter no support of symlinks
TEMPLATE = 'cookiecutter-mltrainer'
SYMLINKS_DIRS = {
    ".ansible/playbooks/roles/{{cookiecutter.app_type}}_vars":
    "../../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/roles/{{cookiecutter.app_type}}_vars",  #noqa
    ".ansible/playbooks/roles/{{cookiecutter.app_type}}":
    "../../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/roles/{{cookiecutter.app_type}}",  #noqa
}
SYMLINKS_FILES = {
    ".ansible/scripts/setup_vaults.sh": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/setup_corpusops.sh": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/test.sh": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/setup_core_variables.sh": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/call_roles.sh": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/yamldump.py": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/call_ansible.sh": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/edit_vault.sh": "cops_wrapper.sh",  #noqa
    ".ansible/scripts/print_env.sh": "call_ansible.sh",  #noqa
    ".ansible/scripts/setup_ansible.sh": "cops_wrapper.sh",  #noqa
    "bin/load_registry.py": "../{{cookiecutter.deploy_project_dir}}/bin/load_registry.py",  #noqa
    "bin/mlflow.sh": "../{{cookiecutter.deploy_project_dir}}/bin/mlflow.sh",  #noqa
    "bin/docker-mlflow.sh": "../{{cookiecutter.deploy_project_dir}}/bin/docker-mlflow.sh",  #noqa
    ".ansible/playbooks/ping.yml": "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/ping.yml",  #noqa
    ".ansible/playbooks/teleport.yml": "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/teleport.yml",  #noqa
    ".ansible/playbooks/backup.yml": "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/backup.yml",  #noqa
    ".ansible/playbooks/delivery.yml": "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/delivery.yml",  #noqa
    ".ansible/playbooks/app.yml": "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/app.yml",  #noqa
    ".ansible/playbooks/deploy_key_setup.yml":
    "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/deploy_key_setup.yml",  #noqa
    ".ansible/playbooks/deploy_key_teardown.yml":
    "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/deploy_key_teardown.yml",  #noqa
    ".ansible/playbooks/site.yml":
    "../../{{cookiecutter.deploy_project_dir}}/.ansible/playbooks/site.yml",  #noqa
    # "tox.ini":    "{{cookiecutter.deploy_project_dir}}/tox.ini",  #noqa
    "Dockerfile": "{{cookiecutter.deploy_project_dir}}/Dockerfile",  #noqa
}
SYMLINKS = {}
SYMLINKS.update(SYMLINKS_DIRS)
SYMLINKS.update(SYMLINKS_FILES)
GITSCRIPT = """
set -ex
if [ ! -e .git ];then git init;fi
git remote rm origin || /bin/true
git remote add origin {{cookiecutter.git_project_url}}
git add .
git add -f local/regen.sh
if [ ! -e "{{cookiecutter.deploy_project_dir}}/.git" ];then
    rm -rf "{{cookiecutter.deploy_project_dir}}"
fi
if [ ! -e "{{cookiecutter.deploy_mlflow_dir}}/.git" ];then
    rm -rf "{{cookiecutter.deploy_mlflow_dir}}"
fi
if [ ! -e "{{cookiecutter.deploy_mlflow_dir}}/.git" ];then
    git submodule add -f "{{cookiecutter.deploy_mlflow_url}}" \
        "{{cookiecutter.deploy_mlflow_dir}}"
fi
"""
if use_submodule_for_deploy_code:
    GITSCRIPT += """
if [ ! -e "{{cookiecutter.deploy_project_dir}}/.git" ];then
    git submodule add -f "{{cookiecutter.deploy_project_url}}" \
        "{{cookiecutter.deploy_project_dir}}"
fi
"""
else:
    GITSCRIPT += """
if [ ! -e "{{cookiecutter.deploy_project_dir}}/.git" ];then
    git clone "{{cookiecutter.deploy_project_url}}" \
            "{{cookiecutter.deploy_project_dir}}"
    fi
( cd "{{cookiecutter.deploy_project_dir}}" \
  && git fetch origin && git reset --hard origin/{DEPLOY_BR} )
""".format(**locals())
EGITSCRIPT = """
sed="sed";if (uname | egrep -iq "darwin|bsd");then sed="gsed";fi
if !($sed --version);then echo $sed not avalaible;exit 1;fi
{%raw%}vv() {{ echo "$@">&2;"$@"; }}{%endraw%}
{% if cookiecutter.use_submodule_for_deploy_code %}
dockerfile={{cookiecutter.deploy_project_dir}}/Dockerfile
{% else %}
dockerfile=Dockerfile
{% endif %}
{% if cookiecutter.no_lib %}
$sed -i -re "/ADD( --chown={{cookiecutter.app_type}}:{{cookiecutter.app_type}})? lib/d" $dockerfile
rm -rf lib
{% endif %}
if [ -e $dockerfile ] && [ ! -h $dockerfile ];then
$sed -i -re \
	"s/PY_VER=.*/PY_VER={{cookiecutter.py_ver}}/g" \
	$dockerfile

$sed -i -re \
	"s/project/{{cookiecutter.mltrainer_project_name}}/g" \
	$dockerfile
fi
if ( find sys/*sh 2>/dev/null );then
$sed -i -re \
	"s/project/{{cookiecutter.mltrainer_project_name}}/g" \
	sys/*sh
fi
set +x
{% if not cookiecutter.use_submodule_for_deploy_code %}

while read f;do
    if ( egrep -q "local/{{cookiecutter.app_type}}" "$f" );then
        echo "rewrite: $f"
        vv $sed -i -r \
        -e "s|local/{{cookiecutter.app_type}}/||g" \
        -e "/(ADD\s+){{cookiecutter.deploy_project_dir.replace('/', '\/')}}\/ local/d" \
        -e "s|{{cookiecutter.deploy_project_dir}}/||g" \
        -e "/ADD\s*\/code\/$/d" \
        "$f"
    fi
done < <( find -type f|egrep -v "((^./(\.tox|\.git|local))|/static/)"; )
$sed -i -re "/\/code\/sys\/\* sys/d" $dockerfile
{% endif %}
set -x
# strip whitespaces from compose
$sed -i -re 's/\s+$//g' docker-compose*.yml
$sed -i -r '/^\s*$/d' docker-compose*.yml
"""

MOTD = '''
After reviewing all changes
do not forget to commit and push your new/regenerated project
'''


def remove_path(i):
    if os.path.exists(i) or os.path.islink(i):
        if os.path.islink(i):
            os.unlink(i)
        elif os.path.isdir(i):
            remove_tree(i)
        elif os.path.islink(i):
            os.unlink(i)


def sym(i, target):
    print('* Symlink: {0} -> {1}'.format(i, target))
    d = os.path.dirname(i)
    if d and not os.path.exists(d):
        os.makedirs(d)
    remove_path(i)
    os.symlink(target, i)


def main():
    s = GITSCRIPT
    for i in SYMLINKS:
        sym(i, SYMLINKS[i])
    if not use_submodule_for_deploy_code:
        for i in SYMLINKS:
            remove_path(i)
            target = SYMLINKS[i]
            slash = (i in SYMLINKS_DIRS) and '/' or ''
            d = os.path.dirname(i)
            if d and not os.path.exists(d):
                os.makedirs(d)
            if '/' not in target:
                sym(i, SYMLINKS[i])
            else:
                s += '\nrsync -azv --delete {0}{1} {2}{1}'.format(
                    SYMLINKS[i].replace('../', ''), slash, i)
        s += '\nrsync -azv {0}/Dockerfile Dockerfile'.format(
            "{{cookiecutter.deploy_project_dir}}")
        s += '\nrsync -azv {0}/.ansible/playbooks/ .ansible/playbooks/'.format(
            "{{cookiecutter.deploy_project_dir}}")
        s += '\nrsync -azv {0}/sys/ sys/'.format(
            "{{cookiecutter.deploy_project_dir}}")
        s += '\ngit add .ansible'
    s += EGITSCRIPT
    subprocess.check_call(["bash", "-c", s.format(template=TEMPLATE)])
    print(MOTD)


if __name__ == '__main__':
    main()
# vim:set et sts=4 ts=4 tw=0: