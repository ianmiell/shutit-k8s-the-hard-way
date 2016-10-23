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
		shutit.send_file(home_dir + '/' + module_name + '/Vagrantfile','''

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |vb|
    vb.gui = ''' + gui + '''
    vb.memory = "''' + memory + '''"
  end

  config.vm.define "controller0" do |controller0|    
    controller0.vm.box = ''' + '"' + vagrant_image + '"' + '''
    controller0.vm.hostname = "controller0"
    controller0.vm.network "private_network", ip: "192.168.2.2"
  end

  config.vm.define "controller1" do |controller1|
    controller1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    controller1.vm.network :private_network, ip: "192.168.2.3"
    controller1.vm.hostname = "controller1"
  end

  config.vm.define "controller2" do |controller2|
    controller2.vm.box = ''' + '"' + vagrant_image + '"' + '''
    controller2.vm.network :private_network, ip: "192.168.2.4"
    controller2.vm.hostname = "controller2"
  end

  config.vm.define "worker0" do |worker0|    
    worker0.vm.box = ''' + '"' + vagrant_image + '"' + '''
    worker0.vm.network "private_network", ip: "192.168.2.5"
    worker0.vm.hostname = "worker0"
  end

  config.vm.define "worker1" do |worker1|
    worker1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    worker1.vm.network :private_network, ip: "192.168.2.6"
    worker1.vm.hostname = "worker1"
  end

  config.vm.define "worker2" do |worker2|
    worker2.vm.box = ''' + '"' + vagrant_image + '"' + '''
    worker2.vm.network :private_network, ip: "192.168.2.7"
    worker2.vm.hostname = "worker2"
  end

  config.vm.define "load_balancer" do |load_balancer|
    load_balancer.vm.box = ''' + '"' + vagrant_image + '"' + '''
    load_balancer.vm.network :private_network, ip: "192.168.2.8"
    load_balancer.vm.hostname = "load-balancer"
  end
end''')
		shutit.send('cd ~/' + module_name)
		shutit.send('vagrant up --provider virtualbox',timeout=99999)

		# Set up the load balancer - tcp 6443 as per https://github.com/kelseyhightower/kubernetes-the-hard-way/blob/master/docs/01-infrastructure-aws.md
		shutit.login(command='vagrant ssh load_balancer')
		shutit.login(command='sudo su -',password='vagrant')
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
		shutit.send('''export KUBERNETES_PUBLIC_ADDRESS=192.168.2.8''')
		shutit.send('''cat > kubernetes-csr.json <<EOF
{
  "CN": "kubernetes",
  "hosts": [
    "worker0",
    "worker1",
    "worker2",
    "ip-10-240-0-20",
    "ip-10-240-0-21",
    "ip-10-240-0-22",
    "10.32.0.1",
    "10.240.0.10",
    "10.240.0.11",
    "10.240.0.12",
    "10.240.0.20",
    "10.240.0.21",
    "10.240.0.22",
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
		for ip in ('192.168.2.2','192.168.2.3','192.168.2.4','192.168.2.5','192.168.2.6','192.168.2.7'):
			for f in ('kubernetes.pem','ca.pem','kubernetes-key.pem'):
				shutit.multisend('scp ' + f + ' vagrant@' + ip + ':~/',{'continue':'yes','assword':'vagrant'})
		shutit.logout()
		shutit.logout()

		# etcd HA cluster
		for machine in ('controller0','controller1','controller2'):
			shutit.login(command='vagrant ssh ' + machine)
			shutit.login(command='sudo su -',password='vagrant')
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
  --initial-cluster controller0=https://10.240.0.10:2380,controller1=https://10.240.0.11:2380,controller2=https://10.240.0.12:2380 \
  --initial-cluster-state new \
  --data-dir=/var/lib/etcd
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF''')
			shutit.send('''export INTERNAL_IP=$(ifconfig eth1 | grep inet.addr | awk '{print $2}' | awk -F: '{print $2}')''')
			shutit.send('''ETCD_NAME=controller$(echo $INTERNAL_IP | cut -c 11)''')
			shutit.send('''sed -i s/INTERNAL_IP/${INTERNAL_IP}/g etcd.service''')
			shutit.send('''sed -i s/ETCD_NAME/${ETCD_NAME}/g etcd.service''')
			shutit.pause_point('systemctl install?')
			shutit.send('''mv etcd.service /etc/systemd/system/''')
			shutit.logout()
			shutit.logout()
		shutit.pause_point('')
		return True

	def get_config(self, shutit):
		shutit.get_config(self.module_id,'vagrant_image',default='ubuntu/trusty64')
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
