#!/bin/bash

# wrapper of ycsb run to generate a series of loads

ycsb_run_sh=/home/user/experiments/ycsb_run.sh
output_dir=/home/user/experiments/runtime

target=8000

for threads in 080 160
do
  for ops in 1 2 4 8
  do
    "${ycsb_run_sh}" -t "${threads}" -o "${ops}000000" -p "${target}" -f "${output_dir}"
  done
done
