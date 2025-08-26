# AI-Driven Anomaly Detector as a Service

An intelligent, AI-powered anomaly detection system designed for Kubernetes service mesh environments. This system automatically monitors network traffic patterns, detects DDoS attacks using machine learning, and implements intelligent traffic failover to maintain service availability.

## 🚀 Overview

This system consists of three main components working together to provide intelligent anomaly detection and automated response:

1. **DDoS Detector Service** - AI-powered traffic analysis and anomaly detection
2. **Report Receiver Service** - Intelligent traffic management and failover orchestration
3. **Ratings Service (v2)** - Backup service for traffic failover scenarios

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   DDoS Detector │    │ Report Receiver  │    │  Ratings v2     │
│   (ML Service)  │───▶│  (Traffic Mgmt)  │───▶│  (Backup)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Istio Proxy    │    │  Kubernetes      │    │  Traffic        │
│  Logs (Envoy)   │    │  API             │    │  Failover      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔧 Components

### 1. DDoS Detector Service (`git/` folder)

**Purpose**: Monitors network traffic patterns and detects DDoS attacks using machine learning.

**Key Features**:
- Real-time log collection from Istio proxy containers
- Feature extraction from network traffic data
- ML-based DDoS detection using pre-trained models
- LIME explanations for detected anomalies
- Automatic report generation and submission

**Files**:
- `ddos_detection.py` - Main detection logic
- `ddos_detection_model.pkl` - Pre-trained ML model
- `train_sample.csv` - Training data sample
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies

### 2. Report Receiver Service (`app/` folder)

**Purpose**: Receives anomaly reports and orchestrates intelligent traffic management.

**Key Features**:
- REST API endpoint for receiving anomaly reports
- Automatic traffic failover from v1 to v2 services
- Kubernetes API integration for service management
- Istio VirtualService patching for traffic routing

**Files**:
- `report_receiver.py` - Main service logic
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies

### 3. Ratings Service v2 (`ratings-v2/` folder)

**Purpose**: Backup service that receives traffic during failover scenarios.

**Key Features**:
- Database-backed ratings service
- High availability design
- Automatic traffic reception during failover

**Files**:
- `ratings.js` - Service implementation
- `Dockerfile` - Container configuration

### 4. Kubernetes Manifests (`ml/` folder)

**Purpose**: Infrastructure configuration for deploying the entire system.

**Files**:
- `ddos-detector-deployment.yaml` - DDoS detector deployment
- `ddos-detector-serviceaccount.yaml` - Service account and RBAC
- `report-receiver-deployment.yaml` - Report receiver deployment
- `report-receiver-rbac.yaml` - RBAC configuration
- `ratings-v2.yaml` - Ratings v2 service deployment
- `ratings-istio.yaml` - Istio traffic routing rules
- `logs.yaml` - Envoy access log configuration

## 🚀 Complete Setup and Installation Guide

### Prerequisites

- Windows/Mac/Linux host machine
- At least 8GB RAM available for VirtualBox
- At least 100GB free disk space
- Internet connection for downloads

### Step 1: Setting Up Ubuntu Virtual Machine

