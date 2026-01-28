#!/bin/bash

# usage: grading_all_questions_from_evidence.py [-h] [--submission_folder_path SUBMISSION_FOLDER_PATH] [--output_dir OUTPUT_DIR] [--student_id STUDENT_ID]
#                                               [--verbose]
# 
# Batch grade all questions using preprocessed evidence
# 
# options:
#   -h, --help            show this help message and exit
#   --submission_folder_path SUBMISSION_FOLDER_PATH
#                         Path to submissions folder (default: grading_dynamic_rubrics/submissions)
#   --output_dir OUTPUT_DIR
#                         Output directory for results (default: output)
#   --student_id STUDENT_ID
#                         Student ID to grade (default: student_001)
#   --verbose             Print detailed output
#   --include_question INCLUDE_QUESTION
#                         Include question text in LLM prompt (default: True)
#   --include_criterion_description INCLUDE_CRITERION_DESCRIPTION
#                         Include criterion description in LLM prompt (default: True)
#   --save_prompts SAVE_PROMPTS
#                         Save full LLM prompts to JSON files for analysis (default: False)
# 
# Examples:
#   python grading_all_questions_from_evidence.py \
#       --submission_folder_path grading_dynamic_rubrics/submissions
# 
#   python grading_all_questions_from_evidence.py \
#       --submission_folder_path grading_dynamic_rubrics/submissions \
#       --output_dir my_results \
#       --student_id student_001 \
#       --verbose

uv run python grading_all_questions_from_evidence.py \
   --submission_folder_path grading_dynamic_rubrics/submissions \
   --output_dir my_results_improved_retry \
   --student_id student_001 \
   --save_prompts True \
   --verbose
