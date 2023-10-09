from rich.console import Console
import boto3, os, json, re
import logging, time
import subprocess

# Configure the root logger
logging.basicConfig(
    level=logging.WARNING,  # Set the log level to DEBUG (you can use other levels like INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID",None)
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY",None)
s3_client = boto3.client('s3')
if aws_access_key_id and aws_secret_access_key:
    s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id , aws_secret_access_key=aws_secret_access_key)


def set_attr(values):
    try:
        for key, value in values.items():
            globals()[key] = value
        return True
    except:
        return False

def get_cmd(configuration):
    cmd = ["cmd","file","s3_file","file_path"]
    for each_cmd in cmd:
        try:
            return configuration[each_cmd]
        except:
            continue
    return ""
    
def seconds_to_minutes_and_seconds(seconds):
    # Round the seconds to two decimal places
    rounded_seconds = round(seconds, 2)

    # Calculate minutes and remaining seconds
    minutes = int(rounded_seconds // 60)
    remaining_seconds = rounded_seconds % 60

    # Format the result as "X min Y.YY sec"
    if minutes > 0:
        return f"{minutes} min {remaining_seconds:.2f} sec"
    else:
        return f"{remaining_seconds:.2f} sec"

def log_header(name):
    console = Console()
    console_width = console.width
    padding = (console_width - len(name)) // 2
    formatted_header = f"{' ' * padding}{name}{' ' * padding}"
    console.print(formatted_header, style="bold magenta")
    console.print("=" * console_width)

def boto3_s3_upload(local_file_path, s3_path):
    try:
        s3_path = s3_path.split("s3://")[-1]
        bucket_name = s3_path.split("/")[0]
        s3_path = s3_path.replace(f'{bucket_name}/', '')
        s3_client.upload_file(local_file_path, bucket_name, s3_path)
        return True
    except Exception as e:
        logger.warning(f"Failed to upload file {local_file_path} with error {e}")
        return False


def path_exist(path, pattern=None):
    try:
        path = path.format(**globals())
        if pattern:
            file_list = os.listdir(path)
            count=0
            matching_files = [file for file in file_list if re.match(pattern, file)]
            for file in matching_files:
                count+=1
            if count>=1:
                return True
            else:
                return False
        else:
            if os.path.isdir(path):
                logger.debug(f"Folder Exist : {path}")
                return True
            elif os.path.isfile(path):
                logger.debug(f"File Exist : {path}")
                return True
            else:
                logger.debug(f"File or Folder don't exist : {path}")
                return False
    except:
        return False


def execute_bash(command,response):
    try:
        command = command.format(**globals())
        response = response.format(**globals())
        start_time = time.time()  # Record the start time
        logger.debug(f"{command} started executing at {start_time}")
        # Run the Bash command, capture its output as a byte string
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        
        end_time = time.time()  # Record the end time

        # Calculate the duration
        duration = end_time - start_time
        logger.debug(f"{command} ended executing at {end_time}")

        # Access the standard output and standard error
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout == response:
            return True
        else:
            return False

    except Exception as e:
        # If the command returns a non-zero exit code, you can handle the error here
        logger.error(f"Error executing command: {e}")
        return False


def boto3_s3_download(local_file_path, s3_path):
    try:
        local_file_path = local_file_path.format(**globals())
        s3_path = s3_path.format(**globals())
        s3_path = s3_path.split("s3://")[-1]
        bucket_name = s3_path.split("/")[0]
        s3_path = s3_path.replace(f'{bucket_name}/', '')
        s3_client.download_file(bucket_name, s3_path, local_file_path)
        return True
    except Exception as e:
        logger.warning(f"Failed to download file {s3_path} with error {e}")
        return False

def file_overwrite(content, local_file_path):
    try:
        content = content.format(**globals())
        local_file_path = local_file_path.format(**globals())
        content = content.replace("'", "\"")
        content = json.loads(content)
        with open(local_file_path,'w+') as file:
            file.write(content)
        return True
    except Exception as e:
        logger.warning(f"failed to write content in file: {e} and content : {content}, datatype : {type(content)}")
        return False
    

def json_file_content_check(content, local_file_path):
    try:
        local_file_path = local_file_path.format(**globals())
        content = content.format(**globals())
        with open(local_file_path,'r') as file:
            file_content = json.load(file)
        content = content.replace("'", "\"")
        content = json.loads(content)
        if file_content == content:
            return True
        else:
            return False
    except Exception as e:
        logger.warning(f"failed to read content in file: {e}")
        return False