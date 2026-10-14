import hashlib
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

_CLIENT = None
_CLASSIFICATION_CACHE: dict[tuple[str, str], dict] = {}
_TAXONOMY_CACHE: dict[str, list[dict]] = {}
_GEMINI_FAILURE_LOGGED = False
_GEMINI_CALL_COUNT = 0
_MAX_GEMINI_CALLS = int(os.getenv("MAX_GEMINI_CLASSIFICATIONS", "12"))
GROUP_ANCHORS = {
    "regression": {"regression", "linear", "logistic", "residual", "glm", "odds", "likelihood", "poisson"},
    "classification": {"svm", "support", "vector", "classification", "kernel", "ensemble", "bagging", "boosting", "forest"},
    "decision": {"decision", "tree", "entropy", "forest", "bagging", "boosting", "xgboost", "cart", "id4", "c4", "c5"},
    "clustering": {"cluster", "clustering", "kmeans", "hierarchical", "dendrogram", "agglomerative", "divisive", "dbscan", "unsupervised"},
}
GENERIC_ANCHOR_STOPWORDS = {
    "data", "task", "learn", "model", "network", "neural", "algorithm", "architectur",
    "application", "applicat", "method", "technique", "pattern", "introduct", "component",
    "process", "system", "issue", "concept", "analysis", "classif", "predict", "design",
    "limitat", "advantage",
}


def classify_question(question_text: str, syllabus: str) -> dict:
    """Classify a question to a syllabus topic and subtopic."""
    normalized_question = _normalize_text(question_text)
    syllabus_key = hashlib.md5(syllabus.encode("utf-8")).hexdigest()
    cache_key = (normalized_question, syllabus_key)
    if cache_key in _CLASSIFICATION_CACHE:
        return _CLASSIFICATION_CACHE[cache_key]

    entries = _get_taxonomy(syllabus, syllabus_key)
    if not entries:
        result = {
            "topic": "Unclassified",
            "subtopic": "Unclassified",
            "confidence": "low",
            "route": "review",
            "used_gemini": False,
        }
        _CLASSIFICATION_CACHE[cache_key] = result
        return result

    local_analysis = _analyze_local_classification(question_text, entries)
    local_result = local_analysis["result"]

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        _CLASSIFICATION_CACHE[cache_key] = local_result
        return local_result

    if _should_use_local_result(local_analysis):
        _CLASSIFICATION_CACHE[cache_key] = local_result
        return local_result

    gemini_result = _classify_with_gemini(question_text, syllabus, api_key, entries)
    final_result = gemini_result or local_result
    _CLASSIFICATION_CACHE[cache_key] = final_result
    return final_result


def _should_use_local_result(local_analysis: dict) -> bool:
    if local_analysis["best_score"] == 0:
        return True

    if local_analysis["result"]["topic"] == "Off Topic":
        return local_analysis["best_score"] <= 1

    if local_analysis["best_score"] >= 7 and local_analysis["score_gap"] >= 2:
        return True

    if local_analysis["keyword_hits"] >= 3 and local_analysis["score_gap"] >= 1:
        return True

    return False


def _classify_with_gemini(question_text: str, syllabus: str, api_key: str, entries: list[dict]) -> dict | None:
    global _CLIENT
    global _GEMINI_FAILURE_LOGGED
    global _GEMINI_CALL_COUNT

    try:
        if _GEMINI_CALL_COUNT >= _MAX_GEMINI_CALLS:
            return None

        if _CLIENT is None:
            _CLIENT = genai.Client(api_key=api_key)

        prompt = f"""
        You are an expert exam question classifier mapping questions to a syllabus.

        Syllabus Topics and Subtopics:
        ```
        {syllabus}
        ```

        Question: {question_text}

        Analyze the question and classify it strictly according to the provided syllabus.
        Return a valid JSON response with exactly two keys: 'topic' and 'subtopic'.
        Select the closest topic and subtopic from the syllabus provided.
        If the question is not part of the syllabus, return topic='Off Topic' and subtopic='Off Topic'.
        """

        response = _CLIENT.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        _GEMINI_CALL_COUNT += 1
        data = json.loads(response.text)
        topic = data.get("topic", "Unclassified").strip()
        subtopic = data.get("subtopic", "Unclassified").strip()
        return _normalize_gemini_result(topic, subtopic, entries)
    except Exception as e:
        if not _GEMINI_FAILURE_LOGGED:
            print(f"Gemini classification failed, falling back to local classification: {e}")
            _GEMINI_FAILURE_LOGGED = True
        return None


