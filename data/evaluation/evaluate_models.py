import os
import sys
import pandas as pd
import numpy as np
import requests
import time
import logging
from typing import Dict, List, Any, Optional
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

logger = logging.getLogger('prompt_evaluation')

API_URL = os.getenv("API_URL", "http://localhost:8000")

PROVIDERS = ["openai"]
MODELS = ["gpt-4.1-nano", "gpt-4.1-mini", "gpt-3.5-turbo", "gpt-4"]
PROMPT_VERSION = "v3"
DATASET_PATH = os.path.join("data", "datasets", "sample-prompts.csv")

OUTPUT_DIR = os.path.join("data", "evaluation", "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def classify_prompt(text: str, model: str, provider: str, prompt_version: str = PROMPT_VERSION) -> Optional[Dict[str, Any]]:
    """
    Send a prompt to the API for classification
    
    Args:
        text: The prompt text to classify
        model: The model to use
        provider: The LLM provider to use
        prompt_version: The prompt version to use
        
    Returns:
        dict: Classification result or None if error
    """ 
    try: 
        response = requests.post(
            f"{API_URL}/api/v1/classify",
            json={
                "text": text,
                "provider": provider,
                "prompt_version": prompt_version,
                "model_version": model
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error classifying prompt: {e}")
        return None

def plot_confusion_matrix(y_true: List[str], y_pred: List[str], model_name: str, provider: str) -> None:
    """
    Plot confusion matrix for the results
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        model_name: Name of the model for the title
        provider: Name of the LLM provider
    """
    # Create confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=["Benign", "Malicious"])
    
    # Plot
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', xticklabels=["Benign", "Malicious"], 
                yticklabels=["Benign", "Malicious"], cmap="Blues")
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title(f"Confusion Matrix - {provider}/{model_name} with {PROMPT_VERSION}")
    
    # Save plot
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"confusion_matrix_{provider}_{model_name}_{PROMPT_VERSION}.png"))
    plt.close()

def evaluate_model(df: pd.DataFrame, model: str, provider: str) -> Dict[str, Any]:
    """
    Evaluate a model on all prompts in the dataframe
    
    Args:
        df: DataFrame with prompts and labels
        model: Model name to evaluate
        provider: LLM provider to use
        
    Returns:
        dict: Evaluation results
    """
    logger.info(f"Evaluating {provider}/{model} with prompt version: {PROMPT_VERSION}")
    
    results: Dict[str, List[Any]] = {
        "prompt": [],
        "true_label": [],
        "predicted_label": [],
        "confidence": [],
        "reasoning": [],
        "severity": [],
    }
    
    # Process each prompt
    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Testing {provider}/{model}"):
        prompt = row["Prompt"]
        true_label = row["Label"]
        
        results["prompt"].append(prompt)
        results["true_label"].append(true_label)
        
        # Classify with API
        response = classify_prompt(prompt, model, provider)
        
        # Add API response to results
        if response and "classification" in response:
            predicted_label = response["classification"].capitalize()  # Ensure consistent capitalization
            results["predicted_label"].append(predicted_label)
            results["confidence"].append(response.get("confidence", 0))
            results["reasoning"].append(response.get("reasoning", ""))
            results["severity"].append(response.get("severity", ""))

        else:
            results["predicted_label"].append("Unknown")
            results["confidence"].append(0)
            results["reasoning"].append("")
            results["severity"].append("")
        
        # Small delay to avoid overwhelming the API
        time.sleep(0.5)
    
    results_df = pd.DataFrame(results)
    
    # Filter out any "Unknown" predictions for metrics calculation
    metrics_df = results_df[results_df["predicted_label"] != "Unknown"]
    
    # Calculate metrics only if we have valid predictions
    if len(metrics_df) > 0:
        
        report = classification_report(
            metrics_df["true_label"], 
            metrics_df["predicted_label"],
            output_dict=True
        )
        
        plot_confusion_matrix(
            metrics_df["true_label"].tolist(), 
            metrics_df["predicted_label"].tolist(),
            model,
            provider
        )
        
        report_df = pd.DataFrame(report).transpose()
        
        logger.info(f"Classification Report for {provider}/{model} with {PROMPT_VERSION}:")
        logger.info("\n" + report_df.to_string())
        report_df.to_csv(os.path.join(OUTPUT_DIR, f"classification_report_{provider}_{model}_{PROMPT_VERSION}.csv"))
        
        result_dict: Dict[str, Any] = {
            "provider": provider,
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "accuracy": report["accuracy"],
            "benign_precision": report.get("Benign", {}).get("precision", 0),
            "benign_recall": report.get("Benign", {}).get("recall", 0),
            "benign_f1": report.get("Benign", {}).get("f1-score", 0),
            "malicious_precision": report.get("Malicious", {}).get("precision", 0),
            "malicious_recall": report.get("Malicious", {}).get("recall", 0),
            "malicious_f1": report.get("Malicious", {}).get("f1-score", 0),
            "weighted_f1": report.get("weighted avg", {}).get("f1-score", 0),
            "details": results_df
        }
        return result_dict
    else:
        logger.warning(f"No valid predictions for {provider}/{model}")
        result_dict: Dict[str, Any] = {
            "provider": provider,
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "accuracy": 0,
            "details": results_df
        }
        return result_dict

