import difflib
import re

GENERIC_TOKENS = {
    "what", "how", "why", "when", "where", "which", "who", "explain", "describe",
    "discuss", "compare", "define", "write", "note", "detail", "details", "used",
    "using", "their", "there", "does", "work", "works", "used", "mean", "means",
    "role", "advantages", "disadvantages", "application", "applications", "algorithm",
}
TOKEN_SYNONYMS = {
    "working": "work",
    "principle": "work",
    "classify": "classification",
    "classifier": "classification",
    "classifiers": "classification",
    "visualizing": "visualize",
    "visualized": "visualize",
    "visualization": "visualize",
    "fitting": "fit",
    "coefficients": "coefficient",
    "assumptions": "assumption",
    "models": "model",
    "methods": "method",
    "techniques": "technique",
}
TRAILING_NOISE_PATTERN = re.compile(
    r"(?i)\s*(?:with\s+(?:an?\s+)?(?:example|examples|suitable example|suitable examples)|in detail|in brief|briefly|and its applications?|and its significance|and their applications?|with neat sketch|with diagram|with a neat diagram)\.?\s*$"
)
CANONICAL_SUBTOPIC_QUESTIONS = {
    "1. Overview of Statistical Linear Models": "Explain the concept and overview of statistical linear models.",
    "2. Residuals and Regression Inference": "What are residuals and how are they used to evaluate regression models?",
    "3. Generalized Linear Models (GLM)": "Explain generalized linear models (GLM) and their components.",
    "4. Logistic Regression": "Explain logistic regression and its working principle.",
    "5. Interpretation of Odds and Odds Ratios": "Explain the interpretation of odds and odds ratios in logistic regression.",
    "6. Maximum Likelihood Estimation in Logistic Regression": "What is maximum likelihood estimation (MLE) and how is it used in logistic regression?",
    "7. Poisson Regression": "Explain Poisson regression and its applications.",
    "8. Visualization and Interpretation of Logistic Regression": "How are logistic regression curves visualized and interpreted?",
    "1. Support Vector Machine (SVM)": "What is the Support Vector Machine classification algorithm and how does it classify data points?",
    "2. Kernel Functions and Kernel Selection": "What are kernel functions and how are they used in SVM classification?",
    "3. Applications of Classification Methods": "Explain with examples where SVM and random forest classifiers excel.",
    "4. Introduction to Ensemble Methods": "What are ensemble methods and how do they improve classification accuracy?",
    "5. Bagging and Bootstrap Ensemble Methods": "Explain bagging and bootstrap ensemble methods.",
    "6. Boosting": "What is boosting and how does it reduce model bias?",
    "7. Random Forest": "What is random forest and how does it work?",
    "8. Growing of Random Forest": "Explain the growing of random forest algorithm.",
    "9. Random Feature Selection": "Explain random feature selection in random forest.",
    "10. Classification Model Evaluation": "How do you evaluate the performance of a classification model and what metrics are used?",
    "1. Decision Trees": "What is a decision tree and how is it used to partition data or feature space?",
    "2. Entropy in Decision Trees": "What is entropy and how is it used in decision trees?",
    "3. Creating a Decision Tree": "Explain the steps involved in creating a decision tree.",
    "4. Decision Tree Algorithms": "Compare decision tree algorithms such as ID3, C4.5 and CART.",
    "5. Random Forests": "What is random forest and how does it combine multiple decision trees to improve accuracy?",
    "6. Ensemble Methods": "What advantages do ensemble methods offer over individual classifiers?",
    "7. Bagging and Boosting": "Explain bagging and boosting and their impact on bias and variance.",
    "8. C5.0 Boosting": "What is C5.0 boosting and how does it differ from other boosting methods?",
    "9. Gradient Boosting Machines": "Explain Gradient Boosting Machines and how they work.",
    "10. XGBoost": "What is XGBoost and how does it improve traditional gradient boosting?",
    "11. Model Evaluation": "How do you evaluate decision tree or ensemble model performance and what metrics are used?",
    "1. Overview of Clustering and Unsupervised Learning": "What is clustering and how is it used in unsupervised learning?",
    "2. Introduction to Clustering Methods": "What are the different clustering methods used in data analysis?",
    "3. Partitioning Methods": "Explain partitioning clustering methods and how they assign data points to clusters.",
    "4. Density-Based Spatial Clustering": "Explain density-based spatial clustering and its working principle.",
    "5. Hierarchical Clustering Methods": "What is hierarchical clustering and how does it create a tree-like structure of clusters?",
    "6. Agglomerative Hierarchical Clustering": "Explain agglomerative hierarchical clustering technique.",
    "7. Dendrograms and Cluster Selection": "Explain the role of dendrograms in hierarchical clustering.",
    "8. Divisive Clustering Techniques": "Explain divisive clustering techniques and how they differ from agglomerative clustering.",
}
DISPLAY_NOISE_PATTERNS = [
    re.compile(r"\[[^\]]{1,20}\]"),
    re.compile(r"\bCO\d+\b", re.I),
    re.compile(r"\bL\d+\b", re.I),
    re.compile(r"\bSr\.?\s*No\.?.*$", re.I),
]
CLAUSE_SPLIT_PATTERN = re.compile(
    r"(?:(?<=[\?\.;:])\s+)|(?=\b(?:What|How|Why|When|Which|Who|Explain|Define|Compare|Discuss|Describe|Write|State|Evaluate|Illustrate|List|Differentiate|Classify|Comment|Derive|Calculate|Find|Determine|Identify|Compute|Estimate|Predict|Draw|Give|Mention)\b)"
)
QUESTION_STARTERS = (
    "what", "how", "why", "when", "where", "which", "who", "explain", "define", "compare",
    "discuss", "describe", "write", "state", "evaluate", "illustrate", "list", "differentiate",
    "classify", "comment", "derive", "calculate", "find", "determine", "identify", "compute",
    "estimate", "predict", "draw", "give", "mention",
)
VAGUE_CLAUSE_PATTERN = re.compile(
    r"(?i)^(?:how|what|why|when|which|who|explain|describe|discuss|state|evaluate|list)\s+"
    r"(?:it|they|this|these|its|their)\b"
)
WEAK_QUESTION_PATTERN = re.compile(
    r"(?i)^(?:what\s+are\s+(?:advantages|limitations)|how\s+it\s+is\s+used|write\s+an\s+algorithm\s+for\s+it)\b"
)
CONCEPT_PATTERNS = {
    "overview": re.compile(r"\boverview|statistical linear model|what is linear regression|primary objectives|applications?\b", re.I),
    "assumption": re.compile(r"\bassumption|assumptions\b", re.I),
    "coefficient": re.compile(r"\bcoefficient|coefficients\b", re.I),
    "goodness_fit": re.compile(r"\bgoodness of fit|metrics?|performance|evaluate\b", re.I),
    "residual": re.compile(r"\bresidual|inference\b", re.I),
    "glm": re.compile(r"\bgeneralized linear model|glm\b", re.I),
    "logistic_compare": re.compile(r"\bdiffer|difference|compare|advantage\b", re.I),
    "logistic_core": re.compile(r"\blogistic regression|sigmoid|logistic function\b", re.I),
    "odds": re.compile(r"\bodds ratio|odds ratios|odds\b", re.I),
    "mle": re.compile(r"\bmaximum likelihood|mle\b", re.I),
    "poisson": re.compile(r"\bpoisson\b", re.I),
    "svm": re.compile(r"\bsvm|support vector|hyperplane|margin\b", re.I),
    "kernel": re.compile(r"\bkernel\b", re.I),
    "ensemble": re.compile(r"\bensemble|random forest\b", re.I),
    "bagging_boosting": re.compile(r"\bbagging|boosting|bootstrap\b", re.I),
    "decision_tree": re.compile(r"\bdecision tree|decision trees|pruning\b", re.I),
    "entropy": re.compile(r"\bentropy|information gain|gini\b", re.I),
    "clustering": re.compile(r"\bclustering|cluster|unsupervised\b", re.I),
    "hierarchical": re.compile(r"\bhierarchical|agglomerative|divisive\b", re.I),
    "dendrogram": re.compile(r"\bdendrogram\b", re.I),
    "kmeans": re.compile(r"\bk[\s-]?means?\b", re.I),
    "kmedoids": re.compile(r"\bk[\s-]?medoids?\b", re.I),
    "dbscan": re.compile(r"\bdbscan|density[- ]based\b", re.I),
    "olap": re.compile(r"\bolap|rolap|molap|holap\b", re.I),
    "etl": re.compile(r"\betl\b", re.I),
    "warehouse": re.compile(r"\bdata warehouse|warehousing|warehouse\b", re.I),
    "business_intelligence": re.compile(r"\bbusiness intelligence|\bbi\b|\boltp\b|\bdw\b", re.I),
    "mlp": re.compile(r"\bmlp|multilayer perceptron\b", re.I),
    "feedforward": re.compile(r"\bfeed forward|feedforward\b", re.I),
    "backprop": re.compile(r"\bback propagation|backpropagation\b", re.I),
    "gradient_descent": re.compile(r"\bgradient descent|stochastic gradient descent|momentum\b", re.I),
    "activation": re.compile(r"\bactivation function|sigmoid neuron|sigmoid\b", re.I),
    "rnn": re.compile(r"\brnn|recurrent neural network\b", re.I),
    "cnn": re.compile(r"\bcnn|convolutional neural network\b", re.I),
    "lstm": re.compile(r"\blstm\b", re.I),
    "anomaly_detection": re.compile(r"\banomaly detection|anomaly\b", re.I),
    "challenge": re.compile(r"\bchallenge|limitations?|difficult(?:y|ies)\b", re.I),
    "network_attacks": re.compile(r"\bnetwork attack|transport layer attacks?|classify network attacks?\b", re.I),
    "transport_attacks": re.compile(r"\btransport layer attacks?\b", re.I),
    "botnet": re.compile(r"\bbotnet|botnet topology\b", re.I),
    "user_authentication": re.compile(r"\bauthentication|keystroke|biometric|facial recognition|account reputation\b", re.I),
    "fraud_detection": re.compile(r"\bfraud detection|cloud ai solutions\b", re.I),
}

