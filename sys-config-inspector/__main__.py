from .inspector import SysConfigInspector
import argparse

def main():
    parser = argparse.ArgumentParser(description="SysConfigInspector Command Line Tool")
    parser.add_argument("--configuration-file", nargs='+', required=True, help="Path to the configuration file")
    parser.add_argument("--report-location", required=True, help="Path to the report location")
    args = parser.parse_args()
    SysConfigInspector(configuration_file=args.configuration_file, report_location=args.report_location)
    
if __name__ == "__main__":
    main()