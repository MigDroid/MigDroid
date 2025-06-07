#!/bin/bash

# Activate the Conda environment
source activate py39 || conda activate py39

SAVE_DIR="construct_dataset/src_screens_annoted"

# Define the range for the loops
declare -a categories=("1" "2" "4" "5")

# Log file
LOGFILE="construct_dataset/run_annots.log"
# Redirect stdout and stderr to log file
exec > >(tee -a "$LOGFILE") 2>&1


# Iterate over the ranges
for category in "${categories[@]}"; do
    for i in {1..9} 0; do
        for k in {1..2}; do
            # if 1<=i<=5, skip
            udid="emulator-5554"
            if [ $i -ge 6 ] || [ $i -eq 0 ]; then
                udid="emulator-5556"
            fi
            if [ $category -eq 1 ] && [ $i -eq 1 ]; then
                udid="emulator-5556"
            fi
            if [ $category -eq 4 ] && [ $i -eq 3 ]; then
                udid="emulator-5556"
            fi

            test_id="a${category}${i}b${category}${k}"
            command="python construct_dataset/TestRunner_annots.py $test_id $udid"
            
            fpath="${SAVE_DIR}/a${category}/b${category}${k}/base/a${category}${i}_screens"
            echo $fpath
            # if it is a dir already, and not empty, skip
            if [ -d "$fpath" ] && [ "$(ls -A $fpath)" ]; then
                echo "Skipping $test_id"
            else
                echo "Running $command"
                $command
            fi
        done
    done
done

echo "All commands executed."