def _normalize_question(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"^\s*(q\.?\s*)?\d+[a-z]?[.)-]?\s*", "", lowered)
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered

def _tokenize(text: str) -> set[str]:
    normalized_tokens = set()
    for token in _normalize_question(text).split():
        if len(token) <= 2 or token in GENERIC_TOKENS:
            continue
        token = TOKEN_SYNONYMS.get(token, token)
        token = _stem_token(token)
        if token and token not in GENERIC_TOKENS:
            normalized_tokens.add(token)
    return normalized_tokens

def is_duplicate(new_question: str, existing_questions: list[dict], threshold: float = 0.85) -> dict | None:
    """Return the matching existing question entry if it is similar enough."""
    nq_norm = _normalize_question(new_question)
    nq_tokens = _tokenize(new_question)
    nq_intent = _question_intent(new_question)
    nq_concepts = _question_concepts(new_question)
    for entry in existing_questions:
        entry_concepts = entry.get("concepts") or set()
        if nq_concepts and entry_concepts and nq_concepts.isdisjoint(entry_concepts):
            continue
        entry_texts = [entry["main_question"], *entry.get("variants", [])]
        best_ratio = 0.0
        best_overlap = 0.0
        best_core_overlap = 0
        for candidate in entry_texts:
            eq_norm = _normalize_question(candidate)
            eq_tokens = _tokenize(candidate)
            ratio = difflib.SequenceMatcher(None, nq_norm, eq_norm).ratio()
            token_overlap = len(nq_tokens & eq_tokens) / max(len(nq_tokens | eq_tokens), 1)
            best_ratio = max(best_ratio, ratio)
            best_overlap = max(best_overlap, token_overlap)
            best_core_overlap = max(best_core_overlap, len(nq_tokens & eq_tokens))

        entry_tokens = entry.get("all_tokens") or _entry_tokens(entry)
        aggregate_overlap = len(nq_tokens & entry_tokens) / max(len(nq_tokens | entry_tokens), 1)
        contains_same_core = nq_tokens and entry_tokens and (nq_tokens <= entry_tokens or entry_tokens <= nq_tokens)
        same_intent = nq_intent == _question_intent(entry["main_question"])

        if (
            best_ratio >= 0.90
            or (best_overlap >= 0.78 and best_core_overlap >= 3)
            or (best_ratio >= 0.70 and best_overlap >= 0.52 and best_core_overlap >= 3)
            or (same_intent and best_core_overlap >= 4 and aggregate_overlap >= 0.50)
            or (contains_same_core and best_core_overlap >= 3 and aggregate_overlap >= 0.62)
        ):
            return entry
    return None