#### 1.1 Install VirtualBox
1. Download VirtualBox from [https://www.virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads)
2. Install VirtualBox on your host machine

#### 1.2 Download Ubuntu ISO
1. Download Ubuntu 22.04 LTS (Jammy Jellyfish) from [https://releases.ubuntu.com/jammy/](https://releases.ubuntu.com/jammy/)
2. Choose the **64-bit PC (AMD64) desktop image**

#### 1.3 Create Virtual Machine
1. Open VirtualBox and click **New**
2. **Name**: Give your VM a name (e.g., "naz")
3. **ISO Image**: Select the downloaded Ubuntu ISO from your Downloads folder
4. **Username & Password**: Set both to "naz" (or your preferred username)
5. **Hostname**: Set to "naz" (or your preferred hostname)
6. **Memory**: Allocate 5000 MB (5GB) - adjust based on your host machine capacity
7. **CPU**: Allocate 5 CPU cores - adjust based on your host machine capacity
8. **Hard Disk**: Allocate 60 GB
9. Click **Create** and wait for installation to complete

### Step 2: Configure Ubuntu User Permissions

#### 2.1 Open Terminal and Switch to Root
```bash
# Open terminal (Ctrl+Alt+T)
# Switch to root user
su root

# Edit sudoers file
nano /etc/sudoers
```

#### 2.2 Add User to Sudoers
In the nano editor, find the line:
```
root    ALL=(ALL:ALL) ALL
```

Add your username below it:
```
naz     ALL=(ALL:ALL) ALL
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

### Step 3: Install Dependencies

#### 3.1 Install Minikube
```bash
# Install curl
sudo apt install curl

# Download and install Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

#### 3.2 Install Docker
```bash
# Install required packages
sudo apt install apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Add Docker repository
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"

# Check Docker availability
apt-cache policy docker-ce

# Install Docker
sudo apt install docker-ce

# Add user to docker group
sudo usermod -aG docker naz

# Restart VM to apply group changes
sudo reboot
```

**After restart, log back in as your user (naz)**

#### 3.3 Install kubectl
```bash
# Download kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Install kubectl
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

#### 3.4 Start Minikube
```bash
# Start Minikube cluster
minikube start --cpus 2 --memory 1900 --driver docker
```

**Explanation**:
- `--cpus 2`: Allocates 2 virtual CPUs
- `--memory 1900`: Allocates 1900 MB RAM
- `--driver docker`: Uses Docker as the driver (faster than VM)

#### 3.5 Install Istio
```bash
# Download Istio 1.24.2
# Go to https://istio.io/latest/docs/setup/getting-started/#download
# Download istio-1.24.2-linux-amd64.tar.gz

# Extract the file (adjust path as needed)
cd ~/Downloads
tar -xzf istio-1.24.2-linux-amd64.tar.gz

# Export Istio to PATH
export PATH=$PATH:/home/naz/Downloads/istio-1.24.2-linux-amd64/istio-1.24.2/bin

# Install Istio
istioctl install --set profile=default
```

**Explanation**:
- `--set profile=default`: Installs standard Istio components (istiod, ingress gateway, sidecar injection)

#### 3.6 Verify Installation
```bash
# Check all pods across namespaces
minikube kubectl -- get pods -A

# You should see Istio pods running in istio-system namespace
```

### Step 4: Configure Bookinfo Microservices

#### 4.1 Enable Istio Sidecar Injection
```bash
# Label default namespace for automatic sidecar injection
kubectl label namespace default istio-injection=enabled
```

**Explanation**: This tells Istio to automatically inject Envoy sidecar proxy into pods deployed in the default namespace.

#### 4.2 Deploy Bookinfo Application
```bash
# Deploy Bookinfo microservices
kubectl apply -f /home/naz/Downloads/istio-1.24.2-linux-amd64/istio-1.24.2/samples/bookinfo/platform/kube/bookinfo.yaml

# Deploy Bookinfo gateway
kubectl apply -f /home/naz/Downloads/istio-1.24.2-linux-amd64/istio-1.24.2/samples/bookinfo/networking/bookinfo-gateway.yaml
```

#### 4.3 Get Access URL
```bash
# Find the invoke point (gateway URL)
export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].nodePort}')
export SECURE_INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')
export INGRESS_HOST=$(kubectl get po -l istio=ingressgateway -n istio-system -o jsonpath='{.items[0].status.hostIP}')
export GATEWAY_URL=$INGRESS_HOST:$INGRESS_PORT

# Display the URLs
echo "$GATEWAY_URL"
echo "http://$GATEWAY_URL/productpage"
```

**Note**: Save the `$GATEWAY_URL` - you'll need it for testing.

### Step 5: Deploy AI-Driven Anomaly Detection System

#### 5.1 Clone Repository
```bash
# Clone the repository
git clone https://github.com/nazrulhuda/AI-Driven-Anamoly-Detector-as-a-service.git

