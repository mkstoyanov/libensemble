psql -c 'create database ../test-balsam;' -U postgres
balsam init ../test-balsam
sudo chown -R postgres:postgres /var/run/postgresql
source balsamactivate test-balsam

export EXE=script_test_jobcontroller_hworld_balsam.py
export NUM_WORKERS=2
export WORKFLOW_NAME=libe_test-balsam
export SCRIPT_ARGS=$NUM_WORKERS
export LIBE_WALLCLOCK=3
export THIS_DIR=$PWD
export SCRIPT_BASENAME=${EXE%.*}

balsam rm apps --all --force
balsam rm jobs --all --force

balsam app --name $SCRIPT_BASENAME.app --exec $EXE --desc "Run $SCRIPT_BASENAME"

balsam job --name job_$SCRIPT_BASENAME --workflow $WORKFLOW_NAME --application $SCRIPT_BASENAME.app --args $SCRIPT_ARGS --wall-time-minutes $LIBE_WALLCLOCK --num-nodes 1 --ranks-per-node $((NUM_WORKERS+1)) --url-out="local:/$THIS_DIR" --stage-out-files="*.out *.txt *.log" --url-in="local:/$THIS_DIR/*" --yes