def add_question(question: str, source: str, topic: str, subtopic: str, organized_data: dict) -> bool:
    """Adds or merges a question into organized_data. Returns True when a new entry is created."""
    meta = organized_data.setdefault("__meta__", {})
    subtopic_key = (topic, subtopic)
    subtopic_meta = meta.setdefault(subtopic_key, {"buckets": {}})

    if topic not in organized_data:
        organized_data[topic] = {}

    if subtopic not in organized_data[topic]:
        organized_data[topic][subtopic] = []

    existing = organized_data[topic][subtopic]
    bucket_key = _bucket_key(question)
    if topic.startswith("Appendix"):
        candidate_indexes = subtopic_meta["buckets"].get(bucket_key, [])
        candidate_entries = [existing[index] for index in candidate_indexes]
    else:
        candidate_entries = existing
    duplicate = is_duplicate(question, candidate_entries)
    display_question = _extract_best_clause(question, topic, subtopic)
    if duplicate:
        duplicate["sources"].add(source)
        if question not in duplicate["variants"]:
            duplicate["variants"].append(question)
            duplicate["all_tokens"] = _entry_tokens(duplicate)
            duplicate["concepts"] = _entry_concepts(duplicate)
            duplicate["main_question"] = _synthesize_main_question(duplicate, subtopic)
        return False

    new_entry = {
        "main_question": _canonicalize_display_question(display_question, subtopic),
        "variants": [question],
        "sources": {source},
    }
    new_entry["all_tokens"] = _entry_tokens(new_entry)
    new_entry["concepts"] = _entry_concepts(new_entry)
    organized_data[topic][subtopic].append(new_entry)
    subtopic_meta["buckets"].setdefault(bucket_key, []).append(len(existing) - 1)
    return True