def _analyze_local_classification(question_text: str, entries: list[dict]) -> dict:
    normalized_question = _normalize_text(question_text)
    question_tokens = _tokenize(question_text)
    token_count = len(question_tokens)
    best_entry = None
    best_score = 0
    second_best = 0
    best_keyword_hits = 0
    best_alias_hits = 0
    best_anchor_hits = 0
    group_scores: dict[str, int] = {}

    for entry in entries:
        token_overlap = len(question_tokens & entry["tokens"])
        keyword_hits = sum(3 for keyword in entry["keywords"] if keyword and keyword in normalized_question)
        alias_hits = sum(2 for alias in entry["aliases"] if alias and alias in normalized_question)
        anchor_hits = len(question_tokens & entry["anchors"])
        score = token_overlap + keyword_hits + alias_hits + (anchor_hits * 3)
        if score > 0:
            group_scores[entry["group"]] = max(group_scores.get(entry["group"], 0), score)
        if score > best_score:
            second_best = best_score
            best_score = score
            best_entry = entry
            best_keyword_hits = keyword_hits
            best_alias_hits = alias_hits
            best_anchor_hits = anchor_hits
        elif score > second_best:
            second_best = score

    ranked_groups = sorted(group_scores.values(), reverse=True)
    best_group_score = ranked_groups[0] if ranked_groups else 0
    second_group_score = ranked_groups[1] if len(ranked_groups) > 1 else 0
    cross_topic_mixed = second_group_score >= max(3, best_group_score - 1) and token_count > 12

    if (
        not best_entry
        or best_anchor_hits == 0
        or best_score < 3
        or (token_count > 30 and best_score < 6)
        or _fails_context_guard(normalized_question, best_entry)
    ):
        result = {
            "topic": "Needs Review",
            "subtopic": "Off-topic or mixed question",
            "confidence": "low",
            "route": "review",
            "used_gemini": False,
        }
    else:
        confidence = "high" if best_score >= 7 and (best_score - second_best) >= 2 else "medium"
        strong_medium_match = best_anchor_hits >= 2 and (best_keyword_hits + best_alias_hits) >= 2 and best_score >= 6
        generic_main_match = best_entry.get("generic", False) and best_score >= 2 and not cross_topic_mixed
        nearest_topic_match = best_anchor_hits >= 1 and best_score >= 4 and not cross_topic_mixed
        route = "main" if not cross_topic_mixed and (confidence == "high" or strong_medium_match or generic_main_match or nearest_topic_match) else "review"
        result = {
            "topic": best_entry["topic"],
            "subtopic": best_entry["subtopic"],
            "confidence": confidence,
            "route": route,
            "used_gemini": False,
        }

    return {
        "result": result,
        "best_score": best_score,
        "second_best": second_best,
        "score_gap": best_score - second_best,
        "keyword_hits": best_keyword_hits,
        "alias_hits": best_alias_hits,
        "anchor_hits": best_anchor_hits,
    }


def _fails_context_guard(normalized_question: str, entry: dict) -> bool:
    if entry["group"] != "regression":
        return False

    if "residual" in normalized_question and not any(
        term in normalized_question
        for term in ("regression", "model", "fit", "inference", "error", "square error")
    ):
        return True

    if "linear" in normalized_question and "regression" not in normalized_question and "model" not in normalized_question:
        return True

    return False