# Navigate to the repository
cd AI-Driven-Anamoly-Detector-as-a-service
```

#### 5.2 Configure Access Logs
```bash
# Apply Envoy access log configuration
kubectl apply -f ml/logs.yaml

# View logs from a specific pod (adjust pod name as needed)
kubectl logs productpage-v1-d49bb79b4-zzth6 -c istio-proxy -n default

# Find your actual pod names
kubectl get pods -A
```

#### 5.3 Deploy Ratings v2 Service

**Important**: Deploy ratings v2 before the DDoS detector to ensure the backup service is available.

1. **Build and Push Docker Image**:
   ```bash
   # Navigate to ratings-v2 folder
   cd ratings-v2/
   
   # Build Docker image
   docker build -t hudabhai/ratings-v2:4 .
   
   # Push to Docker Hub
   docker push hudabhai/ratings-v2:4
   
   # Return to root directory
   cd ..
   ```

2. **Deploy Ratings v2**:
   ```bash
   # Deploy ratings v2 service
   kubectl apply -f ml/ratings-v2.yaml
   
   # Apply Istio routing configuration
   kubectl apply -f ml/ratings-istio.yaml
   ```

#### 5.4 Deploy DDoS Detector

**Important**: Before deploying, update the pod names in the configuration files to match your actual Bookinfo deployment.

1. **Update `git/ddos_detection.py`**:
   ```python
   # Find this section and update with your actual pod names
   POD_SHORT_NAMES = {
       'details-v1-79dfbd6fff-577tm': 'details',  # Update this
       'productpage-v1-d49bb79b4-zzth6': 'product',  # Update this
       'ratings-v1-856f65bcff-xb6kr': 'ratings',  # Update this
       'reviews-v1-848b8749df-6cw47': 'reviews1',  # Update this
       'reviews-v2-5fdf9886c7-m4rjm': 'reviews2',  # Update this
       'reviews-v3-bb6b8ddc7-v5rjh': 'reviews3'   # Update this
   }
   
   # Also update the POD_NAMES list in the main() function
   POD_NAMES = [
       "details-v1-79dfbd6fff-577tm",  # Update this
       "productpage-v1-d49bb79b4-zzth6",  # Update this
       "ratings-v1-856f65bcff-xb6kr",  # Update this
       "reviews-v1-848b8749df-6cw47",  # Update this
       "reviews-v2-5fdf9886c7-m4rjm",  # Update this
       "reviews-v3-bb6b8ddc7-v5rjh"   # Update this
   ]
   ```

2. **Update `ml/ddos-detector-deployment.yaml`**:
   ```yaml
   env:
     - name: POD_NAME
       value: "details-v1-79dfbd6fff-577tm,productpage-v1-d49bb79b4-zzth6,ratings-v1-856f65bcff-xb6kr,reviews-v1-848b8749df-6cw47,reviews-v2-5fdf9886c7-m4rjm,reviews-v3-bb6b8ddc7-v5rjh"
   ```

3. **Build and Push Docker Image**:
   ```bash
   # Navigate to git folder
   cd git/
   
   # Build Docker image
   docker build -t hudabhai/ddos-detector:latest71 .
   
   # Push to Docker Hub
   docker push hudabhai/ddos-detector:latest71
   
   # Return to root directory
   cd ..
   ```

4. **Deploy DDoS Detector**:
   ```bash
   # Apply service account
   kubectl apply -f ml/ddos-detector-serviceaccount.yaml
   
   # Deploy DDoS detector
   kubectl apply -f ml/ddos-detector-deployment.yaml
   
   # Check if it's working
   kubectl logs deployment/ddos-detector
   ```

#### 5.5 Deploy Report Receiver

1. **Build and Push Docker Image**:
   ```bash
   # Navigate to app folder
   cd app/
   
   # Build Docker image
   docker build -t hudabhai/report_receiver:latest2 .
   
   # Push to Docker Hub
   docker push hudabhai/report_receiver:latest2
   
   # Return to root directory
   cd ..
   ```

2. **Deploy Report Receiver**:
   ```bash
   # Deploy report receiver
   kubectl apply -f ml/report-receiver-deployment.yaml
   
   # Apply RBAC configuration
   kubectl apply -f ml/report-receiver-rbac.yaml
   ```

### Step 6: Test DDoS Detection

#### 6.1 Install Traffic Generation Tool
```bash
# Install hey for generating traffic
sudo snap install hey