def _choose_main_question(current: str, candidate: str, subtopic: str) -> str:
    candidates = [
        _canonicalize_display_question(_clean_display_question(current), subtopic),
        _canonicalize_display_question(_clean_display_question(candidate), subtopic),
    ]
    scored = sorted(candidates, key=_question_quality_score, reverse=True)
    return scored[0]

def _clean_display_question(question: str) -> str:
    cleaned = question
    for pattern in DISPLAY_NOISE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = TRAILING_NOISE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"[?]{2,}", "?", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .;:-")
    return cleaned

def _canonicalize_display_question(question: str, subtopic: str) -> str:
    cleaned = _clean_display_question(question)
    tokens = _tokenize(cleaned)
    starts_like_question = cleaned.lower().startswith(QUESTION_STARTERS)
    if (len(tokens) < 4 or not starts_like_question) and subtopic in CANONICAL_SUBTOPIC_QUESTIONS:
        return CANONICAL_SUBTOPIC_QUESTIONS[subtopic]
    return cleaned

def _extract_best_clause(question: str, topic: str, subtopic: str) -> str:
    cleaned_question = _clean_display_question(question)
    clauses = [clause.strip(" .;:-") for clause in CLAUSE_SPLIT_PATTERN.split(cleaned_question) if clause.strip(" .;:-")]
    if not clauses:
        return cleaned_question

    target_tokens = _tokenize(f"{topic} {subtopic}")
    scored_clauses = sorted(clauses, key=lambda clause: _clause_score(clause, target_tokens), reverse=True)
    best_clause = scored_clauses[0]
    best_tokens = _tokenize(best_clause)
    if _clause_score(best_clause, target_tokens)[0] <= 0:
        return cleaned_question
    if VAGUE_CLAUSE_PATTERN.match(best_clause) or WEAK_QUESTION_PATTERN.match(best_clause):
        return cleaned_question
    if len(best_tokens) < 4:
        return cleaned_question
    return best_clause

