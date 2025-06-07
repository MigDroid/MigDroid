#!/bin/bash

# Activate the Conda environment
source activate py39 || conda activate py39

SAVE_DIR="test_repo_migdroid"
model_name="gpt-4o"

# Define the range for the loops
# declare -a categories=("1" "2" "4" "5")
declare -a categories=("1" "2" "4" "5")

# Log file
# LOGFILE="Temp/run.log"
# Redirect stdout and stderr to log file
# exec > >(tee -a "$LOGFILE") 2>&1


# Iterate over the ranges
for category in "${categories[@]}"; do
    for i in {1..9} 0; do
        for j in {1..5}; do
            for k in {1..2}; do
                config_id="a${category}${i}-a${category}${j}-b${category}${k}"
                if [ $i -eq $j ]; then
                    echo "Skipping ${config_id}"
                    continue
                fi
                if [ $category -eq 4 ] && [ $k -eq 2 ]; then
                    echo "Skipping ${config_id}"
                    continue
                fi
                if [ $category -eq 1 ] && [ $j -eq 6 ]; then
                    echo "Skipping ${config_id}"
                    continue
                fi
                # if [ $category -eq 1 ] && [ $j -eq 8 ]; then
                #     echo "Skipping ${config_id}"
                #     continue
                # fi
                if [ $category -eq 4 ] && [ $j -eq 5 ]; then
                    echo "Skipping ${config_id}"
                    continue
                fi
                if [ $category -eq 5 ] && [ $j -eq 7 ] && [ $k -eq 2 ]; then
                    echo "Skipping ${config_id}"
                    continue
                fi
                if [ $category -eq 5 ] && [ $j -eq 9 ] && [ $k -eq 2 ]; then
                    echo "Skipping ${config_id}"
                    continue
                fi
                # if 1<=i<=5, skip
                udid="emulator-5560"
                if [ $j -ge 6 ] || [ $j -eq 0 ]; then
                    udid="emulator-5554"
                fi
                if [ $category -eq 1 ] && [ $j -eq 1 ]; then
                    udid="emulator-5554"
                fi
                if [ $category -eq 4 ] && [ $j -eq 3 ]; then
                    udid="emulator-5554"
                fi

                udid="emulator-5554"
                
                command="python -u Planner/Planner.py $config_id 4723 $udid $model_name"
                
                fpath="${SAVE_DIR}/a${category}/b${category}${k}/generated_gpt_4o/${config_id}"
                log_file="$fpath/log.txt"
                echo $log_file
                # create the log file if it does not exist
                echo $fpath
                mkdir -p $fpath
                screen_dir="${fpath}/screens"
                # if screen_dir already exists, skip
                if [ -d "$screen_dir" ]; then
                    echo "Skipping $config_id"
                else
                    echo "Running $command"
                    # run the command and redirect its output to a log file
                    $command > $log_file 2>&1
                fi
                # # if it is a dir already, and have at least two files, skip
                # if [ -d "$fpath" ] && [ "$(ls -A $fpath | wc -l)" -ge 1 ]; then
                #     echo "Skipping $config_id"
                # else
                #     echo "Running $command"
                #     # run the command and redirect its output to a log file
                #     $command > $log_file 2>&1
                # fi
            done
        done
    done
done

echo "All commands executed."
