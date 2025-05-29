import subprocess
import pandas as pd
import joblib
import os
import sys
import json
import time
import logging
from kubernetes import client, config
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO)

# Additional imports for HTTP posting and LIME
import requests
from lime.lime_tabular import LimeTabularExplainer

##############################################################################
# Pod name mapping with the new pod names
##############################################################################
POD_SHORT_NAMES = {
    'details-v1-54ffdd5947-vvm48': 'details',
    'productpage-v1-d49bb79b4-ds6gt': 'product',
    'ratings-v1-856f65bcff-xb6kr': 'ratings',
    'reviews-v1-848b8749df-6cw47': 'reviews1',
    'reviews-v2-5fdf9886c7-m4rjm': 'reviews2',
    'reviews-v3-bb6b8ddc7-v5rjh': 'reviews3'
}

##############################################################################
# 1) Collect Logs
##############################################################################
def collect_logs(namespace, pod_name, log_file):
    logging.info(f"[{pod_name}] Collecting logs from pod {pod_name} in namespace {namespace}")
    try:
        config.load_incluster_config()
        logging.debug("In-cluster Kubernetes config loaded")
    except config.ConfigException:
        logging.info("In-cluster config not found; loading local kube config")
        config.load_kube_config()

    v1 = client.CoreV1Api()
    open(log_file, 'w').close()  # empty the file

    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container='istio-proxy',
            since_seconds=60,  # last 60 seconds
            timestamps=True
        )
        logging.debug(f"[{pod_name}] Raw logs:\n{logs[:500]}")
        with open(log_file, 'a') as f:
            f.write(logs)
        logging.info(f"[{pod_name}] Collected logs from pod {pod_name}")
    except client.exceptions.ApiException as e:
        logging.exception(f"[{pod_name}] APIException collecting logs from {pod_name}: {e}")
    except Exception as e:
        logging.exception(f"[{pod_name}] Exception collecting logs from {pod_name}: {e}")

##############################################################################
# 2) Extract Features
##############################################################################
def extract_features(log_file, pod_name):
    if not os.path.exists(log_file):
        logging.warning(f"[{pod_name}] Log file {log_file} does not exist.")
        return None

    with open(log_file, 'r') as f:
        log_lines = f.readlines()

    log_count = len(log_lines)
    logging.info(f"[{pod_name}] Number of logs collected: {log_count}")

    threshold = 10
    if log_count < threshold:
        logging.info(f"[{pod_name}] Log count ({log_count}) below threshold ({threshold}). Skipping.")
        return None

    short_name = POD_SHORT_NAMES.get(pod_name, pod_name.split('-')[0])

    parsed_logs = []
    for line in log_lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(' ', 1)
        if len(parts) < 2:
            logging.warning(f"[{pod_name}] Skipping malformed log line: '{line}'")
            continue

        timestamp_str, json_str = parts
        if not json_str.strip().startswith('{'):
            logging.debug(f"[{pod_name}] Skipping non-JSON line: '{line}'")
            continue

        try:
            log_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logging.exception(f"[{pod_name}] JSON error on line: {line}")
            continue
        except Exception as e:
            logging.exception(f"[{pod_name}] Unexpected error parsing line: {e}")
            continue

        log_data['timestamp'] = timestamp_str
        log_data['pod_shortname'] = short_name
        parsed_logs.append(log_data)

    if not parsed_logs:
        logging.info(f"[{pod_name}] No logs were parsed successfully.")
        return None

    logs_df = pd.DataFrame(parsed_logs)
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')
    logs_df.set_index('timestamp', inplace=True)

    time_window = '20s'
    grouped = logs_df.resample(time_window)
    feature_vectors = []

    for time_period, group in grouped:
        if group.empty:
            continue

        total_requests = len(group)
        unique_ips = group['client_ip'].nunique() if 'client_ip' in group else 0
        requests_per_ip = group.groupby('client_ip').size() if 'client_ip' in group else pd.Series([])
        max_requests_per_ip = requests_per_ip.max() if not requests_per_ip.empty else 0
        avg_requests_per_ip = requests_per_ip.mean() if not requests_per_ip.empty else 0
        error_rate = 0.0
        if total_requests > 0 and 'response_code' in group:
            error_rate = (group[group['response_code'] >= 400].shape[0] / total_requests) * 100
        avg_response_time = group['duration'].mean() if 'duration' in group else 0

        feature_vector = {
            'timestamp': time_period,
            'total_requests': total_requests,
            'unique_ips': unique_ips,
            'max_requests_per_ip': max_requests_per_ip,
            'avg_requests_per_ip': avg_requests_per_ip,
            'error_rate': error_rate,
            'avg_response_time': avg_response_time,
            'pod_shortname': short_name
        }
        feature_vectors.append(feature_vector)

    if feature_vectors:
        features_df = pd.DataFrame(feature_vectors)
        return features_df
    else:
        logging.info(f"[{pod_name}] No feature vectors after grouping.")
        return None

