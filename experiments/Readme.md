# Experimental results

## Scripts
- ### ycsb_run.sh
  Invokes four serial workloads (a, b, c and f, respectively) with the given parameters and stores the overall throughput
  
  `Usage: ./ycsb_run.sh -t <threads> -o <operations> -p <target_throughput> -f <outdir>`
  
  > Note: Target throughput is not always achieved, but ycsb tries it's best to reach it
  
  > Note: mongodb.url used in ycsb parameters inside the script is pointing to mongos and the previously loaded via ycsb database
  > So the parameter `-p mongodb.url=...` needs specific modification
  
  Generates a single file `outdir/ts_<threads>_<operations>_<target-throughput>_abcf` 
  containing four lines of different throughputs achieved

- ### generate_load.sh
  A Wrapper around ycsb_run to invoke a long running workload, modifiable according certain needs
  
  `Usage ./generate_load.sh`


## Naming Convention
Resulting files are named after the parameters used to produce them, so the template is `ts_<threads>_<operations>_<target_throughput>_abcf`

## Reference
Contains experiments with a single MongoDB server, in order to find it's limits

## Runtime folder
Contains experiments with variable number of MongoDB servers, according to the protocol
> Note: Due to the sensitivity of the protocol on adding or removing nodes, a lot of throughputs are calculated with single MongoDB server
> until the decision to add a new one is made
