import yaml
import subprocess
import time, json
import logging, os
from rich.console import Console
import jinja2
import argparse
from rich.table import Table
from .helper_wrapper import log_header, boto3_s3_download, file_overwrite, json_file_content_check, get_cmd, seconds_to_minutes_and_seconds, set_attr, execute_bash, path_exist

# Configure the root logger
logging.basicConfig(
    level=logging.WARNING,  # Set the log level to DEBUG (you can use other levels like INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SysConfigInspector():
    def __init__(self, configuration_file = None,report_location=None, env_values_files=None):
        self.data = {}
        if env_values_files:
            with open(f"{env_values_files}",'r') as f:
                env_file_data = yaml.safe_load(f)
            set_attr(env_file_data['values'])
        if configuration_file:
            with open(f"{configuration_file[0]}",'r') as f:
                self.data = yaml.safe_load(f)
            if len(configuration_file) >1:
                for each_config in configuration_file[1:]:
                    with open(f"{each_config}",'r') as f:
                        tmp = yaml.safe_load(f)
                        self.data['sections'].update(tmp['sections'])
        self.logger = logging.getLogger(__name__)
        self.result = self.get_project_metadetails(self.data)
        self.response = {}
        self.console = Console()       
        for each_section in self.data['sections']:
            section_name = self.data['sections'][each_section]['section_name']
            log_header(section_name)
            if section_name not in self.response:
                self.response[section_name] = []
            for each_step in self.data['sections'][each_section]['events']:
                response = self.start_processing(each_step_config=self.data['sections'][each_section]['events'][each_step])
                self.response[section_name].append({
                    "step_name" : self.data['sections'][each_section]['events'][each_step]['event_name'],
                    "event_type" : self.data['sections'][each_section]['events'][each_step]['type'],
                    "cmd" : get_cmd(self.data['sections'][each_section]['events'][each_step]),
                    "time_taken" : response[1],
                    "status" : response[0],
                    "modified" : response[2]
                })
                if response[2]:
                    self.result['modified'] = True
                self.result['passed'] += (1 if response[0] else 0)
                self.result['failed'] += (0 if response[0] else 1)
                
        self.result['events'] = self.response
        dir_path = os.path.dirname(os.path.realpath(__file__))
        templateLoader = jinja2.FileSystemLoader(searchpath=f"{dir_path}")
        templateEnv = jinja2.Environment(loader=templateLoader)
        TEMPLATE_FILE = f"final_report.html"
        template = templateEnv.get_template(TEMPLATE_FILE)
        content = template.render(data=self.result)  # this is where to put args to the template renderer
        if report_location:
            with open(f"{report_location}",'w+') as file:
                file.write(content)
        
        
    def start_processing(self,each_step_config):
        with self.console.status("[bold green] Event checks going on ...") as status:
            start_time = time.time()
            response, modified = self.process_step(each_step_config)
            end_time = time.time()
            event_name = each_step_config.get("event_name","")
            execution_time = end_time - start_time
            execution_time = seconds_to_minutes_and_seconds(execution_time)
            if response:
                formatted_text = f"{event_name:<{60}} [bold green] [PASS] [/bold green] "+('[MODIFIED] [bold orange]' if modified else '[NO CHANGES] [bold green]')
                self.console.log(formatted_text)
            else:
                formatted_text = f"{event_name:<{60}} [bold red] [FAIL] [/bold red] "+ ('[MODIFIED] [bold orange]' if modified else '[NO CHANGES] [bold green]')
                self.console.log(formatted_text)
            return response, execution_time, modified

    def get_project_metadetails(self,config_data):
        temp = {}
        temp['project_name'] = config_data['project_name']
        temp['sections'] = len(list(config_data['sections'].keys()))
        temp['events'] = 0
        temp['passed'] = 0
        temp['failed'] = 0
        temp['modified'] = False
        temp['total_events'] = 0

        for each_section in config_data['sections']:
            temp['total_events'] += len(list(config_data['sections'][each_section]['events'].keys()))
        return temp
    

    def process_step(self,step_config_data):
        log=""
        valid_event_types = ["bash","file_check","s3_download","file_overwrite","json_file_content_check"]
        event_type=step_config_data['type']
        validate = step_config_data.get("validate",True)
        if event_type in valid_event_types:
            if event_type == 'bash':
                res=execute_bash(command=step_config_data['cmd'],response=step_config_data['response'])
                if res == False:
                    if "action" in step_config_data:
                        return self.process_step(step_config_data['action'])[0], True
                    else:
                        return False, False
                else:
                    return res, False
            elif event_type == 'file_check':
                res=path_exist(step_config_data['file'],step_config_data.get("pattern",None))
                if res == False:
                    if "action" in step_config_data:
                        return self.process_step(step_config_data['action'])[0], True
                    else:
                        return False, False
                else:
                    return res, False
                
            elif event_type == 's3_download':
                res=boto3_s3_download(step_config_data['local_file'],step_config_data['s3_file'])
                if res == False:
                    if "action" in step_config_data:
                        return self.process_step(step_config_data['action'])[0], True
                    else:
                        return False, False
                else:
                    return res, False

            elif event_type == 'file_overwrite':
                res=file_overwrite(step_config_data['content'],step_config_data['file_path'])
                if res == False:
                    if "action" in step_config_data:
                        return self.process_step(step_config_data['action'])[0], True
                    else:
                        return False, False
                else:
                    if validate:
                        return res, False
                    else:
                        return self.process_step(step_config_data['action'])[0], True
                
            elif event_type == 'json_file_content_check':
                res=json_file_content_check(step_config_data['content'],step_config_data['file_path'])
                if res == False:
                    if "action" in step_config_data:
                        return self.process_step(step_config_data['action'])[0], True
                    else:
                        return False, False
                else:
                    return res, False         

def main():
    parser = argparse.ArgumentParser(description="SysConfigInspector Command Line Tool")
    parser.add_argument("--configuration-file", nargs='+', required=True, help="Path to the configuration file")
    parser.add_argument("--report-location", required=True, help="Path to the report location")
    parser.add_argument("--env-values-files", required=False, help="Path to the report location")
    args = parser.parse_args()
    SysConfigInspector(configuration_file=args.configuration_file, report_location=args.report_location,env_values_files=args.env_values_files)
    

        
if __name__ == "__main__":
    main()