##############################################################################
# 3) Predict (No immediate LIME)
##############################################################################
def predict_ddos(features_df, model_path, pod_name):
    """
    Return (features_df_with_pred, ddos_rows_for_lime).
    ddos_rows_for_lime: numeric data aligned to the model for rows predicted DDoS=1.
    We'll run LIME on them later, after collecting all pods' data.
    """
    ddos_rows_for_lime = pd.DataFrame()
    try:
        model = joblib.load(model_path)
        inference_df = features_df.copy()

        # Remove 'timestamp' from model’s input
        if 'timestamp' in inference_df.columns:
            inference_df.drop(columns=['timestamp'], inplace=True)

        if 'pod_shortname' in inference_df.columns:
            logging.info(f"[{pod_name}] Encoding 'pod_shortname' for inference...")
            inference_df = pd.get_dummies(inference_df, columns=['pod_shortname'], drop_first=True)

        needed_cols = getattr(model, 'feature_names_in_', None)
        if needed_cols is not None:
            for col in needed_cols:
                if col not in inference_df.columns:
                    inference_df[col] = 0
            extra_cols = set(inference_df.columns) - set(needed_cols)
            if extra_cols:
                logging.info(f"[{pod_name}] Dropping extra columns not in model: {extra_cols}")
                inference_df.drop(columns=list(extra_cols), inplace=True)

        predictions = model.predict(inference_df)
        features_df['prediction'] = predictions

        ddos_mask = (features_df['prediction'] == 1)
        if ddos_mask.any():
            ddos_rows_for_lime = inference_df[ddos_mask].copy()
            ddos_rows_for_lime['original_index'] = ddos_rows_for_lime.index
            ddos_rows_for_lime['timestamp'] = features_df.loc[ddos_mask, 'timestamp'].astype(str)
            ddos_rows_for_lime['pod_name'] = pod_name

        return features_df, ddos_rows_for_lime

    except Exception as e:
        logging.exception(f"[{pod_name}] Error during prediction: {e}")
        return features_df, ddos_rows_for_lime

##############################################################################
# 4) Single LIME Explanation, then POST the final CSV to a Report Receiver
##############################################################################
def explain_all_ddos_rows(ddos_rows_list, model_path, receiver_url):
    """
    - ddos_rows_list: list of DataFrames from each pod with numeric data 
      +timestamp +pod_name +original_index for rows predicted DDoS=1.
    - We combine them, run LIME in a single pass, write one CSV, 
      then POST it to 'receiver_url'.
    """
    if not ddos_rows_list:
        logging.info("No DDoS rows to explain in this cycle. Done.")
        return

    combined_ddos_df = pd.concat(ddos_rows_list, axis=0).reset_index(drop=True)

    # We'll keep these meta columns separate
    meta_cols = ['timestamp','pod_name','original_index']
    numeric_cols = [c for c in combined_ddos_df.columns if c not in meta_cols]

    # Load the model
    model = joblib.load(model_path)

    # Load reference data for LIME
    train_sample = pd.read_csv('train_sample.csv')
    if 'label' in train_sample.columns:
        train_sample.drop(columns=['label'], inplace=True)
    if 'timestamp' in train_sample.columns:
        train_sample.drop(columns=['timestamp'], inplace=True)
    if 'pod_shortname' in train_sample.columns:
        train_sample = pd.get_dummies(train_sample, columns=['pod_shortname'], drop_first=True)

    needed_cols = getattr(model, 'feature_names_in_', None)
    if needed_cols is not None:
        for col in needed_cols:
            if col not in train_sample.columns:
                train_sample[col] = 0
        extra_cols = set(train_sample.columns) - set(needed_cols)
        if extra_cols:
            train_sample.drop(columns=list(extra_cols), inplace=True)

    train_sample_values = train_sample.values
    class_names = ['noDDOS','DDOS']
    explainer = LimeTabularExplainer(
        training_data=train_sample_values,
        feature_names=train_sample.columns.tolist(),
        class_names=class_names,
        discretize_continuous=False
    )

    # Align combined_ddos_df to model columns
    numeric_df = combined_ddos_df[numeric_cols].copy()

    for col in needed_cols:
        if col not in numeric_df.columns:
            numeric_df[col] = 0
    extra_cols_2 = set(numeric_df.columns) - set(needed_cols)
    if extra_cols_2:
        numeric_df.drop(columns=list(extra_cols_2), inplace=True)

    all_explanations = []

    for i in numeric_df.index:
        row_values = numeric_df.loc[i].values
        try:
            explanation = explainer.explain_instance(
                data_row=row_values,
                predict_fn=model.predict_proba,
                num_features=6
            )
            explanation_list = explanation.as_list()
            exp_df = pd.DataFrame(explanation_list, columns=['feature','contribution'])

            exp_df['timestamp'] = combined_ddos_df.loc[i, 'timestamp']
            exp_df['pod_name'] = combined_ddos_df.loc[i, 'pod_name']
            exp_df['original_index'] = combined_ddos_df.loc[i, 'original_index']
            exp_df['row_id'] = i

            all_explanations.append(exp_df)
        except Exception as e:
            logging.exception(f"Error explaining row {i}: {e}")

    if all_explanations:
        final_expl = pd.concat(all_explanations, axis=0)
        out_file = f"/tmp/lime_explanations_cycle_{int(time.time())}.csv"
        final_expl.to_csv(out_file, index=False)
        logging.warning(f"LIME explanations for entire cycle saved to {out_file}")

        # Now POST this file to the external microservice
        post_report_to_receiver(out_file, receiver_url)

    else:
        logging.info("No DDoS rows were explained (all_explanations is empty).")

