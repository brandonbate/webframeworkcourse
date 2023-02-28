import random
from fabric import Connection
from invoke import Responder
from patchwork.files import exists, append

HOST = 'lists.bearcornfield.com'
USER = 'ec2-user'
KEY_FILENAME = '../../../aws_server9.pem'
REPO_URL = 'git@github.com:bb8fran/my_book_example.git' 
PROJECT = 'superlists'

def main():

    with Connection(host=HOST, user=USER, connect_kwargs={"key_filename": KEY_FILENAME}) as c:

        # Checks local git repo for latest commit id on local machine. Apparently I need
        # to run this BEFORE running c.cd.
        current_commit = c.local("git log -n 1 --format=%H").stdout
        site_folder = f'/home/{USER}/sites/{HOST}'
        # -p tells the server to create this folder if it doesn't already exist.
        c.run(f'mkdir -p {site_folder}')  
        with c.cd(site_folder):
            _get_latest_source(c, current_commit)
            _update_virtualenv(c)
            _create_or_update_dotenv(c)
            _update_static_files(c)
            _update_database(c)
            _install_and_run_nginx(c)
            _create_nginx_conf(c)
            _create_socket_directory(c)
            _create_gunicorn_service(c)
            _startup_services(c)
            
def _get_latest_source(c, current_commit):

    if exists(c,'.git'):  
        c.run('git fetch')  
    else:
        yes = Responder(pattern=r'Is this ok \[y/d/N\]:', response='y\n')

        # Make sure git is installed
        c.run('sudo yum install git', pty=True, watchers=[yes])
        
        c.run('git config --global user.name "bb8fran@gmail.com"')
        
        # Need git keys on system for this to work.
        yes2 = Responder(pattern=r'Are you sure you want to continue connecting \(yes\/no\)\?',
                         response='yes')
        
        c.run(f'git clone {REPO_URL} .', pty=True, watchers=[yes2])

        
    # Forces remote git repo to this latest commit id on local machine.
    c.run(f'git reset --hard {current_commit}')  

def _update_virtualenv(c):
    if not exists(c,'virtualenv/bin/pip'):  
        c.run(f'python3.7 -m venv virtualenv')
    c.run('./virtualenv/bin/pip install -r requirements.txt')  

def _create_or_update_dotenv(c):
    append(c,'.env', 'DJANGO_DEBUG_FALSE=y')  
    append(c,'.env', f'SITENAME={HOST}')
    current_contents = c.run('cat .env').stdout
    if 'DJANGO_SECRET_KEY' not in current_contents:  
        new_secret = ''.join(random.SystemRandom().choices(  
            'abcdefghijklmnopqrstuvwxyz0123456789', k=50
        ))
        append(c,'.env', f'DJANGO_SECRET_KEY={new_secret}')

def _update_static_files(c):
    c.run('./virtualenv/bin/python manage.py collectstatic --noinput')

def _update_database(c):
    c.run('./virtualenv/bin/python manage.py migrate --noinput')

def _install_and_run_nginx(c):
    c.run('sudo amazon-linux-extras install nginx1')
    c.run('sudo systemctl enable nginx')
    c.run('sudo systemctl start nginx')

def _create_nginx_conf(c):
    c.run('sudo mkdir -p /etc/nginx/sites-available')
    c.run('sudo mkdir -p /etc/nginx/sites-enabled')
    c.run('cat ./deploy_tools/nginx.template.conf' +
          f'| sed "s/DOMAIN/' + HOST + f'/"g' +
          f'| sudo tee /etc/nginx/sites-available/' + HOST)
    c.run('sudo ln -s -f /etc/nginx/sites-available/' + HOST + 
          ' /etc/nginx/sites-enabled/' + HOST)
    
    # regex for include /etc/nginx/conf.d/*;
    orig_include = f'include \/etc\/nginx\/conf\.d\/\*\.conf;'
    # regex for include /etc/nginx/sites-enabled/*;
    new_include = f'include \/etc\/nginx\/sites-enabled\/\*;'
    # regex replacement pattern
    pattern = 's/' + orig_include + '/' + orig_include + f'\\n' + new_include + '/g'
    
    c.run('cat /etc/nginx/nginx.conf' +
          f'| sed "s/user\snginx;/user ec2-user;/g" ' +
          f'| sed "' + pattern + '"' +
          f'| sudo tee /etc/nginx/nginx.conf');

def _create_socket_directory(c):
    c.run('sudo mkdir -p /var/sockets')
    c.run('sudo chmod -R 777 /var/sockets')

def _create_gunicorn_service(c):
    c.run('cat ./deploy_tools/gunicorn-systemd.template.service' +
          f'| sed "s/DOMAIN/' + HOST + f'/"g' +
          f'| sed "s/PROJECT/' + PROJECT + f'/"g' +
          f'| sudo tee /etc/systemd/system/gunicorn-' + HOST + '.service')

def _startup_services(c):
    c.run('sudo systemctl daemon-reload')
    c.run('sudo systemctl restart nginx')
    c.run('sudo systemctl enable gunicorn-' + HOST)
    c.run('sudo systemctl start gunicorn-' + HOST)

if __name__ == "__main__":
    main()