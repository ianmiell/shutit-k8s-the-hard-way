import random
import string
import os

from shutit_module import ShutItModule

class shutit_k8s_the_hard_way(ShutItModule):


	def build(self, shutit):
		vagrant_image = shutit.cfg[self.module_id]['vagrant_image']
		vagrant_provider = shutit.cfg[self.module_id]['vagrant_provider']
		gui = shutit.cfg[self.module_id]['gui']
		memory = shutit.cfg[self.module_id]['memory']
		module_name = 'shutit_k8s_the_hard_way_' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
		home_dir = os.path.expanduser('~')
		shutit.send('rm -rf ' + home_dir + '/' + module_name + ' && mkdir -p ' + home_dir + '/' + module_name + ' && cd ' + home_dir + '/' + module_name)
		shutit.send('vagrant init ' + vagrant_image)
		controller0ip    = '192.168.2.2'
		controller1ip    = '192.168.2.3'
		controller2ip    = '192.168.2.4'
		worker0ip        = '192.168.2.5'
		worker1ip        = '192.168.2.6'
		worker2ip        = '192.168.2.7'
		load_balancer_ip = '192.168.2.8'
		client_ip        = '192.168.2.9'
		kube_token       = 'chAng3m3'
		shutit.send_file(home_dir + '/' + module_name + '/Vagrantfile','''

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |vb|
    vb.gui = ''' + gui + '''
    vb.memory = "''' + memory + '''"
  end

  config.vm.define "controller0" do |controller0|    
    controller0.vm.box = ''' + '"' + vagrant_image + '"' + '''
    controller0.vm.hostname = "controller0"
    controller0.vm.network "private_network", ip: "''' + controller0ip + '''"
  end

  config.vm.define "controller1" do |controller1|
    controller1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    controller1.vm.network :private_network, ip: "''' + controller1ip+ '''"
    controller1.vm.hostname = "controller1"
  end

  config.vm.define "controller2" do |controller2|
    controller2.vm.box = ''' + '"' + vagrant_image + '"' + '''
    controller2.vm.network :private_network, ip: "''' + controller2ip + '''"
    controller2.vm.hostname = "controller2"
  end

  config.vm.define "worker0" do |worker0|    
    worker0.vm.box = ''' + '"' + vagrant_image + '"' + '''
    worker0.vm.network "private_network", ip: "''' + worker0ip + '''"
    worker0.vm.hostname = "worker0"
  end

  config.vm.define "worker1" do |worker1|
    worker1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    worker1.vm.network :private_network, ip: "''' + worker1ip + '''"
    worker1.vm.hostname = "worker1"
  end

  config.vm.define "worker2" do |worker2|
    worker2.vm.box = ''' + '"' + vagrant_image + '"' + '''
    worker2.vm.network :private_network, ip: "''' + worker2ip + '''"
    worker2.vm.hostname = "worker2"
  end

  config.vm.define "load_balancer" do |load_balancer|
    load_balancer.vm.box = ''' + '"' + vagrant_image + '"' + '''
    load_balancer.vm.network :private_network, ip: "''' + load_balancer_ip + '''"
    load_balancer.vm.hostname = "load-balancer"
  end

  config.vm.define "client" do |client|
    client.vm.box = ''' + '"' + vagrant_image + '"' + '''
    client.vm.network :private_network, ip: "''' + client_ip + '''"
    client.vm.hostname = "client"
  end
end''')
		shutit.send('cd ~/' + module_name)
		shutit.send('vagrant up --provider virtualbox',timeout=99999)
		# Set up the load balancer - tcp 6443 as per https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/01-infrastructure-aws.md

		# debug - takes some time
		#for machine in ('controller0','controller1','controller2','worker0','worker1','worker2','load_balancer','client'):
		#	shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
		#	shutit.login(command='sudo su -',prompt_prefix=machine,password='vagrant')
		#	shutit.install('xterm') # for resize
		#	shutit.logout()
		#	shutit.logout()
		# Log in and set up the load balancer
		shutit.login(command='vagrant ssh load_balancer',prompt_prefix='load_balancer',note='Log into the load balancer machine')
		shutit.login(command='sudo su -',prompt_prefix='load_balancer',password='vagrant',note='Elevate to root')
		shutit.install('haproxy',note='Install haproxy. We use haproxy to be the interface for external requests to the kubernetes cluster.')
		shutit.send_file('''/etc/haproxy/haproxy.cfg''','''global
    log /dev/log    local0
    log /dev/log    local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    tcp
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000

frontend k8snodes
    bind *:6443
    mode tcp
    default_backend nodes

backend nodes
    mode tcp
    balance roundrobin
    server controller0 ''' + controller0ip + ''':6443 check
    server controller1 ''' + controller1ip + ''':6443 check
    server controller2 ''' + controller2ip + ''':6443 check''',note='Create the haproxy config file, and point requests to 6443 to the three controller ips')
		shutit.send('mkdir -p /run/haproxy')
		shutit.send('systemctl daemon-reload',note='Reload the haproxy config.')
		shutit.send('systemctl enable haproxy',note='Enable the haproxy service.')
		shutit.send('systemctl start haproxy',note='Start the haproxy service.')
		shutit.send('systemctl status haproxy --no-pager',note='Check all is ok with the service.')

		# https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/02-certificate-authority.md
		shutit.send('cd')
		shutit.send('mkdir -p certs && cd certs',note='Create a certs folder')
		shutit.send('wget https://pkg.cfssl.org/R1.2/cfssl_linux-amd64',note='Get the cfssl binaries')
		shutit.send('wget https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64',note='Get the cfssl binaries')
		shutit.send('chmod +x cfssl_linux-amd64',note='Make the binaries executable')
		shutit.send('chmod +x cfssljson_linux-amd64',note='Make the binaries executable')
		shutit.send('mv cfssl_linux-amd64 /usr/local/bin/cfssl',note='Move the binaries to a path folder')
		shutit.send('mv cfssljson_linux-amd64 /usr/local/bin/cfssljson',note='Move the binaries to a path folder')
		shutit.send('''echo '{
  "signing": {
    "default": {
      "expiry": "8760h"
    },
    "profiles": {
      "kubernetes": {
        "usages": ["signing", "key encipherment", "server auth", "client auth"],
        "expiry": "8760h"
      }
    }
  }
}' > ca-config.json''',note='Create the certificate authority creation config file')
		shutit.send('''echo '{
  "CN": "Kubernetes",
  "key": {
    "algo": "rsa",
    "size": 2048
  },
  "names": [
    {
      "C": "US",
      "L": "Portland",
      "O": "Kubernetes",
      "OU": "CA",
      "ST": "Oregon"
    }
  ]
}' > ca-csr.json''',note='Create the certificate authority signing request file with details of the certificate')
		shutit.send('cfssl gencert -initca ca-csr.json | cfssljson -bare ca',note='Generate the certificate authority certificate')
		shutit.send('openssl x509 -in ca.pem -text -noout',note='Check all is ok with the cert')
		shutit.send('''cat > kubernetes-csr.json <<EOF
{
  "CN": "kubernetes",
  "hosts": [
    "worker0",
    "worker1",
    "worker2",
    "controller0",
    "controller1",
    "controller2",
    "ip-192-168-2-2",
    "ip-192-168-2-3",
    "ip-192-168-2-4",
    "ip-192-168-2-5",
    "ip-192-168-2-6",
    "ip-192-168-2-7",
    "ip-192-168-2-8",
    "10.32.0.1",
    "''' + controller0ip + '''",
    "''' + controller1ip + '''",
    "''' + controller2ip + '''",
    "''' + worker0ip + '''",
    "''' + worker1ip + '''",
    "''' + worker2ip + '''",
    "''' + load_balancer_ip + '''",
    "127.0.0.1"
  ],
  "key": {
    "algo": "rsa",
    "size": 2048
  },
  "names": [
    {
      "C": "US",
      "L": "Portland",
      "O": "Kubernetes",
      "OU": "Cluster",
      "ST": "Oregon"
    }
  ]
}
EOF''',note='Create the details of the kubernetes certificate')
		shutit.send('cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes kubernetes-csr.json | cfssljson -bare kubernetes',note='Create the kubernetes certificate')
		shutit.send('openssl x509 -in kubernetes.pem -text -noout',note='Check all is ok with the kubernetes certificate')
		shutit.send('ls *pem',note='Copying the key files to the various servers')
		for ip in (controller0ip, controller1ip, controller2ip, worker0ip, worker1ip, worker2ip, client_ip):
			for f in ('kubernetes.pem','ca.pem','kubernetes-key.pem'):
				shutit.multisend('scp ' + f + ' vagrant@' + ip + ':~/',{'continue':'yes','assword':'vagrant'})
		shutit.logout()
		shutit.logout()

		# etcd HA cluster - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/03-etcd.md
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine,note='Log onto machine: ' + machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine,note='Elevate privileges to root')
			shutit.send('mkdir -p /etc/etcd/',note='Ensure the etcd config folder exists')
			shutit.send('cp /home/vagrant/ca.pem /home/vagrant/kubernetes-key.pem /home/vagrant/kubernetes.pem /etc/etcd/',note='Copy the certificates to the etcd config folder')
			shutit.send('curl -L https://github.com/coreos/etcd/releases/download/v3.0.10/etcd-v3.0.10-linux-amd64.tar.gz | tar -zxvf -',note='Get the etcd binaries')
			shutit.send('mv etcd-v3.0.10-linux-amd64/etcd* /usr/bin/',note='Move the etcd binaries to the path')
			shutit.send(' mkdir -p /var/lib/etcd',note='Create the etcd folder in var')
			shutit.send('''cat > etcd.service <<"EOF"
[Unit]
Description=etcd
Documentation=https://github.com/coreos

[Service]
ExecStart=/usr/bin/etcd --name ETCD_NAME \
  --cert-file=/etc/etcd/kubernetes.pem \
  --key-file=/etc/etcd/kubernetes-key.pem \
  --peer-cert-file=/etc/etcd/kubernetes.pem \
  --peer-key-file=/etc/etcd/kubernetes-key.pem \
  --trusted-ca-file=/etc/etcd/ca.pem \
  --peer-trusted-ca-file=/etc/etcd/ca.pem \
  --initial-advertise-peer-urls https://INTERNAL_IP:2380 \
  --listen-peer-urls https://INTERNAL_IP:2380 \
  --listen-client-urls https://INTERNAL_IP:2379,http://127.0.0.1:2379 \
  --advertise-client-urls https://INTERNAL_IP:2379 \
  --initial-cluster-token etcd-cluster-0 \
  --initial-cluster controller0=https://''' + controller0ip + ''':2380,controller1=https://''' + controller1ip + ''':2380,controller2=https://''' + controller2ip + ''':2380 \
  --initial-cluster-state new \
  --data-dir=/var/lib/etcd
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF''',note='Create the etcd service file.')
			shutit.send('''export INTERNAL_IP=$(ifconfig eth1 | grep inet.addr | awk '{print $2}' | awk -F: '{print $2}')''',note='Get the external ip for this machine')
			shutit.send('''sed -i s/INTERNAL_IP/${INTERNAL_IP}/g etcd.service''')
			shutit.send('''sed -i s/ETCD_NAME/''' + machine + '''/g etcd.service''')
			shutit.send('''mv etcd.service /etc/systemd/system/''',note='Put the service file in the right place')
			shutit.send('systemctl daemon-reload',note='Reload the systemctl config.')
			shutit.send('systemctl enable etcd',note='Enable the etcd service.')
			shutit.send('systemctl start etcd',note='Start the etcd service.')
			shutit.send('systemctl status etcd --no-pager',note='Check all is ok with the service.')
			shutit.logout()
			shutit.logout()
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine,note='Log into the machine: ' + machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine,note='Elevate privileges to root')
			shutit.send_and_require('etcdctl --ca-file=/etc/etcd/ca.pem cluster-health','healthy',note='Check the cluster looks healthy from machine: ' + machine)
			shutit.logout()
			shutit.logout()
		# kubernetes controller - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/04-kubernetes-controller.md
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine,note='Log into the machine: ' + machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine,note='Elevate privileges to root')
			shutit.send('mkdir -p /var/lib/kubernetes',note='Ensure the kubernetes folder exists in var')
			shutit.send('cp /home/vagrant/ca.pem /home/vagrant/kubernetes-key.pem /home/vagrant/kubernetes.pem /var/lib/kubernetes/',note='Copy the certificates to the kubernetes folder')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kube-apiserver',note='Get the binaries')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kube-controller-manager',note='Get the binaries')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kube-scheduler',note='Get the binaries')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kubectl',note='Get the binaries')
			shutit.send('chmod +x kube-apiserver kube-controller-manager kube-scheduler kubectl',note='Chown the binaries')
			shutit.send('mv kube-apiserver kube-controller-manager kube-scheduler kubectl /usr/bin/',note='Move the binaries to the path')
			shutit.send('wget https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/token.csv',note='Get the token file')
			
			# TODO: replace default token 'changeme' aka kubetoken in token.csv
			shutit.send('mv token.csv /var/lib/kubernetes/',note='Move the token file')
			shutit.send('wget https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/authorization-policy.jsonl',note='Get the authorization policy')
			shutit.send('mv authorization-policy.jsonl /var/lib/kubernetes/',note='Move the authorization policy to the kubernetes folder')
			shutit.send('''cat > kube-apiserver.service <<"EOF"
[Unit]
Description=Kubernetes API Server
Documentation=https://github.com/GoogleCloudPlatform/kubernetes

[Service]
ExecStart=/usr/bin/kube-apiserver \
  --admission-control=NamespaceLifecycle,LimitRanger,SecurityContextDeny,ServiceAccount,ResourceQuota \
  --advertise-address=INTERNAL_IP \
  --allow-privileged=true \
  --apiserver-count=3 \
  --authorization-mode=ABAC \
  --authorization-policy-file=/var/lib/kubernetes/authorization-policy.jsonl \
  --bind-address=0.0.0.0 \
  --enable-swagger-ui=true \
  --etcd-cafile=/var/lib/kubernetes/ca.pem \
  --insecure-bind-address=0.0.0.0 \
  --kubelet-certificate-authority=/var/lib/kubernetes/ca.pem \
  --etcd-servers=https://''' + controller0ip + ''':2379,https://''' + controller1ip + ''':2379,https://''' + controller2ip + ''':2379 \
  --service-account-key-file=/var/lib/kubernetes/kubernetes-key.pem \
  --service-cluster-ip-range=10.32.0.0/16 \
  --service-node-port-range=30000-32767 \
  --tls-cert-file=/var/lib/kubernetes/kubernetes.pem \
  --tls-private-key-file=/var/lib/kubernetes/kubernetes-key.pem \
  --token-auth-file=/var/lib/kubernetes/token.csv \
  --v=2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF''',note='Create the kubernetes apiserver service. Note that the service ip cluster range is 10.23.0.0/16 - this is the network that will be used for services.')
			shutit.send('''export INTERNAL_IP=$(ifconfig eth1 | grep inet.addr | awk '{print $2}' | awk -F: '{print $2}')''',note='Get the external ip of this host')
			shutit.send('''sed -i s/INTERNAL_IP/$INTERNAL_IP/g kube-apiserver.service''',note='Overwrite the internal ip in the "advertise-address" section of the service file')
			shutit.send('mv kube-apiserver.service /etc/systemd/system/',note='Install the service file')
			shutit.send('systemctl daemon-reload',note='Reload the systemctl config.')
			shutit.send('systemctl enable kube-apiserver',note='Enable the kube-apiserver service')
			shutit.send('systemctl start kube-apiserver',note='Start the kube-apiserver service')
			shutit.send('systemctl status kube-apiserver --no-pager',note='Check the kube-apiserver service is up ok')
			# kube controller manager service
			shutit.send('''cat > kube-controller-manager.service <<"EOF"
[Unit]
Description=Kubernetes Controller Manager
Documentation=https://github.com/GoogleCloudPlatform/kubernetes

[Service]
ExecStart=/usr/bin/kube-controller-manager \
  --allocate-node-cidrs=true \
  --cluster-cidr=10.200.0.0/16 \
  --cluster-name=kubernetes \
  --leader-elect=true \
  --master=http://INTERNAL_IP:8080 \
  --root-ca-file=/var/lib/kubernetes/ca.pem \
  --service-account-private-key-file=/var/lib/kubernetes/kubernetes-key.pem \
  --service-cluster-ip-range=10.32.0.0/24 \
  --v=2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF''',note='Create the kube-controller-manager service file')
			shutit.send('sed -i s/INTERNAL_IP/$INTERNAL_IP/g kube-controller-manager.service',note='Replace INTERNAL_IP in the master section with the IP of this host.')
			shutit.send('mv kube-controller-manager.service /etc/systemd/system/',note='Move the service file into systemd')
			shutit.send('systemctl daemon-reload',note='Reload the systemctl config.')
			shutit.send('systemctl enable kube-controller-manager',note='Enable the kube-controller-manager service')
			shutit.send('systemctl start kube-controller-manager',note='Start the kube-controller-manager service')
			shutit.send('systemctl status kube-controller-manager --no-pager',note='Check the kube-controller-manager is ok')
			# kube scheduler service
			shutit.send('''cat > kube-scheduler.service <<"EOF"
[Unit]
Description=Kubernetes Scheduler
Documentation=https://github.com/GoogleCloudPlatform/kubernetes

[Service]
ExecStart=/usr/bin/kube-scheduler \
  --leader-elect=true \
  --master=http://INTERNAL_IP:8080 \
  --v=2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF''')
			shutit.send('sed -i s/INTERNAL_IP/$INTERNAL_IP/g kube-scheduler.service')
			shutit.send('mv kube-scheduler.service /etc/systemd/system/')
			shutit.send('systemctl daemon-reload',note='Reload the systemctl config.')
			shutit.send('systemctl enable kube-scheduler',note='Enable the kube-scheduler')
			shutit.send('systemctl start kube-scheduler',note='Start the kube-scheduler')
			shutit.send('systemctl status kube-scheduler --no-pager',note='Check the kube-scheduler service is ok')
			shutit.logout()
			shutit.logout()
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
			shutit.send_and_require('kubectl get componentstatuses','Healthy',note='Checking the status of the kube cluster from machine: ' + machine)
			shutit.logout()
			shutit.logout()

		# Kubernetes workers - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/05-kubernetes-worker.md
		for machine in ('worker0','worker1','worker2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
			shutit.send('mkdir -p /var/lib/kubernetes')
			shutit.send('cp /home/vagrant/ca.pem /home/vagrant/kubernetes-key.pem /home/vagrant/kubernetes.pem /var/lib/kubernetes/')
			shutit.send('curl -L https://get.docker.com/builds/Linux/x86_64/docker-1.12.1.tgz | tar -zxvf -')
			shutit.send('cp docker/docker* /usr/bin/')
			shutit.send("""sudo sh -c 'echo "[Unit]
Description=Docker Application Container Engine
Documentation=http://docs.docker.io

[Service]
ExecStart=/usr/bin/docker daemon \
  --iptables=false \
  --ip-masq=false \
  --host=unix:///var/run/docker.sock \
  --log-level=error \
  --storage-driver=overlay
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/docker.service'""")
			shutit.send('systemctl daemon-reload',note='Reload the systemctl config.')
			shutit.send('systemctl enable docker')
			shutit.send('systemctl start docker')
			shutit.send('docker version')
			shutit.send('mkdir -p /opt/cni')
			shutit.send('curl -L https://storage.googleapis.com/kubernetes-release/network-plugins/cni-07a8a28637e97b22eb8dfe710eeae1344f69d16e.tar.gz | tar -zxvf - -C /opt/cni')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kubectl')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kube-proxy')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kubelet')
			shutit.send('chmod +x kubectl kube-proxy kubelet')
			shutit.send('mv kubectl kube-proxy kubelet /usr/bin/')
			shutit.send('mkdir -p /var/lib/kubelet/')
			# NOTE: changeme token is in as raw below in original
			shutit.send("""sudo sh -c 'echo "apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority: /var/lib/kubernetes/ca.pem
    server: https://""" + controller0ip + """:6443
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: kubelet
  name: kubelet
current-context: kubelet
users:
- name: kubelet
  user:
    token: """ + kube_token + '''" > /var/lib/kubelet/kubeconfig''' + "'")
			shutit.send("""sudo sh -c 'echo "[Unit]
Description=Kubernetes Kubelet
Documentation=https://github.com/GoogleCloudPlatform/kubernetes
After=docker.service
Requires=docker.service

[Service]
ExecStart=/usr/bin/kubelet \
  --allow-privileged=true \
  --api-servers=https://""" + controller0ip + """:6443,https://""" + controller1ip + """:6443,https://""" + controller2ip + """:6443 \
  --cloud-provider= \
  --cluster-dns=10.32.0.10 \
  --cluster-domain=cluster.local \
  --configure-cbr0=true \
  --container-runtime=docker \
  --docker=unix:///var/run/docker.sock \
  --network-plugin=kubenet \
  --kubeconfig=/var/lib/kubelet/kubeconfig \
  --reconcile-cidr=true \
  --serialize-image-pulls=false \
  --tls-cert-file=/var/lib/kubernetes/kubernetes.pem \
  --tls-private-key-file=/var/lib/kubernetes/kubernetes-key.pem \
  --v=2

Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/kubelet.service'""")
			shutit.send('systemctl daemon-reload',note='Reload the systemctl config.')
			shutit.send('systemctl enable kubelet')
			shutit.send('systemctl start kubelet')
			shutit.send('systemctl status kubelet --no-pager')
			# Should controller0ip be load balancer ip?
			shutit.send("""sudo sh -c 'echo "[Unit]
Description=Kubernetes Kube Proxy
Documentation=https://github.com/GoogleCloudPlatform/kubernetes

[Service]
ExecStart=/usr/bin/kube-proxy \
  --master=https://""" + controller0ip + """:6443 \
  --kubeconfig=/var/lib/kubelet/kubeconfig \
  --proxy-mode=iptables \
  --v=2

Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/kube-proxy.service'""")
			shutit.send('systemctl daemon-reload',note='Reload the systemctl config.')
			shutit.send('systemctl enable kube-proxy')
			shutit.send('systemctl start kube-proxy')
			shutit.send('systemctl status kube-proxy --no-pager')
			shutit.logout()
			shutit.logout()

		# restart haproxy (not sure why, possibly health checks fails it up to here)
		machine = 'load_balancer'
		shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
		shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
		shutit.send('systemctl restart haproxy')
		shutit.logout()
		shutit.logout()


		# kubectl client - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/06-kubectl.md
		machine = 'client'
		shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
		shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
		shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kubectl')
		shutit.send('chmod +x kubectl')
		shutit.send('mv kubectl /usr/local/bin')
		shutit.send('cp /home/vagrant/ca.pem /home/vagrant/kubernetes-key.pem /home/vagrant/kubernetes.pem /root')
		shutit.send('kubectl config set-cluster kubernetes-the-hard-way --certificate-authority=/root/ca.pem --embed-certs=true --server=https://' + load_balancer_ip + ':6443')
		shutit.send('kubectl config set-credentials admin --token ' + kube_token)
		shutit.send('kubectl config set-context default-context --cluster=kubernetes-the-hard-way --user=admin')
		shutit.send('kubectl config use-context default-context')
		shutit.send_and_require('kubectl get componentstatuses','etcd-2.*Healthy')
		shutit.send_and_require('kubectl get nodes','worker2.*Ready')
		# network routes - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/07-network.md
		# TODO: there's a problem here (altho everything else seems to work):
		# ip route add here? https://github.com/kubernetes/kubernetes/issues/27161
		shutit.send(r"""kubectl get nodes --output=jsonpath='{range .items[*]}{.status.addresses[?(@.type=="InternalIP")].address} {.spec.podCIDR} {.spec.externalID} {"\n"}{end}'""")
		worker0cidr = shutit.send(r"""kubectl get nodes --output=jsonpath='{.spec.podCIDR} {.spec.externalID} {"\n"}{end}' | grep worker0 | awk '{print $1}'""")
		worker1cidr = shutit.send(r"""kubectl get nodes --output=jsonpath='{.spec.podCIDR} {.spec.externalID} {"\n"}{end}' | grep worker1 | awk '{print $1}'""")
		worker2cidr = shutit.send(r"""kubectl get nodes --output=jsonpath='{.spec.podCIDR} {.spec.externalID} {"\n"}{end}' | grep worker2 | awk '{print $1}'""")
		# Log out of client
		shutit.logout()
		shutit.logout()

		# Log onto each of the workers and add the route to each node. We are
		# doing layer3 networking, so ...
		# Do worker0
		worker_machine = 'worker0'
		shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
		shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
		shutit.send('ip route add ' + worker1cidr + ' via ' + worker1ip)
		shutit.send('ip route add ' + worker2cidr + ' via ' + worker2ip)
		shutit.logout()
		shutit.logout()

		# Do worker1
		worker_machine = 'worker1'
		shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
		shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
		shutit.send('ip route add ' + worker0cidr + ' via ' + worker0ip)
		shutit.send('ip route add ' + worker2cidr + ' via ' + worker2ip)
		shutit.logout()
		shutit.logout()

		# Do worker2
		worker_machine = 'worker2'
		shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
		shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
		shutit.send('ip route add ' + worker0cidr + ' via ' + worker0ip)
		shutit.send('ip route add ' + worker1cidr + ' via ' + worker1ip)
		shutit.logout()
		shutit.logout()

		# Log back onto the client
		shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
		shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
		# cluster dns add-on - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/08-dns-addon.md
		shutit.send('kubectl create -f https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/services/kubedns.yaml')
		shutit.send('kubectl --namespace=kube-system get svc')
		shutit.send('kubectl create -f https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/deployments/kubedns.yaml')
		shutit.send_and_require('kubectl --namespace=kube-system get pods','Running')

		# smoke test - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/09-smoke-test.md
		shutit.send('kubectl run nginx --image=nginx --port=80 --replicas=3')
		#shutit.send_until('kubectl get pods -o wide','Running')
		shutit.send('kubectl expose deployment nginx --type NodePort')
		shutit.send('kubectl get svc')
		port = shutit.send_and_get_output("""kubectl get svc nginx --output=jsonpath='{range .spec.ports[0]}{.nodePort}'""")
		
		shutit.pause_point('')
		shutit.logout()
		shutit.logout()

		# cleanup - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/10-cleanup.md
		# Not needed - just run ./destroy_vms.sh
		return True

	def get_config(self, shutit):
		#shutit.get_config(self.module_id,'vagrant_image',default='ubuntu/trusty64')
		shutit.get_config(self.module_id,'vagrant_image',default='velocity42/xenial64')
		shutit.get_config(self.module_id,'vagrant_provider',default='virtualbox')
		shutit.get_config(self.module_id,'gui',default='false')
		shutit.get_config(self.module_id,'memory',default='1024')

		return True

	def test(self, shutit):

		return True

	def finalize(self, shutit):

		return True

	def isinstalled(self, shutit):

		return False

	def start(self, shutit):

		return True

	def stop(self, shutit):

		return True

def module():
	return shutit_k8s_the_hard_way(
		'shutit.shutit_k8s_the_hard_way.shutit_k8s_the_hard_way', 538738828.0001,   
		description='',
		maintainer='',
		delivery_methods=['bash'],
		depends=['shutit.tk.setup','shutit-library.virtualbox.virtualbox.virtualbox','tk.shutit.vagrant.vagrant.vagrant']
	)