# Increase file descriptor limit
ulimit -n 2500
```

**Explanation**: `ulimit -n 2500` increases the number of open file descriptors, required for generating high concurrent traffic.

#### 6.2 Generate Test Traffic
```bash
# Generate traffic to trigger DDoS detection
# Replace IP and port with your actual GATEWAY_URL
hey -n 500 -c 10 http://192.168.49.2:32489/ratings/1
```

**Parameters**:
- `-n 500`: Total number of requests
- `-c 10`: Number of concurrent connections
- URL: Use your actual gateway URL from Step 4.3

**Note**: The example shows `-n 500 -c 10`, but your document mentions `-n 1250 -c 2500`. Use the parameters that work best for your testing scenario.

#### 6.3 Monitor System Response
```bash
# Check DDoS detector logs
kubectl logs deployment/ddos-detector

# Check report receiver logs
kubectl logs deployment/report-receiver

# Find report receiver pod name
kubectl get pods

# Access reports (replace pod name with actual name)
kubectl exec -it report-receiver-6c77546688-f8rrz -- /bin/bash

# Inside the pod, check reports
ls -l /reports
cd /reports
cat <filename>  # View specific report
```

## 🔍 How It Works

### 1. Traffic Monitoring
The DDoS detector continuously monitors Istio proxy logs from all configured pods:
- Collects access logs every 60 seconds
- Extracts features like request counts, IP addresses, response times
- Processes data in 20-second time windows

### 2. Anomaly Detection
Using the pre-trained ML model:
- Analyzes traffic patterns for anomalies
- Generates DDoS predictions (0 = normal, 1 = attack)
- Creates LIME explanations for detected anomalies

### 3. Intelligent Response
When anomalies are detected:
- Generates comprehensive CSV reports
- Submits reports to the report receiver service
- Automatically triggers traffic failover from v1 to v2 services
- Scales down problematic v1 deployments

### 4. Traffic Management
The report receiver:
- Receives anomaly reports via HTTP POST
- Analyzes reports for specific service issues
- Patches Istio VirtualService configurations
- Orchestrates Kubernetes deployment scaling

## 📊 Configuration

### Environment Variables

**DDoS Detector**:
- `NAMESPACE`: Kubernetes namespace (default: "default")
- `RECEIVER_URL`: Report receiver service URL

**Report Receiver**:
- `UPLOAD_FOLDER`: Directory for storing reports (default: "/reports")

### Pod Configuration

**Important**: Update these pod names in your configuration files to match your actual Bookinfo deployment:
- `details-v1-79dfbd6fff-577tm`
- `productpage-v1-d49bb79b4-zzth6`
- `ratings-v1-856f65bcff-xb6kr`
- `reviews-v1-848b8749df-6cw47`
- `reviews-v2-5fdf9886c7-m4rjm`
- `reviews-v3-bb6b8ddc7-v5rjh`

### Service Deployment Order

**Critical**: Deploy services in this order to ensure proper functionality:
1. **Bookinfo microservices** (from Istio samples)
2. **Ratings v2 service** (backup service)
3. **DDoS detector** (monitoring service)
4. **Report receiver** (traffic management)

## 🧪 Testing Scenarios

### 1. Normal Operation
```bash
# Generate normal traffic
curl http://$GATEWAY_URL/productpage
```

### 2. DDoS Simulation
```bash
# Generate high traffic to trigger detection
hey -n 1000 -c 100 http://$GATEWAY_URL/ratings/1

