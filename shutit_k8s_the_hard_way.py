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
		for machine in ('controller0','controller1','controller2','worker0','worker1','worker2','load_balancer','client'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
			shutit.login(command='sudo su -',prompt_prefix=machine,password='vagrant')
			shutit.send('apt-get update')
			shutit.send('apt install xterm') # for resize
			shutit.logout()
			shutit.logout()

		shutit.login(command='vagrant ssh load_balancer',prompt_prefix='load_balancer')
		shutit.login(command='sudo su -',prompt_prefix='load_balancer',password='vagrant')
		shutit.install('haproxy')
		shutit.send_file('''/etc/haproxy.cfg''','''global
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
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 408 /etc/haproxy/errors/408.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http
    errorfile 504 /etc/haproxy/errors/504.http

frontend k8snodes
    bind *:6443
    mode tcp
    default_backend nodes

backend nodes
    mode tcp
    balance roundrobin
    server controller0 192.168.2.2:6443 check
    server controller0 192.168.2.3:6443 check
    server controller0 192.168.2.4:6443 check''')
		shutit.send('mkdir -p /run/haproxy')
		shutit.send('haproxy -f /etc/haproxy.cfg')

		# https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/02-certificate-authority.md
		shutit.send('cd')
		shutit.send('mkdir -p certs')
		shutit.send('cd certs')
		shutit.send('wget https://pkg.cfssl.org/R1.2/cfssl_linux-amd64')
		shutit.send('wget https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64')
		shutit.send('chmod +x cfssl_linux-amd64')
		shutit.send('chmod +x cfssljson_linux-amd64')
		shutit.send('sudo mv cfssl_linux-amd64 /usr/local/bin/cfssl')
		shutit.send('sudo mv cfssljson_linux-amd64 /usr/local/bin/cfssljson')
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
}' > ca-config.json''')
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
}' > ca-csr.json''')
		shutit.send('cfssl gencert -initca ca-csr.json | cfssljson -bare ca')
		shutit.send('openssl x509 -in ca.pem -text -noout')
		shutit.send('''export KUBERNETES_PUBLIC_ADDRESS=''' + load_balancer_ip)
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
    "ip-192-168-2-9",
    "10.32.0.1",
    "''' + controller0ip + '''",
    "''' + controller1ip + '''",
    "''' + controller2ip + '''",
    "''' + worker0ip + '''",
    "''' + worker1ip + '''",
    "''' + worker2ip + '''",
    "${KUBERNETES_PUBLIC_ADDRESS}",
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
EOF''')
		shutit.send('cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes kubernetes-csr.json | cfssljson -bare kubernetes')
		shutit.send('openssl x509 -in kubernetes.pem -text -noout')
		for ip in (controller0ip,controller1ip,controller2ip,worker0ip,worker1ip,worker2ip,client_ip):
			for f in ('kubernetes.pem','ca.pem','kubernetes-key.pem'):
				shutit.multisend('scp ' + f + ' vagrant@' + ip + ':~/',{'continue':'yes','assword':'vagrant'})
		shutit.logout()
		shutit.logout()

		# etcd HA cluster - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/03-etcd.md
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
			shutit.send('mkdir -p /etc/etcd/')
			shutit.send('cp /home/vagrant/ca.pem /home/vagrant/kubernetes-key.pem /home/vagrant/kubernetes.pem /etc/etcd/')
			shutit.send('curl -L https://github.com/coreos/etcd/releases/download/v3.0.10/etcd-v3.0.10-linux-amd64.tar.gz | tar -zxvf -')
			shutit.send('mv etcd-v3.0.10-linux-amd64/etcd* /usr/bin/')
			shutit.send(' mkdir -p /var/lib/etcd')
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
EOF''')
			shutit.send('''export INTERNAL_IP=$(ifconfig eth1 | grep inet.addr | awk '{print $2}' | awk -F: '{print $2}')''')
			shutit.send('''export ETCD_NAME=''' + machine)
			shutit.send('''sed -i s/INTERNAL_IP/${INTERNAL_IP}/g etcd.service''')
			shutit.send('''sed -i s/ETCD_NAME/${ETCD_NAME}/g etcd.service''')
			shutit.send('''mv etcd.service /etc/systemd/system/''')
			shutit.send('systemctl daemon-reload')
			shutit.send('systemctl enable etcd')
			shutit.send('systemctl start etcd')
			shutit.send('systemctl status etcd --no-pager')
			shutit.logout()
			shutit.logout()
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
			shutit.send_and_require('etcdctl --ca-file=/etc/etcd/ca.pem cluster-health','healthy')
			shutit.logout()
			shutit.logout()
		# kubernetes controller - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/04-kubernetes-controller.md
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
			shutit.send('mkdir -p /var/lib/kubernetes')
			shutit.send('cp /home/vagrant/ca.pem /home/vagrant/kubernetes-key.pem /home/vagrant/kubernetes.pem /var/lib/kubernetes/')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kube-apiserver')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kube-controller-manager')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kube-scheduler')
			shutit.send('wget https://storage.googleapis.com/kubernetes-release/release/v1.4.0/bin/linux/amd64/kubectl')
			shutit.send('chmod +x kube-apiserver kube-controller-manager kube-scheduler kubectl')
			shutit.send('mv kube-apiserver kube-controller-manager kube-scheduler kubectl /usr/bin/')
			shutit.send('wget https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/token.csv')
			
			# TODO: replace default token 'changeme' aka kubetoken in token.csv
			shutit.send('mv token.csv /var/lib/kubernetes/')
			shutit.send('wget https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/authorization-policy.jsonl')
			shutit.send('mv authorization-policy.jsonl /var/lib/kubernetes/')
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
EOF''')
			shutit.send('''export INTERNAL_IP=$(ifconfig eth1 | grep inet.addr | awk '{print $2}' | awk -F: '{print $2}')''')
			shutit.send('''sed -i s/INTERNAL_IP/$INTERNAL_IP/g kube-apiserver.service''')
			shutit.send('''mv kube-apiserver.service /etc/systemd/system/''')
			shutit.send('''systemctl daemon-reload''')
			shutit.send('''systemctl enable kube-apiserver''')
			shutit.send('''systemctl start kube-apiserver''')
			shutit.send('''systemctl status kube-apiserver --no-pager''')

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
EOF''')
			shutit.send('sed -i s/INTERNAL_IP/$INTERNAL_IP/g kube-controller-manager.service')
			shutit.send('mv kube-controller-manager.service /etc/systemd/system/')
			shutit.send('systemctl daemon-reload')
			shutit.send('systemctl enable kube-controller-manager')
			shutit.send('systemctl start kube-controller-manager')
			shutit.send('systemctl status kube-controller-manager --no-pager')
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
			shutit.send('systemctl daemon-reload')
			shutit.send('systemctl enable kube-scheduler')
			shutit.send('systemctl start kube-scheduler')
			shutit.send('systemctl status kube-scheduler --no-pager')
			shutit.logout()
			shutit.logout()
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine,prompt_prefix=machine)
			shutit.login(command='sudo su -',password='vagrant',prompt_prefix=machine)
			shutit.send_and_require('kubectl get componentstatuses','Healthy')
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
			shutit.send('systemctl daemon-reload')
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
			shutit.send('systemctl daemon-reload')
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
			shutit.send('systemctl daemon-reload')
			shutit.send('systemctl enable kube-proxy')
			shutit.send('systemctl start kube-proxy')
			shutit.send('systemctl status kube-proxy --no-pager')
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
		shutit.send(r"""kubectl get nodes --output=jsonpath='{range .items[*]}{.status.addresses[?(@.type=="InternalIP")].address} {.spec.podCIDR} {"\n"}{end}'""")
		# TODO: Vagrant's 10.0.2.15 gets in the way here?
		#10.0.2.15 10.200.0.0/24 
		#10.0.2.15 10.200.1.0/24 
		#10.0.2.15 10.200.2.0/24 

		# cluster dns add-on - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/08-dns-addon.md
		shutit.send('kubectl create -f https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/services/kubedns.yaml')
		shutit.send('kubectl --namespace=kube-system get svc')
		shutit.send('kubectl create -f https://raw.githubusercontent.com/kelseyhightower/kubernetes-the-hard-way/master/deployments/kubedns.yaml')
		shutit.send_and_require('kubectl --namespace=kube-system get pods','Running')

		# smoke test - https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/09-smoke-test.md
		shutit.send('kubectl run nginx --image=nginx --port=80 --replicas=3')
		shutit.send_until('kubectl get pods -o wide','Running.*worker2')
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
