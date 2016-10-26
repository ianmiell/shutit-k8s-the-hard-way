#!/bin/bash
bash ./destroy_vms.sh
asciinema rec -t 'Learn Kubernetes The Hard Way On Vagrant Walkthrough' -w 2 -c 'shutit build -d bash -m shutit-library/vagrant -m shutit-library/virtualbox --walkthrough' walkthrough_video.json