def _clause_score(clause: str, target_tokens: set[str]) -> tuple[int, int, int]:
    clause_tokens = _tokenize(clause)
    overlap = len(clause_tokens & target_tokens)
    question_like = int("?" in clause or clause.lower().startswith(QUESTION_STARTERS))
    preferred_length = -abs(len(clause) - 90)
    return (overlap, question_like, preferred_length)

def _question_quality_score(question: str) -> tuple[int, int, int]:
    tokens = _tokenize(question)
    has_question_mark = int("?" in question)
    informative_token_count = len(tokens)
    preferred_length = -abs(len(question) - 85)
    return (has_question_mark, informative_token_count, preferred_length)


def _entry_tokens(entry: dict) -> set[str]:
    tokens = set()
    for text in [entry.get("main_question", ""), *entry.get("variants", [])]:
        tokens |= _tokenize(text)
    return tokens


def _entry_concepts(entry: dict) -> set[str]:
    concepts = set()
    for text in [entry.get("main_question", ""), *entry.get("variants", [])]:
        concepts |= _question_concepts(text)
    return concepts


def _question_concepts(question: str) -> set[str]:
    concepts = set()
    for label, pattern in CONCEPT_PATTERNS.items():
        if pattern.search(question):
            concepts.add(label)
    return concepts


def _question_intent(question: str) -> str:
    lowered = _clean_display_question(question).lower()
    for starter in QUESTION_STARTERS:
        if lowered.startswith(starter):
            return starter
    return "statement"


def _centrality_score(candidate: str, variants: list[str]) -> float:
    candidate_norm = _normalize_question(candidate)
    scores = []
    for variant in variants:
        variant_norm = _normalize_question(variant)
        scores.append(difflib.SequenceMatcher(None, candidate_norm, variant_norm).ratio())
    return sum(scores) / max(len(scores), 1)