def _normalize_gemini_result(topic: str, subtopic: str, entries: list[dict]) -> dict:
    if _normalize_text(topic) == "off topic" or _normalize_text(subtopic) == "off topic":
        return {
            "topic": "Needs Review",
            "subtopic": "Off-topic or mixed question",
            "confidence": "low",
            "route": "review",
            "used_gemini": True,
        }

    gemini_text = f"{topic} {subtopic}"
    gemini_tokens = _tokenize(gemini_text)
    normalized_combined = _normalize_text(gemini_text)

    best_entry = None
    best_score = 0
    for entry in entries:
        topic_tokens = _tokenize(entry["topic"])
        subtopic_tokens = _tokenize(entry["subtopic"])
        overlap = len(gemini_tokens & (topic_tokens | subtopic_tokens))
        topic_match = int(_normalize_text(entry["topic"]) in normalized_combined) * 3
        subtopic_match = int(_normalize_text(entry["subtopic"]) in normalized_combined) * 4
        keyword_match = sum(2 for keyword in entry["keywords"] if keyword and keyword in normalized_combined)
        score = overlap + topic_match + subtopic_match + keyword_match
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry and best_score > 0:
        return {
            "topic": best_entry["topic"],
            "subtopic": best_entry["subtopic"],
            "confidence": "high",
            "route": "main",
            "used_gemini": True,
        }

    return {
        "topic": topic or "Needs Review",
        "subtopic": subtopic or "Gemini uncertain",
        "confidence": "medium",
        "route": "review",
        "used_gemini": True,
    }


def _get_taxonomy(syllabus: str, syllabus_key: str) -> list[dict]:
    if syllabus_key not in _TAXONOMY_CACHE:
        _TAXONOMY_CACHE[syllabus_key] = _build_taxonomy(syllabus)
    return _TAXONOMY_CACHE[syllabus_key]


def _build_taxonomy(syllabus: str) -> list[dict]:
    units = _extract_units(syllabus)
    if _looks_like_data_science_syllabus(units):
        return _build_curated_data_science_taxonomy(units)
    return _build_generic_taxonomy_v3(units)


def _extract_units(syllabus: str) -> list[dict]:
    units = []
    current = None

    for raw_line in syllabus.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if re.match(r"^unit\s+\w+", line, flags=re.I):
            current = {"title": line, "body": []}
            units.append(current)
            continue

        if line.isupper() and len(line.split()) >= 3:
            current = {"title": line, "body": []}
            units.append(current)
            continue

        if line.lower().startswith("exemplar/"):
            continue

        if current is not None:
            current["body"].append(line)

    return units


def _looks_like_data_science_syllabus(units: list[dict]) -> bool:
    joined = " ".join(unit["title"] + " " + " ".join(unit["body"]) for unit in units).lower()
    required = ["regression", "support vector", "decision tree", "clustering"]
    return all(token in joined for token in required)


