import logging
import os
import posixpath
import io
import boto3
import paramiko
from tempfile import mkdtemp
from urllib import unquote_plus
from subprocess import check_call, check_output

os.environ['PATH'] += os.pathsep + os.getcwd()


def format_private_key(s):
    '''Inserts newlines after -----BEGIN RSA PRIVATE KEY----- and before
    -----END RSA PRIVATE KEY-----'''
    return s[:31] + '\n' + s[31:3167] + '\n' + s[3167:]


def get_bucket_and_key(event):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = unquote_plus(event['Records'][0]['s3']['object']['key'])
    print('bucket', bucket)
    print('key', key)
    return (bucket, key)


def get_audiopath(work_dir, key):
    audiopath = os.path.join(mkdtemp(dir=work_dir), key)
    print('audiopath', audiopath)
    return audiopath


def download_from_s3(bucket, key, audiopath):
    s3 = boto3.resource('s3')
    s3.meta.client.download_file(bucket, key, audiopath)


def ssh_connect(ssh_private_key, ssh_username, ssh_host, ssh_port):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
    ssh.connect(
        hostname=ssh_host,
        port=ssh_port,
        username=ssh_username,
        pkey=paramiko.RSAKey.from_private_key(
            io.StringIO(unicode(ssh_private_key))),
        look_for_keys=False,
        allow_agent=False,
    )
    return ssh


def ssh_copy(ssh, ssh_dir, key, audiopath):
    remotepath = get_remotepath(ssh_dir, key, audiopath)
    _, stdout, stderr = ssh.exec_command('mkdir -vp {}'.format(posixpath.dirname(remotepath)))
    print('stdout', stdout.read())
    print('stderr', stderr.read())
    sftp = ssh.open_sftp()
    sftp.put(audiopath, remotepath)


def get_remotepath(ssh_dir, key, audiopath):
    artist = check_output(['tagit', 'g', 'ARTIST', audiopath]).strip()
    remotepath = posixpath.join(ssh_dir, artist, key)
    print('remotepath', remotepath)
    return remotepath


def handler(event, context):
    work_dir = os.environ['WORK_DIR']
    ssh_private_key = format_private_key(os.environ['SSH_PRIVATE_KEY'])
    ssh_username = os.environ['SSH_USERNAME']
    ssh_host = os.environ['SSH_HOST']
    ssh_port = int(os.environ.get('SSH_PORT'))
    ssh_dir = os.environ['SSH_DIR']

    bucket, key = get_bucket_and_key(event)
    audiopath = get_audiopath(work_dir, key)
    download_from_s3(bucket, key, audiopath)

    ssh = ssh_connect(ssh_private_key, ssh_username, ssh_host, ssh_port)
    ssh_copy(ssh, ssh_dir, key, audiopath)

    return None