def _synthesize_main_question(entry: dict, subtopic: str) -> str:
    cleaned_variants = []
    seen = set()
    for variant in entry.get("variants", []):
        cleaned = _canonicalize_display_question(_clean_display_question(variant), subtopic)
        if cleaned and cleaned not in seen:
            cleaned_variants.append(cleaned)
            seen.add(cleaned)

    if not cleaned_variants:
        return _canonicalize_display_question(entry.get("main_question", ""), subtopic)

    concepts = _entry_concepts(entry)
    targeted = _targeted_canonical_question(subtopic, concepts)
    if targeted:
        return targeted

    if len(cleaned_variants) >= 2 and subtopic in CANONICAL_SUBTOPIC_QUESTIONS:
        template = CANONICAL_SUBTOPIC_QUESTIONS[subtopic]
        template_tokens = _tokenize(template)
        variant_union = set().union(*(_tokenize(item) for item in cleaned_variants))
        if len(template_tokens & variant_union) >= max(2, len(template_tokens) // 3):
            return template

    generic_title = _generic_cluster_title(cleaned_variants, subtopic)
    if generic_title:
        return generic_title

    ranked = sorted(
        cleaned_variants,
        key=lambda item: (
            _centrality_score(item, cleaned_variants),
            *_question_quality_score(item),
        ),
        reverse=True,
    )
    return ranked[0]


def _targeted_canonical_question(subtopic: str, concepts: set[str]) -> str | None:
    if subtopic == "1. Overview of Statistical Linear Models":
        if "assumption" in concepts and "overview" not in concepts:
            return "What are the assumptions of linear regression?"
        if "coefficient" in concepts:
            return "How do you interpret linear regression coefficients?"
    if subtopic == "2. Residuals and Regression Inference":
        if "goodness_fit" in concepts and "residual" not in concepts:
            return "How do you evaluate the goodness of fit of a regression model and what metrics are used?"
    if subtopic == "4. Logistic Regression":
        if "logistic_compare" in concepts:
            return "Compare logistic regression and linear regression."
    if subtopic == "5. Interpretation of Odds and Odds Ratios":
        if "odds" in concepts:
            return "Explain the interpretation of odds and odds ratios in logistic regression."

    lowered_subtopic = subtopic.lower()
    if "partitioning clustering methods" in lowered_subtopic:
        if {"kmeans", "kmedoids"} <= concepts:
            return "Compare K-Means and K-Medoids clustering techniques."
        if "kmeans" in concepts:
            return "Explain the K-Means clustering technique with an example."
    if "density-based clustering" in lowered_subtopic or "density-based spatial clustering" in lowered_subtopic:
        if "dbscan" in concepts:
            return "Explain DBSCAN clustering method with examples."
    if "hierarchical clustering" in lowered_subtopic:
        return "Explain hierarchical clustering methods."
    if "business intelligence" in lowered_subtopic:
        if "warehouse" in concepts:
            return "Explain the role of a data warehouse in Business Intelligence systems."
        return "Explain Business Intelligence concepts and components."
    if "etl process" in lowered_subtopic:
        return "Explain the ETL process in data warehousing."
    if "olap" in lowered_subtopic:
        return "Differentiate between ROLAP, MOLAP and HOLAP."
    if "multilayer perceptrons" in lowered_subtopic:
        if "feedforward" in concepts:
            return "Explain the architecture of a Multilayer Perceptron (MLP) and how it differs from a single-layer perceptron."
        return "Explain the architecture of a Multilayer Perceptron (MLP)."
    if "architectures of neural networks" in lowered_subtopic:
        return "Explain feed forward neural networks and their architecture."
    if "feed forward neural networks" in lowered_subtopic:
        return "Explain Feed Forward Neural Networks and their architecture."
    if "error back propagation" in lowered_subtopic or "back propagation" in lowered_subtopic:
        return "Explain the Error Back Propagation Algorithm."
    if "learning factors and performance issues" in lowered_subtopic:
        return "Discuss learning factors and performance issues in feed forward neural networks."
    if "gradient descent" in lowered_subtopic:
        return "Explain Gradient Descent with example."
    if "applications of feed forward neural networks" in lowered_subtopic:
        return "Describe some real-world applications of feed forward neural networks."
    if "activation functions" in lowered_subtopic or "sigmoid neurons" in lowered_subtopic:
        return "Explain the role of activation functions in MLPs and describe sigmoid neurons."
    if "recurrent neural networks" in lowered_subtopic:
        return "Describe the architecture of a recurrent neural network (RNN)."
    if "lstm networks" in lowered_subtopic:
        return "Explain LSTM Networks."
    if "network anomaly detection techniques" in lowered_subtopic:
        if "challenge" in concepts:
            return "Discuss the challenges associated with implementing network anomaly detection systems."
        return "Explain different network anomaly detection techniques used in cybersecurity."
    if "classification of network attacks" in lowered_subtopic:
        if "transport_attacks" in concepts:
            return "Explain different types of network and transport layer attacks."
        return "Explain how to classify network attacks using AI techniques."
    if "botnet topology" in lowered_subtopic:
        return "Explain different approaches used to identify botnet topology."
    if "protecting sensitive information and assets" in lowered_subtopic:
        if "fraud_detection" in concepts:
            return "Explain how machine learning algorithms are used for fraud detection."
        if "user_authentication" in concepts:
            return "Explain different techniques for securing user authentication."
        return "Explain how to protect sensitive information and assets."
    return None


def _generic_cluster_title(cleaned_variants: list[str], subtopic: str) -> str | None:
    if not cleaned_variants:
        return None

    subtopic_tokens = _tokenize(subtopic)
    candidate_rows = []
    for variant in cleaned_variants:
        normalized = _generic_title_cleanup(variant)
        variant_tokens = _tokenize(normalized)
        overlap = len(variant_tokens & subtopic_tokens)
        candidate_rows.append((normalized, variant_tokens, overlap))

    common_tokens = set.intersection(*(tokens for _, tokens, _ in candidate_rows if tokens)) if candidate_rows else set()
    scored = sorted(
        candidate_rows,
        key=lambda row: (
            len(common_tokens & row[1]),
            row[2],
            _centrality_score(row[0], [item[0] for item in candidate_rows]),
            -len(row[0]),
        ),
        reverse=True,
    )
    best = scored[0][0]

    if len(cleaned_variants) >= 2:
        best = _generic_title_cleanup(best, aggressive=True)

    return best


def _generic_title_cleanup(question: str, aggressive: bool = False) -> str:
    cleaned = _clean_display_question(question)
    cleaned = re.sub(r"(?i)\bwhat are some\b", "What are", cleaned)
    cleaned = re.sub(r"(?i)\bwhat are the\b", "What are the", cleaned)
    cleaned = re.sub(r"(?i)\bhow do we\b", "How do you", cleaned)
    cleaned = re.sub(r"(?i)\bhow does one\b", "How do you", cleaned)
    if aggressive:
        cleaned = re.sub(
            r"(?i)\s+(?:along with|and)\s+(?:its|their)\s+(?:applications?|advantages?|limitations?|significance).*$",
            "",
            cleaned,
        ).strip(" .;:-")
        cleaned = re.sub(r"(?i)\bwhat are some\b", "What are", cleaned)
        cleaned = re.sub(r"(?i)\bdescribe\b", "Explain", cleaned)
    return cleaned

def _stem_token(token: str) -> str:
    for suffix in ("ation", "ions", "ment", "ing", "ers", "ies", "ion", "ity", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            if suffix == "ies":
                return token[:-3] + "y"
            return token[:-len(suffix)]
    return token

def _bucket_key(question: str) -> str:
    tokens = sorted(_tokenize(question))
    if not tokens:
        return "__empty__"
    return "|".join(tokens[:4])

def format_source_label(filename: str) -> str:
    match = re.search(r"(April|Apr|October|Oct|November|Nov)\s+(\d{4})", filename, flags=re.I)
    if match:
        month = match.group(1)
        year = match.group(2)
        normalized_month = {
            "april": "Apr",
            "apr": "Apr",
            "october": "Oct",
            "oct": "Oct",
            "november": "Nov",
            "nov": "Nov",
        }[month.lower()]
        return f"{normalized_month} {year}"

    return re.sub(r"\.[^.]+$", "", filename).strip()

def sort_sources(sources: set[str]) -> list[str]:
    month_order = {"Apr": 4, "Oct": 10, "Nov": 11}

    def sort_key(label: str) -> tuple[int, int, str]:
        match = re.match(r"(Apr|Oct|Nov)\s+(\d{4})$", label)
        if match:
            return (int(match.group(2)), month_order[match.group(1)], label)
        return (9999, 99, label)

    return sorted(sources, key=sort_key)