def _build_curated_data_science_taxonomy(units: list[dict]) -> list[dict]:
    unit_titles = {unit["title"].lower(): unit["title"] for unit in units}

    def pick_topic(fragment: str, fallback: str) -> str:
        for lowered, title in unit_titles.items():
            if fragment in lowered:
                return _clean_unit_title(title)
        return fallback

    taxonomy = [
        ("regression", "1. Overview of Statistical Linear Models", ["statistical linear model", "linear regression", "regression assumptions"], ["linear regression coefficients"]),
        ("regression", "2. Residuals and Regression Inference", ["residual", "regression inference", "goodness of fit"], ["evaluate regression model", "fits the data well"]),
        ("regression", "3. Generalized Linear Models (GLM)", ["generalized linear model", "glm"], []),
        ("regression", "4. Logistic Regression", ["logistic regression"], ["difference between logistic regression and linear regression", "advantage over linear regression"]),
        ("regression", "5. Interpretation of Odds and Odds Ratios", ["odds ratio", "odds ratios", "interpretation of odds"], ["interpret logistic regression coefficients"]),
        ("regression", "6. Maximum Likelihood Estimation in Logistic Regression", ["maximum likelihood estimation", "mle"], ["likelihood estimation"]),
        ("regression", "7. Poisson Regression", ["poisson regression"], []),
        ("regression", "8. Visualization and Interpretation of Logistic Regression", ["visualizing fitting logistic regression curves", "logistic regression curves", "visualize logistic regression"], ["predictors and response"]),
        ("classification", "2. Kernel Functions and Kernel Selection", ["kernel in svm", "kernels in svm", "kernel function", "kernel selection", "hyperplane", "kernel"], ["hard margin", "soft margin"]),
        ("classification", "1. Support Vector Machine (SVM)", ["support vector machine", "svm", "support vector regression"], ["separable and non separable"]),
        ("classification", "3. Applications of Classification Methods", ["applications of svm", "random forest classifiers excel", "face recognition"], ["sentimental analysis", "product review"]),
        ("classification", "4. Introduction to Ensemble Methods", ["ensemble methods", "ensemble learning"], ["classification accuracy", "advantages and disadvantages of ensemble"]),
        ("classification", "5. Bagging and Bootstrap Ensemble Methods", ["bagging", "bootstrap ensemble"], []),
        ("classification", "6. Boosting", ["boosting"], ["reduce model bias"]),
        ("classification", "7. Random Forest", ["random forest"], ["reduce overfitting"]),
        ("classification", "8. Growing of Random Forest", ["growing of random forest"], []),
        ("classification", "9. Random Feature Selection", ["random feature selection"], []),
        ("classification", "10. Classification Model Evaluation", ["classification model", "precision", "recall", "f1 score", "confusion matrix", "roc curve"], ["metrics are used"]),
        ("decision", "1. Decision Trees", ["decision tree", "decision trees", "pruning"], ["partition data", "feature space"]),
        ("decision", "2. Entropy in Decision Trees", ["entropy", "information gain"], ["decision tree entropy"]),
        ("decision", "3. Creating a Decision Tree", ["creating a decision tree", "steps involved in creating"], []),
        ("decision", "4. Decision Tree Algorithms", ["id3", "id4", "c4 5", "c4.5", "cart"], ["algorithms used to create decision trees"]),
        ("decision", "5. Random Forests", ["random forests", "combine multiple decision trees"], ["tree based ensemble"]),
        ("decision", "6. Ensemble Methods", ["ensemble methods", "individual classifiers"], []),
        ("decision", "7. Bagging and Boosting", ["bagging and boosting", "bias and variance"], ["reduce variance and bias"]),
        ("decision", "8. C5.0 Boosting", ["c5 0 boosting", "c5.0 boosting"], []),
        ("decision", "9. Gradient Boosting Machines", ["gradient boosting machines", "gradient boosting"], []),
        ("decision", "10. XGBoost", ["xgboost"], []),
        ("decision", "11. Model Evaluation", ["evaluate decision tree", "ensemble model performance"], ["metrics are used"]),
        ("clustering", "1. Overview of Clustering and Unsupervised Learning", ["clustering", "unsupervised learning"], ["supervised learning"]),
        ("clustering", "2. Introduction to Clustering Methods", ["clustering methods"], ["different clustering methods"]),
        ("clustering", "3. Partitioning Methods", ["partitioning methods", "k means", "k-means"], ["cluster assignment"]),
        ("clustering", "4. Density-Based Spatial Clustering", ["density based spatial clustering", "density-based spatial clustering", "dbscan"], ["varying shapes and densities"]),
        ("clustering", "5. Hierarchical Clustering Methods", ["hierarchical clustering"], ["tree like structure of clusters"]),
        ("clustering", "6. Agglomerative Hierarchical Clustering", ["agglomerative"], []),
        ("clustering", "7. Dendrograms and Cluster Selection", ["dendrogram", "number of clusters", "optimal number of clusters"], ["elbow method", "silhouette"]),
        ("clustering", "8. Divisive Clustering Techniques", ["divisive clustering"], ["agglomerative clustering"]),
    ]

    topic_map = {
        "regression": pick_topic("regression", "UNIT III - REGRESSION MODELS"),
        "classification": pick_topic("classification", "UNIT IV - CLASSIFICATION METHODS"),
        "decision": pick_topic("decision", "UNIT V - DECISION TREES & ENSEMBLES METHODS"),
        "clustering": pick_topic("clustering", "UNIT VI - CLUSTERING METHODS"),
    }

    entries = []
    for group, subtopic, keywords, aliases in taxonomy:
        keyword_tokens = set()
        for phrase in keywords + aliases + [subtopic]:
            keyword_tokens |= _tokenize(phrase)
        entries.append({
            "group": group,
            "topic": topic_map[group],
            "subtopic": subtopic,
            "keywords": [_normalize_text(keyword) for keyword in keywords],
            "aliases": [_normalize_text(alias) for alias in aliases],
            "anchors": {token for token in keyword_tokens if token in GROUP_ANCHORS[group]} | GROUP_ANCHORS[group],
            "tokens": keyword_tokens,
        })
    return entries


