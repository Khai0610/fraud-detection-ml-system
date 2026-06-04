Fraud Detection ML System
1. Project Overview

Fraud Detection ML System is a real-time banking transaction fraud detection project. The system combines Machine Learning and Rule-based Engine to classify transactions into Safe, Pending, or Fraud groups.

The project was built to support fraud monitoring, transaction analysis, and data-driven decision making through a real-time dashboard and Power BI reports.

2. Business Problem

Banking fraud is a serious problem in digital financial transactions. Traditional rule-based systems can detect known fraud patterns, but they may not adapt well to new fraud behaviors.

This project aims to build a hybrid fraud detection system that combines Machine Learning prediction with rule-based validation to improve fraud monitoring and explainability.

3. Technologies Used
Python
Pandas, NumPy
Scikit-learn
XGBoost
FastAPI
MySQL
WebSocket
Power BI
HTML, CSS, JavaScript
4. Machine Learning Workflow

The Machine Learning workflow includes:

Data preprocessing
Feature engineering
Train/test split
Model training
Model evaluation
Rule extraction and validation
Fraud score calculation

Models used in this project:

Logistic Regression
Random Forest
XGBoost

Evaluation metrics:

Accuracy
Precision
Recall
F1-score
Confusion Matrix
5. System Architecture

The system follows this workflow:

New Transaction
        ↓
FastAPI Backend
        ↓
Feature Engineering
        ↓
Machine Learning Model
        ↓
Rule-based Engine
        ↓
Final Fraud Score
        ↓
MySQL Database
        ↓
Realtime Dashboard / Power BI
6. Main Features
Receive new banking transactions through API or form input
Predict fraud probability using Machine Learning model
Apply rule-based engine to support fraud validation
Calculate final fraud score
Classify transactions into Safe, Pending, or Fraud
Store transaction results in MySQL database
Update dashboard in real time using WebSocket
Visualize fraud statistics using Power BI
7. Project Structure
fraud-detection-ml-system/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── api.py
│   ├── predictor.py
│   ├── rule_engine.py
│   └── database.py
│
├── notebooks/
│   └── fraud_detection_training.ipynb
│
├── outputs/
│   ├── feature_columns.json
│   ├── validated_rules.json
│   └── important_features.json
│
├── images/
│   ├── dashboard.png
│   ├── system_architecture.png
│   ├── model_result.png
│   └── powerbi_dashboard.png
│
└── docs/
    └── project_summary.pdf
8. Result

The system can identify suspicious banking transactions by combining Machine Learning score and rule-based score. The final result is displayed on a real-time monitoring dashboard and stored in the database for further analysis.

9. Author

Ngô Văn Khải
Data Analyst
Email: khaingovannvk@gmail.com