# Or use higher concurrency for more aggressive testing
hey -n 1250 -c 2500 http://$GATEWAY_URL/ratings/1
```

### 3. Failover Verification
```bash
# Check traffic routing
kubectl get virtualservice -A

# Verify service scaling
kubectl get deployment -A

# Check ratings v2 service status
kubectl get pods -l app=ratings
```

## 📈 Monitoring and Logging

### Log Levels
- **INFO**: Normal operation and status updates
- **WARNING**: Anomaly detection and traffic changes
- **ERROR**: Service failures and exceptions

### Key Metrics
- Request counts per time window
- Unique IP addresses
- Response times and error rates
- DDoS detection accuracy
- Traffic failover success rate

## 🔒 Security Considerations

- Service accounts with minimal required permissions
- RBAC controls for Kubernetes API access
- Istio sidecar injection control
- Secure communication between services
- Input validation for uploaded reports

## 🚨 Troubleshooting

### Common Issues

1. **DDoS detector not starting**:
   - Check service account permissions
   - Verify model file exists
   - Check Kubernetes API connectivity
   - Verify pod names are correct

2. **Report receiver not receiving reports**:
   - Verify service is running
   - Check network policies
   - Verify endpoint configuration

3. **Traffic failover not working**:
   - Check Istio VirtualService configuration
   - Verify destination rules
   - Check deployment scaling
   - Ensure ratings v2 service is deployed

4. **Ratings v2 service not accessible**:
   - Verify service deployment
   - Check Istio routing configuration
   - Verify service endpoints

### Debug Commands

```bash
# Check service connectivity
kubectl exec -it ddos-detector-pod -- curl report-receiver:8000/health

# Verify Istio configuration
istioctl analyze

# Check access logs
kubectl logs -l app=ratings -c istio-proxy

# Check pod status
kubectl get pods -A

# Check services
kubectl get svc -A

# Check ratings v2 specifically
kubectl get pods -l app=ratings
kubectl logs -l app=ratings
```

## 🔄 Maintenance

### Regular Tasks
- Monitor ML model performance
- Update training data as needed
- Review and adjust detection thresholds
- Backup anomaly reports
- Update service images

### Scaling
- Adjust DDoS detector replicas based on cluster size
- Scale report receiver for high-volume scenarios
- Monitor resource usage and adjust limits

## 📚 Additional Resources

- [Istio Documentation](https://istio.io/docs/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [LIME Documentation](https://github.com/marcotcr/lime)
- [Envoy Access Logs](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Minikube Documentation](https://minikube.sigs.k8s.io/docs/)
- [Docker Documentation](https://docs.docker.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs and error messages
3. Open an issue in the repository
4. Contact the development team

---

**Note**: This system is designed for production use but should be thoroughly tested in your specific environment before deployment. Always review security configurations and adjust resource limits based on your cluster capacity.

## 🎯 Quick Start Summary

1. **Setup Ubuntu VM** in VirtualBox (5GB RAM, 5 CPU, 60GB disk)
2. **Install dependencies**: Minikube, Docker, kubectl, Istio
3. **Deploy Bookinfo** microservices
4. **Deploy Ratings v2** service (backup service)
5. **Update pod names** in configuration files
6. **Deploy AI system**: DDoS detector + report receiver
7. **Test with traffic**: Use `hey` tool to generate load
8. **Monitor logs** to see anomaly detection in action

## 🚨 Critical Deployment Order

**IMPORTANT**: Follow this exact order to ensure system functionality:
1. **Bookinfo** (Istio sample application)
2. **Ratings v2** (backup service)
3. **DDoS Detector** (monitoring)
4. **Report Receiver** (traffic management)

**Remember**: Always update the pod names in your configuration files to match your actual Bookinfo deployment!
