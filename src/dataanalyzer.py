from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -----Cnvert text to signal---------
def build_tfidf_signals(contents, max_features=1000):
    vectorizer = TfidfVectorizer(max_features=max_features, ngram_range=(1,2))
    X = vectorizer.fit_transform(contents)
    doc_signal = np.asarray(X.mean(axis=1)).ravel()
    return {
        "vectorizer": vectorizer,
        "X": X,
        "doc_signal": doc_signal
    }

def aggregate_signals(df: pd.DataFrame, doc_signal_col='signal'):
    groups = {}
    for tag, g in df.explode('hashtags').dropna(subset=['hashtags']).groupby('hashtags'):
        vals = g[doc_signal_col].values.astype(float)
        if len(vals)==0:
            continue
        mean = vals.mean()
        se = vals.std(ddof=1)/np.sqrt(len(vals)) if len(vals)>1 else 0.0
        groups[tag] = {
            "count": len(vals),
            "mean_signal": float(mean),
            "ci_lower": float(mean - 1.96*se),
            "ci_upper": float(mean + 1.96*se)
        }
    return groups

def plot_signals(df):
    plt.figure(figsize=(10,5))
    plt.hist(df['signal'], bins=30, color='skyblue', edgecolor='black')
    plt.title("Distribution of Tweet Signals")
    plt.xlabel("Signal Value")
    plt.ylabel("Frequency")
    plt.show()