# report_receiver.py
import os, re, logging, pandas as pd, subprocess
from flask import Flask, request

from kubernetes import client, config
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
UPLOAD_FOLDER = '/reports'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------
# K8s helpers
# ---------------------------------------------------------------------
def k8s_config():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

def switch_ratings_traffic_to_v2(namespace="default"):
    """
    Merge‑patch VirtualService ratings-route so that
    weight v1 = 0  and  weight v2 = 100.
    Then scale ratings‑v1 to 0 replicas.
    """
    # Merge‑patch sets only the fields we supply
    patch_body = {
        "spec": {
            "http": [{
                "route": [
                    { "destination": { "host": "ratings", "subset": "v1" }, "weight": 0   },
                    { "destination": { "host": "ratings", "subset": "v2" }, "weight": 100 }
                ]
            }]
        }
    }

    # load cluster credentials
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    custom = client.CustomObjectsApi()
    custom.patch_namespaced_custom_object(
        group="networking.istio.io",
        version="v1beta1",
        namespace=namespace,
        plural="virtualservices",
        name="ratings-route",
        body=patch_body          # <- no extra args, defaults to merge‑patch
    )
    logging.warning("✅  VirtualService ratings-route patched (100 % → v2)")

    apps = client.AppsV1Api()
    apps.patch_namespaced_deployment_scale(
        name="ratings-v1",
        namespace=namespace,
        body={"spec": {"replicas": 0}}
    )
    logging.warning("✅  Deployment ratings-v1 scaled to 0 replicas")
# ---------------------------------------------------------------------
# Flask route
# ---------------------------------------------------------------------
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return "missing file field", 400
    f = request.files['file']
    if f.filename == '':
        return "empty filename", 400

    save_path = os.path.join(UPLOAD_FOLDER, f.filename)
    f.save(save_path)
    logging.info(f"📄  Saved report → {save_path}")

    try:
        df = pd.read_csv(save_path)
        # look for any pod_name that starts with 'ratings-v1'
        if df['pod_name'].str.contains(r'^ratings-v1').any():
            logging.warning("⚠️  Report flags ratings‑v1 → initiating traffic fail‑over")
            switch_ratings_traffic_to_v2()
    except Exception as e:
        logging.exception(f"Could not evaluate report {f.filename}: {e}")

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