##############################################################################
# 5) Post the CSV to the 'report receiver' microservice
##############################################################################
def post_report_to_receiver(file_path, receiver_url):
    """
    file_path: path to CSV in local container
    receiver_url: e.g. "http://report-receiver.default.svc.cluster.local:8000/upload"
    """
    try:
        if not os.path.exists(file_path):
            logging.warning(f"Report file not found: {file_path}")
            return
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            resp = requests.post(receiver_url, files=files)
        if resp.status_code == 200:
            logging.info(f"Successfully posted {file_path} to {receiver_url}")
        else:
            logging.warning(f"Failed posting {file_path} (status {resp.status_code}): {resp.text}")
    except Exception as e:
        logging.exception(f"Error posting report to {receiver_url}: {e}")

##############################################################################
# 6) Main loop
##############################################################################
def main():
    NAMESPACE = os.getenv('NAMESPACE', 'default')
    
    # Original pod list with fallback for ratings-v1
    POD_NAMES = [
        'details-v1-54ffdd5947-vvm48',
        'productpage-v1-d49bb79b4-ds6gt',
        'ratings-v1-856f65bcff-xb6kr',
        'reviews-v1-848b8749df-6cw47',
        'reviews-v2-5fdf9886c7-m4rjm',
        'reviews-v3-bb6b8ddc7-v5rjh'
    ]
    
    # Define fallback mapping
    fallback_pods = {
        'ratings-v1-856f65bcff-xb6kr': 'ratings-v2-569478494c-f8nt6'
    }

    MODEL_PATH = 'ddos_detection_model.pkl'
    RECEIVER_URL = os.getenv('RECEIVER_URL', 'http://report-receiver.default.svc.cluster.local:8000/upload')

    while True:
        try:
            global_ddos_rows = []

            for pod_name in POD_NAMES:
                try:
                    LOG_FILE = f'/tmp/access_logs_{pod_name}.txt'
                    logging.info(f"[{pod_name}] Starting DDoS detection cycle")

                    # Try collecting logs
                    collect_logs(NAMESPACE, pod_name, LOG_FILE)
                except client.exceptions.ApiException as e:
                    # If PodNotFound and fallback exists
                    if e.status == 404 and pod_name in fallback_pods:
                        fallback = fallback_pods[pod_name]
                        logging.warning(f"[{pod_name}] not found. Falling back to {fallback}")
                        pod_name = fallback
                        LOG_FILE = f'/tmp/access_logs_{pod_name}.txt'
                        collect_logs(NAMESPACE, pod_name, LOG_FILE)
                    else:
                        logging.error(f"Skipping pod {pod_name} due to error: {e}")
                        continue

                if os.path.exists(LOG_FILE):
                    size_bytes = os.path.getsize(LOG_FILE)
                    logging.info(f"[{pod_name}] Log file size: {size_bytes} bytes")
                else:
                    logging.warning(f"[{pod_name}] No log file found, skipping.")
                    continue

                features_df = extract_features(LOG_FILE, pod_name)
                if features_df is not None and not features_df.empty:
                    logging.info(f"[{pod_name}] Extracted features: {features_df.shape[0]} records")

                    results_df, ddos_rows_for_model = predict_ddos(features_df, MODEL_PATH, pod_name)
                    if not ddos_rows_for_model.empty:
                        global_ddos_rows.append(ddos_rows_for_model)

                    if 'prediction' in results_df.columns:
                        ddos_detected = results_df[results_df['prediction'] == 1]
                        if not ddos_detected.empty:
                            logging.warning(f"[{pod_name}] DDoS attack detected:")
                            logging.warning(ddos_detected[['timestamp','total_requests','prediction']].to_string(index=False))
                        else:
                            logging.info(f"[{pod_name}] No DDoS attack detected.")
                    else:
                        logging.warning(f"[{pod_name}] 'prediction' column missing, skipping.")

                logging.info(f"[{pod_name}] DDoS detection cycle completed\n")

            explain_all_ddos_rows(global_ddos_rows, MODEL_PATH, RECEIVER_URL)

        except Exception as e:
            logging.exception(f"Main loop error: {e}")

        time.sleep(60)

if __name__ == '__main__':
    main()