def plot_model_comparison(all_results: List[Dict[str, Any]]) -> None:
    """
    Plot comparison of model performance
    
    Args:
        all_results: List of result dictionaries for each model
    """
    # Create labels that combine provider and model
    labels = [f"{r['provider']}/{r['model']}" for r in all_results]
    accuracy = [r["accuracy"] for r in all_results]
    malicious_f1 = [r.get("malicious_f1", 0) for r in all_results]
    benign_f1 = [r.get("benign_f1", 0) for r in all_results]
    
    # Set up the figure
    plt.figure(figsize=(14, 8))
    
    # Create bar positions
    bar_width = 0.25
    r1 = np.arange(len(labels))
    r2 = [x + bar_width for x in r1]
    r3 = [x + bar_width for x in r2]
    
    # Create bars
    plt.bar(r1, accuracy, width=bar_width, label='Accuracy', color='blue')
    plt.bar(r2, malicious_f1, width=bar_width, label='Malicious F1', color='red')
    plt.bar(r3, benign_f1, width=bar_width, label='Benign F1', color='green')
    
    # Add labels and title
    plt.xlabel('Models')
    plt.ylabel('Scores')
    plt.title(f'Model Performance Comparison with {PROMPT_VERSION}')
    plt.xticks([r + bar_width for r in range(len(labels))], labels, rotation=45)
    plt.ylim(0, 1.1)  # Scores are between 0 and 1
    
    # Add a legend
    plt.legend()
    
    # Add value labels on bars
    for i, v in enumerate(accuracy):
        plt.text(i - 0.1, v + 0.02, f'{v:.2f}', color='blue', fontweight='bold')
    for i, v in enumerate(malicious_f1):
        plt.text(i + 0.15, v + 0.02, f'{v:.2f}', color='red', fontweight='bold')
    for i, v in enumerate(benign_f1):
        plt.text(i + 0.4, v + 0.02, f'{v:.2f}', color='green', fontweight='bold')
    
    # Save the figure
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'model_comparison_{PROMPT_VERSION}.png'))
    plt.close()
    
def main() -> None:
    """Main function to run the evaluation process"""
    logger.info(f"Starting evaluation with prompt version {PROMPT_VERSION}")
    
    # Read prompts CSV
    try:
        df = pd.read_csv(DATASET_PATH)
        logger.info(f"Loaded {len(df)} prompts from {DATASET_PATH}")
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        sys.exit(1)
    
    # Evaluate each model for each provider
    all_results: List[Dict[str, Any]] = []
    for provider in PROVIDERS:
        for model in MODELS:
            result = evaluate_model(df, model, provider)
            all_results.append(result)
    
    plot_model_comparison(all_results)
    
    # Save summary results
    summary_df = pd.DataFrame([
        {
            "provider": r["provider"],
            "model": r["model"],
            "prompt_version": r["prompt_version"],
            "accuracy": r["accuracy"],
            "benign_precision": r.get("benign_precision", 0),
            "benign_recall": r.get("benign_recall", 0),
            "benign_f1": r.get("benign_f1", 0),
            "malicious_precision": r.get("malicious_precision", 0),
            "malicious_recall": r.get("malicious_recall", 0),
            "malicious_f1": r.get("malicious_f1", 0),
            "weighted_f1": r.get("weighted_f1", 0),
        } for r in all_results
    ])
    
    summary_df.to_csv(os.path.join(OUTPUT_DIR, f"summary_results_{PROMPT_VERSION}.csv"), index=False)
    
    logger.info(f"Evaluation complete! Results saved in: {OUTPUT_DIR}")
    logger.info(f"Summary of results with {PROMPT_VERSION}:")
    logger.info("\n" + summary_df.to_string())

if __name__ == "__main__":
    main()
