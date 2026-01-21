#!/bin/bash 


# usage: cli.py grade-question [-h] --question QUESTION --rubrics-config RUBRICS_CONFIG --submissions-dir
#                              SUBMISSIONS_DIR --sources-config SOURCES_CONFIG --index-dir INDEX_DIR
#                              [--index-backend {chromadb,in-memory}] --output OUTPUT
#                              [--mode {sequential,batched,async}] [--log-path LOG_PATH]
#                              [--log-file LOG_FILE] [--log] [--no-log]
# 
# options:
#   -h, --help            show this help message and exit
#   --question QUESTION   Question ID (e.g., q01)
#   --rubrics-config RUBRICS_CONFIG
#                         Path to rubric configuration YAML file
#   --submissions-dir SUBMISSIONS_DIR
#                         Directory containing submission YAML files
#   --sources-config SOURCES_CONFIG
#                         Path to sources configuration YAML file
#   --index-dir INDEX_DIR
#                         Directory for persistent indexes
#   --index-backend {chromadb,in-memory}
#                         Index backend to use (default: chromadb)
#   --output OUTPUT       Path to output JSON file
#   --mode {sequential,batched,async}
#                         Execution mode (default: sequential)
#   --log-path LOG_PATH   Directory where log files are written. If relative (e.g., 'logs'), it is
#                         interpreted relative to the autograder/ directory (default: logs)
#   --log-file LOG_FILE   Name of the main log file (default: grading.log)
#   --log                 Enable transparency logging (default: True)
#   --no-log              Disable transparency logging
######

# usage: cli.py grade-student [-h] [--question QUESTION] --rubrics-config RUBRICS_CONFIG --submission
#                             SUBMISSION --sources-config SOURCES_CONFIG --index-dir INDEX_DIR
#                             [--index-backend {chromadb,in-memory}] --output OUTPUT
#                             [--log-path LOG_PATH] [--log-file LOG_FILE] [--log] [--no-log]
# 
# options:
#   -h, --help            show this help message and exit
#   --question QUESTION   Question ID (optional, will be read from submission if not provided)
#   --rubrics-config RUBRICS_CONFIG
#                         Path to rubric configuration YAML file
#   --submission SUBMISSION
#                         Path to submission YAML file
#   --sources-config SOURCES_CONFIG
#                         Path to sources configuration YAML file
#   --index-dir INDEX_DIR
#                         Directory for persistent indexes
#   --index-backend {chromadb,in-memory}
#                         Index backend to use (default: chromadb)
#   --output OUTPUT       Path to output JSON file
#   --log-path LOG_PATH   Directory where log files are written. If relative (e.g., 'logs'), it is
#                         interpreted relative to the autograder/ directory (default: logs)
#   --log-file LOG_FILE   Name of the main log file (default: grading.log)
#   --log                 Enable transparency logging (default: True)
#   --no-log              Disable transparency logging
#   --log-path LOG_PATH   Directory where log files are written. If relative (e.g., 'logs'), it is
#                         interpreted relative to the autograder/ directory (default: logs)


uv run python -m grading_dynamic_rubrics.cli grade-question --question q01 --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml --submissions-dir grading_dynamic_rubrics/submissions --sources-config grading_dynamic_rubrics/config/sources.yaml --output grading_dynamic_rubrics/results/q01_results.json --log
