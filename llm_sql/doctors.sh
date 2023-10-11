#!/bin/bash

# Define the usage function
usage() {
    echo "Usage: $0 [--file <file_path>] [--launch-gradio]"
    exit 1
}

# Initialize file path as an empty string
file_path=""

# Process command line arguments
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        --file)
        if [[ -z "$2" ]]; then
            echo "--file requires a file path argument"
            usage
        fi
        file_path="$2"
        shift # skip argument
        shift # skip value
        ;;
        --launch-gradio)
        launch_gradio=true
        shift # skip argument
        ;;
        *)
        usage
        ;;
    esac
done

# Create and activate the virtual environment if it does not exist
if [[ ! -d "venv" ]]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install requirements if they haven't been installed
if [[ ! -f "venv/requirements_installed" ]]; then
    pip install -r gradio/requirements.txt
    touch venv/requirements_installed
fi

# If a file path was given, call process.py with the file as argument
if [[ ! -z "$file_path" ]]; then
    python process.py "$file_path"
fi

# If the optional '--launch-gradio' argument was provided, launch gradio app
if [[ ! -z $launch_gradio ]]; then
    python gradio/app.py
fi