def _build_generic_taxonomy(units: list[dict]) -> list[dict]:
    entries = []
    for unit in units:
        topic = _clean_unit_title(unit["title"])
        joined = ", ".join(unit["body"])
        parts = [part.strip(" .-") for part in re.split(r",|•|-{1,2}", joined) if part.strip(" .-")]
        for index, part in enumerate(parts, 1):
            entries.append({
                "group": topic,
                "topic": topic,
                "subtopic": f"{index}. {part}",
                "keywords": [_normalize_text(part)],
                "aliases": [],
                "anchors": _tokenize(part),
                "tokens": _tokenize(part),
            })
    return entries


def _build_generic_taxonomy_v2(units: list[dict]) -> list[dict]:
    entries = []
    for unit in units:
        topic = _clean_unit_title(unit["title"])
        joined = " ".join(unit["body"])
        parts = _split_generic_subtopics(joined)
        for index, part in enumerate(parts, 1):
            tokens = _tokenize(part)
            if not tokens:
                continue
            entries.append({
                "group": topic,
                "topic": topic,
                "subtopic": f"{index}. {part}",
                "keywords": [_normalize_text(part)],
                "aliases": [],
                "anchors": tokens,
                "tokens": tokens,
                "generic": True,
            })
    return entries


def _build_generic_taxonomy_v3(units: list[dict]) -> list[dict]:
    entries = []
    for unit in units:
        topic = _clean_unit_title(unit["title"])
        label_indexes: dict[str, int] = {}
        seen_fragments: set[tuple[str, str]] = set()
        for index, raw_line in enumerate(unit["body"], 1):
            line = raw_line.strip(" .-")
            if len(line) < 8:
                continue
            fragments = [line]
            fragments.extend(fragment for fragment in _split_generic_subtopics(line) if fragment != line)

            for fragment in fragments:
                label = _generic_subtopic_label(fragment)
                if label not in label_indexes:
                    label_indexes[label] = len(label_indexes) + 1
                major_index = label_indexes[label]
                fragment_key = (label, _normalize_text(fragment))
                if fragment_key in seen_fragments:
                    continue
                seen_fragments.add(fragment_key)
                entries.append(_generic_entry(topic, major_index, fragment, label_override=label))
    return [entry for entry in entries if entry["tokens"]]


def _generic_entry(topic: str, index: int, text: str, label_override: str | None = None) -> dict:
    tokens = _tokenize(f"{topic} {text}")
    aliases = [alias for alias in _split_generic_subtopics(text) if alias != text][:4]
    label = label_override or _generic_subtopic_label(text)
    anchors = {token for token in tokens if token not in GENERIC_ANCHOR_STOPWORDS}
    return {
        "group": topic,
        "topic": topic,
        "subtopic": f"{_format_generic_index(index)} {label}",
        "keywords": [_normalize_text(text)],
        "aliases": [_normalize_text(alias) for alias in aliases],
        "anchors": anchors or tokens,
        "tokens": tokens,
        "generic": True,
    }


def _generic_subtopic_label(text: str) -> str:
    keyword_label = _keyword_subtopic_label(text)
    if keyword_label:
        return keyword_label

    chunks = [chunk.strip(" .-") for chunk in re.split(r",|;", text) if chunk.strip(" .-")]
    weak_starts = {"and", "or", "for", "of", "to", "data", "analysis", "techniques", "method", "methods"}
    if chunks:
        label = chunks[0]
        if label and (label[0].islower() or label.split()[0].lower() in weak_starts) and len(chunks) > 1:
            label = chunks[1]
        if len(label.split()) <= 4 and len(chunks) > 1:
            second = chunks[1] if chunks[0] == label and len(chunks) > 1 else chunks[0]
            if second != label:
                label = f"{label}, {second}"
    else:
        label = text.strip(" .-")

    if ":" in label:
        left, right = [part.strip() for part in label.split(":", 1)]
        if len(left.split()) <= 3 and len(right.split()) >= 2:
            label = f"{left}: {right}"
        else:
            label = right or left

    words = label.split()
    if len(words) > 12:
        label = " ".join(words[:12])
    return label


