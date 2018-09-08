#!/bin/bash
set -e
[[ -z "$SHUTIT" ]] && SHUTIT="$1/shutit"
[[ ! -a "$SHUTIT" ]] || [[ -z "$SHUTIT" ]] && SHUTIT="$(which shutit)"
if [[ ! -a "$SHUTIT" ]]
then
	echo "Must have shutit on path, eg export PATH=$PATH:/path/to/shutit_dir"
	exit 1
fi
./destroy_vms.sh
$SHUTIT build --echo -d bash -m shutit-library/vagrant -m shutit-library/virtualization -l debug "$@"
if [[ $? != 0 ]]
then
	exit 1
fi