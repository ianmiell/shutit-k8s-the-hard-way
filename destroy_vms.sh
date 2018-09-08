#!/bin/bash
MODULE_NAME=shutit_k8s_the_hard_way
rm -rf $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/vagrant_run/*
XARGS_FLAG='--no-run-if-empty'
if ! echo '' | xargs --no-run-if-empty >/dev/null 2>&1
then
	XARGS_FLAG=''
fi
if [[ $(command -v VBoxManage) != '' ]]
then
	while true
	do
		VBoxManage list runningvms | grep ${MODULE_NAME} | awk '{print $1}' | xargs $XARGS_FLAG -IXXX VBoxManage controlvm 'XXX' poweroff && VBoxManage list vms | grep shutit_k8s_the_hard_way | awk '{print $1}'  | xargs -IXXX VBoxManage unregistervm 'XXX' --delete
		# The xargs removes whitespace
		if [[ $(VBoxManage list vms | grep ${MODULE_NAME} | wc -l | xargs) -eq '0' ]]
		then
			break
		else
			ps -ef | grep virtualbox | grep ${MODULE_NAME} | awk '{print $2}' | xargs kill
			sleep 10
		fi
	done
fi
if [[ $(command -v virsh) ]] && [[ $(kvm-ok 2>&1 | command grep 'can be used') != '' ]]
then
	virsh list | grep ${MODULE_NAME} | awk '{print $1}' | xargs $XARGS_FLAG -n1 virsh destroy
fi