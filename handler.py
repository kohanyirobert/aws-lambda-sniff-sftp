import sys
import locale
import os
import posixpath
import io
import boto3
import paramiko
import pipes
from tempfile import mkdtemp
from urllib import unquote_plus
from subprocess import check_call, check_output

print('defaultencoding', sys.getdefaultencoding())
print('filesystemencoding', sys.getfilesystemencoding())
print('preferredencoding', locale.getpreferredencoding())

os.environ['PATH'] += os.pathsep + os.getcwd()


def format_private_key(s):
    '''Inserts newlines after -----BEGIN RSA PRIVATE KEY----- and before
    -----END RSA PRIVATE KEY-----'''
    return s[:31] + '\n' + s[31:3167] + '\n' + s[3167:]


def get_bucket_and_key(event):
    '''https://stackoverflow.com/a/39465221/433835'''
    bucket = event['Records'][0]['s3']['bucket']['name']
    urlencoded_key = event['Records'][0]['s3']['object']['key']
    utf8_urlencoded_key = urlencoded_key.encode('utf-8')
    utf8_key = unquote_plus(utf8_urlencoded_key)
    key = utf8_key.decode('utf-8')
    print('bucket', bucket)
    print('urlencoded_key', urlencoded_key)
    print('utf8_urlencoded_key', utf8_urlencoded_key)
    print('utf8_key', utf8_key)
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
    # TODO Externalize like ssh_post_exec
    cmd = "mkdir -vp {}".format(pipes.quote(posixpath.dirname(remotepath)))
    print('cmd', cmd)
    _, stdout, stderr = ssh.exec_command(cmd)
    print('stdout', stdout.read())
    print('stderr', stderr.read())
    sftp = ssh.open_sftp()
    sftp.put(audiopath, remotepath)


def ssh_post_exec(ssh, ssh_command, audiopath):
    title = check_output(['tagit', 'g', 'TITLE', audiopath]).strip()
    stdin, stdout, stderr = ssh.exec_command(ssh_command.format(title))
    stdin.close()
    stdout.close()
    stderr.close()


def get_remotepath(ssh_dir, key, audiopath):
    artist = check_output(['tagit', 'g', 'ARTIST', audiopath]).strip()
    print('artist', artist)
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
    ssh_command = os.environ.get('SSH_COMMAND')

    bucket, key = get_bucket_and_key(event)
    audiopath = get_audiopath(work_dir, key)
    download_from_s3(bucket, key, audiopath)

    ssh = ssh_connect(ssh_private_key, ssh_username, ssh_host, ssh_port)
    ssh_copy(ssh, ssh_dir, key, audiopath)
    if ssh_command:
        ssh_post_exec(ssh, ssh_command, audiopath)

    return None