def _keyword_subtopic_label(text: str) -> str | None:
    lowered = text.lower()
    rules = [
        (("introduction to cluster analysis", "cluster analysis", "major clustering methods"), "Introduction to Cluster Analysis"),
        (("k-means", "k means", "k-medoids"), "Partitioning Clustering Methods"),
        (("dbscan", "density based"), "Density-Based Clustering"),
        (("hierarchical", "agglomerative", "divisive"), "Hierarchical Clustering"),
        (("business intelligence", "oltp", "dw in bi"), "Business Intelligence Concepts"),
        (("data warehouse", "warehousing", "decision support"), "Data Warehousing Concepts"),
        (("three-tier", "warehouse design"), "Data Warehouse Architecture"),
        (("etl",), "ETL Process"),
        (("metadata",), "Metadata in Data Warehousing"),
        (("rolap", "molap", "holap", "olap"), "OLAP Concepts"),
        (("multilayer perceptron", "mlp"), "Multilayer Perceptrons (MLPs)"),
        (("architectures of neural networks", "architecture of neural"), "Architectures of Neural Networks"),
        (("feed forward", "feedforward"), "Feed Forward Neural Networks"),
        (("back propagation", "backpropagation"), "Error Back Propagation"),
        (("learning factors", "performance issues"), "Learning Factors and Performance Issues"),
        (("gradient descent", "stochastic gd", "momentum"), "Gradient Descent"),
        (("sigmoid", "activation function"), "Activation Functions and Sigmoid Neurons"),
        (("recurrent neural network", "rnn"), "Recurrent Neural Networks"),
        (("cnn", "convolutional neural"), "Convolutional Neural Networks"),
        (("lstm",), "LSTM Networks"),
        (("applications of ff neural networks", "applications of feed forward neural networks"), "Applications of Feed Forward Neural Networks"),
        (("self-organizing map", "som"), "Self-Organizing Maps"),
        (("adaptive resonance theory", "art"), "Adaptive Resonance Theory"),
        (("semantic networks",), "Semantic Networks"),
        (("pattern clustering",), "Pattern Clustering Networks"),
        (("feature mapping",), "Feature Mapping Networks"),
        (("network anomaly detection", "anomaly detection"), "Network Anomaly Detection Techniques"),
        (("classify network attacks", "classify network", "network attacks", "transport layer attacks"), "Classification of Network Attacks"),
        (("botnet",), "Botnet Detection and Topology"),
        (("fraud", "authentication", "biometric"), "Protecting Sensitive Information and Assets"),
        (("gan", "adversarial", "intrusion detection"), "GAN Attacks and Defenses"),
        (("roc curve", "overfitting", "bias variance", "training and test"), "Evaluating Algorithms"),
    ]
    for keywords, label in rules:
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


def _format_generic_index(index: int) -> str:
    if index >= 100:
        major = index // 100
        minor = index % 100
        return f"{major}.{minor}"
    return f"{index}."


def _split_generic_subtopics(text: str) -> list[str]:
    normalized = text.replace("â€“", "-").replace("Ã¢â‚¬â€œ", "-")
    raw_parts = re.split(r"\.\s+|;\s+|:\s+|,\s+(?=[A-Z])|,\s+(?=[a-z])", normalized)
    parts = []
    for raw_part in raw_parts:
        part = raw_part.strip(" .-")
        if len(part) < 8:
            continue
        if part.lower().startswith(("unit ", "exemplar/")):
            continue
        parts.append(part)
    return parts


def _clean_unit_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip()
    return cleaned.replace("–", "-").replace("â€“", "-")


def _normalize_text(text: str) -> str:
    text = text.lower().replace("’", "'").replace("â€™", "'").replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> set[str]:
    stop_words = {
        "the", "and", "of", "to", "in", "for", "with", "how", "what", "is", "are",
        "a", "an", "its", "using", "into", "from", "on", "or", "by", "also",
        "explain", "describe", "discuss", "write", "note", "compare", "define",
        "used", "use", "mean", "means", "detail", "details", "different",
    }
    return {
        _stem_token(token)
        for token in re.findall(r"[a-z0-9]+", _normalize_text(text))
        if len(token) > 2 and token not in stop_words
    }


def _stem_token(token: str) -> str:
    for suffix in ("ation", "ions", "ment", "ing", "ers", "ies", "ion", "ity", "est", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            if suffix == "ies":
                return token[:-3] + "y"
            return token[:-len(suffix)]
    return token
