"""Starter churn model — WIP, needs finishing per the ticket.

Loads the users/features/orders tables and trains a classifier to predict
churn. Reports accuracy. Someone on the team flagged this "looks too good to
be true" — that's your cue.
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

users = pd.read_csv("../data/users.csv")
features = pd.read_csv("../data/features.csv")

df = users.merge(features, on="user_id")
df["account_closed_reason"] = df["account_closed_reason"].fillna("none")

X = pd.get_dummies(df[["region", "plan", "account_closed_reason"]])
y = df["churned"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier()
model.fit(X_train, y_train)

preds = model.predict(X_test)
print("accuracy:", accuracy_score(y_test, preds))
