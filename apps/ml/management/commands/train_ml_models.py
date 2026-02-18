"""
Management command to train all 3 ML models from scratch.
Downloads datasets, trains models using scikit-learn, and pickles them.

Usage: python manage.py train_ml_models
"""
import os
import pickle
import numpy as np
import pandas as pd
from io import StringIO
from django.core.management.base import BaseCommand
from django.conf import settings

ML_DIR = os.path.join(settings.BASE_DIR, 'ml_models')


class Command(BaseCommand):
    help = 'Train all ML models (At-Risk, Anomaly, Text Classifier) and save as pickle files'

    def handle(self, *args, **options):
        os.makedirs(ML_DIR, exist_ok=True)
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== ML Model Training ===\n'))

        self.train_at_risk_model()
        self.train_anomaly_model()
        self.train_text_classifier()

        self.stdout.write(self.style.SUCCESS('\n✅ All 3 models trained and saved!\n'))

    # =====================================================
    # MODEL 3A: Student At-Risk Prediction (Random Forest)
    # =====================================================
    def train_at_risk_model(self):
        self.stdout.write(self.style.HTTP_INFO('\n📊 [3A] Training At-Risk Prediction Model...'))

        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, classification_report

        # Download UCI Student Performance dataset
        url = 'https://archive.ics.uci.edu/ml/machine-learning-databases/student/student-mat.csv'
        try:
            self.stdout.write('   Downloading UCI Student Performance dataset...')
            df = pd.read_csv(url, sep=';')
            self.stdout.write(f'   Dataset loaded: {len(df)} records')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   Could not download dataset: {e}'))
            self.stdout.write('   Generating synthetic dataset instead...')
            df = self._generate_synthetic_student_data()

        # Feature Engineering
        # G3 is the final grade (0-20). At-risk = G3 < 10 (fail threshold)
        df['at_risk'] = (df['G3'] < 10).astype(int)

        features = ['absences', 'failures', 'studytime', 'G1', 'G2',
                     'age', 'Medu', 'Fedu', 'traveltime', 'freetime',
                     'goout', 'health']

        X = df[features].values
        y = df['at_risk'].values

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train/Test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train Random Forest
        model = RandomForestClassifier(
            n_estimators=100, max_depth=8, random_state=42, class_weight='balanced'
        )
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        self.stdout.write(f'   Accuracy: {acc:.2%}')
        self.stdout.write(f'   Features: {features}')

        # Save model + scaler + feature names
        model_data = {
            'model': model,
            'scaler': scaler,
            'features': features,
            'accuracy': acc,
        }
        path = os.path.join(ML_DIR, 'at_risk_model.pkl')
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

        self.stdout.write(self.style.SUCCESS(f'   ✅ Saved to {path}'))

    def _generate_synthetic_student_data(self):
        """Fallback: generate synthetic data matching UCI format."""
        np.random.seed(42)
        n = 500
        data = {
            'age': np.random.randint(15, 22, n),
            'Medu': np.random.randint(0, 5, n),
            'Fedu': np.random.randint(0, 5, n),
            'traveltime': np.random.randint(1, 5, n),
            'studytime': np.random.randint(1, 5, n),
            'failures': np.random.choice([0, 0, 0, 1, 2, 3], n),
            'freetime': np.random.randint(1, 6, n),
            'goout': np.random.randint(1, 6, n),
            'health': np.random.randint(1, 6, n),
            'absences': np.random.randint(0, 75, n),
            'G1': np.random.randint(0, 20, n),
            'G2': np.random.randint(0, 20, n),
        }
        # G3 correlated with G1, G2, studytime, inversely with absences/failures
        data['G3'] = np.clip(
            (data['G1'] * 0.3 + data['G2'] * 0.5 +
             data['studytime'] * 0.5 - data['failures'] * 3 -
             data['absences'] * 0.05 + np.random.normal(0, 2, n)).astype(int),
            0, 20
        )
        return pd.DataFrame(data)

    # =====================================================
    # MODEL 3B: Attendance Anomaly Detection (Isolation Forest)
    # =====================================================
    def train_anomaly_model(self):
        self.stdout.write(self.style.HTTP_INFO('\n🔍 [3B] Training Attendance Anomaly Model...'))

        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        # Generate realistic synthetic attendance data
        np.random.seed(42)
        n_normal = 400
        n_anomaly = 50

        # Normal students: high attendance, low streaks
        normal = pd.DataFrame({
            'attendance_pct': np.random.normal(78, 10, n_normal).clip(40, 100),
            'max_absent_streak': np.random.randint(0, 5, n_normal),
            'total_classes_missed': np.random.randint(2, 25, n_normal),
            'late_arrivals': np.random.randint(0, 8, n_normal),
            'subjects_below_75': np.random.randint(0, 2, n_normal),
        })

        # Anomalous students: low attendance, long streaks
        anomaly = pd.DataFrame({
            'attendance_pct': np.random.normal(35, 15, n_anomaly).clip(0, 60),
            'max_absent_streak': np.random.randint(5, 20, n_anomaly),
            'total_classes_missed': np.random.randint(30, 80, n_anomaly),
            'late_arrivals': np.random.randint(8, 25, n_anomaly),
            'subjects_below_75': np.random.randint(3, 7, n_anomaly),
        })

        df = pd.concat([normal, anomaly], ignore_index=True)
        features = list(df.columns)

        self.stdout.write(f'   Synthetic dataset: {len(df)} records ({n_normal} normal, {n_anomaly} anomalous)')

        # Scale
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df.values)

        # Train Isolation Forest
        model = IsolationForest(
            n_estimators=100, contamination=0.1, random_state=42
        )
        model.fit(X_scaled)

        # Evaluate on training data
        preds = model.predict(X_scaled)
        n_detected = (preds == -1).sum()
        self.stdout.write(f'   Anomalies detected: {n_detected}/{len(df)}')

        # Save
        model_data = {
            'model': model,
            'scaler': scaler,
            'features': features,
        }
        path = os.path.join(ML_DIR, 'anomaly_model.pkl')
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

        self.stdout.write(self.style.SUCCESS(f'   ✅ Saved to {path}'))

    # =====================================================
    # MODEL 3C: Discussion Auto-Tagger (TF-IDF + Naive Bayes)
    # =====================================================
    def train_text_classifier(self):
        self.stdout.write(self.style.HTTP_INFO('\n💬 [3C] Training Discussion Auto-Tagger...'))

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score

        # Build a labeled training dataset with academic Q&A patterns
        data = self._build_text_dataset()
        df = pd.DataFrame(data, columns=['text', 'tag'])

        self.stdout.write(f'   Training dataset: {len(df)} samples')
        self.stdout.write(f'   Tags: {df["tag"].value_counts().to_dict()}')

        X = df['text'].values
        y = df['tag'].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Build pipeline: TF-IDF -> Naive Bayes
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words='english')),
            ('clf', MultinomialNB(alpha=0.1)),
        ])

        pipeline.fit(X_train, y_train)

        # Evaluate
        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        self.stdout.write(f'   Accuracy: {acc:.2%}')

        # Save
        path = os.path.join(ML_DIR, 'text_classifier.pkl')
        with open(path, 'wb') as f:
            pickle.dump(pipeline, f)

        self.stdout.write(self.style.SUCCESS(f'   ✅ Saved to {path}'))

    def _build_text_dataset(self):
        """Generate a labeled text dataset for academic discussion classification."""
        dataset = []

        # QUESTION - Asking for help, how-to
        questions = [
            "How do I implement a binary search tree in Python?",
            "What is the difference between stack and queue?",
            "Can someone explain how polymorphism works in Java?",
            "How to solve this recurrence relation T(n) = 2T(n/2) + n?",
            "What is the time complexity of merge sort?",
            "How does dynamic memory allocation work in C?",
            "What are the different types of database normalization?",
            "Can anyone explain the concept of virtual memory?",
            "How to implement a hash table with collision handling?",
            "What is the difference between TCP and UDP protocols?",
            "How do you calculate the determinant of a matrix?",
            "What are design patterns and when should I use them?",
            "How to write a recursive function for fibonacci?",
            "What is the difference between process and thread?",
            "How does garbage collection work in Java?",
            "Can someone explain Big O notation with examples?",
            "How to implement a linked list from scratch?",
            "What exactly is a deadlock in operating systems?",
            "How do you normalize a database to 3NF?",
            "What is the difference between compiler and interpreter?",
            "How to connect to MySQL database using Python?",
            "What is an AVL tree and how does it self-balance?",
            "How to use pointers in C programming language?",
            "What is the difference between HTTP and HTTPS?",
            "Can anyone explain how DNS resolution works?",
            "How to implement breadth-first search algorithm?",
            "What are the ACID properties in database systems?",
            "How does public key cryptography work?",
            "What is the OSI model and its seven layers?",
            "How to implement quicksort with random pivot?",
            "What is a semaphore in operating systems?",
            "How to create a REST API in Django?",
            "What is the purpose of an abstract class?",
            "How does the internet routing protocol work?",
            "What is the role of an operating system kernel?",
            "How to implement Dijkstra shortest path algorithm?",
            "What are joins in SQL and types of joins?",
            "How does CSS flexbox layout work?",
            "What is machine learning supervised vs unsupervised?",
            "How to deploy a Django application to production?",
        ]

        # DOUBT - Confusion, clarification needed, not understanding
        doubts = [
            "I'm confused about the difference between abstract class and interface",
            "I don't understand why my code gives segmentation fault",
            "Confused about when to use ArrayList vs LinkedList in Java",
            "Not sure why my SQL query returns duplicate rows",
            "I keep getting a null pointer exception but I don't understand why",
            "I'm struggling to understand recursion, can someone help?",
            "Why does my program work in debug mode but not in release?",
            "I don't understand the difference between static and dynamic typing",
            "Confused about pass by value vs pass by reference in C++",
            "My code runs but gives wrong output for large inputs, not sure why",
            "I'm unable to understand the concept of closure in JavaScript",
            "Why does floating point arithmetic give unexpected results?",
            "I don't get why we need both stack and heap memory",
            "Struggling to understand how backtracking works in algorithms",
            "I'm confused about the difference between GET and POST methods",
            "Not able to understand how memory management works in Python",
            "I am unable to figure out why my sorting code fails for edge cases",
            "Confused about concurrency vs parallelism in computing",
            "Don't understand the difference between a class and an object",
            "I'm having trouble understanding how pointers to pointers work",
            "Why does my recursive function cause stack overflow?",
            "I don't get the concept of inheritance vs composition",
            "Struggling with understanding spanning tree protocol",
            "Not sure why my Django template is not rendering variables",
            "Confused about the difference between authentication and authorization",
            "I still can't understand how neural networks learn from data",
            "Why is my database query so slow with large datasets?",
            "I don't understand the difference between TCP handshake steps",
            "Confused about left join vs right join behavior",
            "Having trouble understanding how virtual functions work in C++",
            "Not clear about the difference between shallow copy and deep copy",
            "I still don't get how asymptotic analysis works",
            "My regex pattern matches wrong strings and I don't know why",
            "Confused about the concept of normalization in databases",
            "Why does changing one object affect another in Python?",
            "I'm unable to understand memoization in dynamic programming",
            "Not clear on how indexing improves database query performance",
            "Having difficulty understanding graph coloring algorithms",
            "Don't understand why my program has a memory leak",
            "I'm confused about how event loop works in JavaScript",
        ]

        # RESOURCE - Sharing materials, notes, links, references
        resources = [
            "Here are my notes on data structures and algorithms PDF",
            "Sharing the textbook solution manual for chapter 5",
            "Found a great YouTube playlist for learning Django framework",
            "MIT OCW lecture notes on operating systems are excellent",
            "Sharing my solved assignment solutions for discrete mathematics",
            "Check out this free course on Coursera about machine learning",
            "Here is the link to the GeeksforGeeks article on graph algorithms",
            "Uploaded my handwritten notes for computer networks unit 3",
            "This website has great practice problems for competitive programming",
            "Sharing the official Python documentation link for beginners",
            "Found a very good reference book PDF for database management",
            "Here are the previous year question papers for mid semester exam",
            "Sharing tutorial link for learning SQL with interactive exercises",
            "This GitHub repository has great project ideas for beginners",
            "Found a helpful article that explains design patterns simply",
            "Uploaded the slides from last week class on software engineering",
            "Here is a cheat sheet for all Linux terminal commands",
            "Sharing a great visualization tool for sorting algorithms",
            "This reference material covers everything about network security",
            "Found lecture recordings on NPTEL for computer architecture",
            "Sharing my compiled notes for the upcoming final exam",
            "Great resource for learning Git version control step by step",
            "Here are practice problems with detailed solutions for DSA",
            "Sharing the official React documentation for frontend developers",
            "Found an excellent course on Udemy for web development",
            "Uploaded formula sheet for numerical methods exam preparation",
            "This website explains all database normalization forms with examples",
            "Sharing link to interactive platform to learn SQL queries",
            "Here is a complete roadmap for learning cloud computing",
            "Found a great mock test series for competitive exam preparation",
            "Sharing my lab manual with all completed experiment write-ups",
            "Reference material for learning Docker and containerization",
            "Here are solved examples for digital logic design circuits",
            "Sharing a link to Stanford CS229 machine learning course materials",
            "Found a great cheat sheet for regular expressions syntax",
            "Uploaded my project report template for final year project",
            "This playlist covers entire computer organization in 20 videos",
            "Sharing a PDF guide on how to write effective technical reports",
            "Found great interview preparation resources for placement season",
            "Here are additional reference problems for graph theory concepts",
        ]

        # ANNOUNCEMENT - Class updates, schedule changes, deadline reminders
        announcements = [
            "Tomorrow class has been cancelled due to faculty meeting",
            "The assignment submission deadline has been extended to Friday",
            "Mid semester exam schedule has been posted on the notice board",
            "Lab session is rescheduled to Thursday this week",
            "Guest lecture on cloud computing tomorrow at 2 PM in hall A",
            "Reminder: Project presentation submissions are due next Monday",
            "The library will be closed this weekend for maintenance",
            "Extra class for DBMS will be held on Saturday morning",
            "Results for the last internal exam have been published",
            "Workshop on machine learning will be conducted next week",
            "Tomorrow is the last date to submit the practical file",
            "Faculty has announced that syllabus for unit 4 is reduced",
            "Placement drive by TCS is scheduled for next month",
            "Change in exam pattern: MCQ based questions will be included",
            "All students must complete their course registration by Friday",
            "Lab exam schedule has been updated please check notice board",
            "Holiday announced for Republic Day all classes are suspended",
            "The semester project topic allocation list has been published",
            "Viva voce for DBMS lab will be conducted next Tuesday",
            "New batch allocation for lab sessions has been posted",
            "Sports day event on Friday all afternoon classes are cancelled",
            "The compiler design teacher has changed textbook for reference",
            "Deadline extended for online assignment portal submission",
            "Tomorrow there will be a department meeting at 10 AM",
            "Remedial exam dates have been announced for failed students",
            "A coding competition will be held this Saturday in computer lab",
            "Notice: ID cards are mandatory for entering examination hall",
            "The college fest committee is looking for volunteers",
            "All pending library books must be returned by end of this month",
            "Class timing for Monday changed from 9AM to 10AM slot",
            "Faculty informed that next week lectures will be online",
            "Final exam timetable has been released please check portal",
            "Attendance shortage notice: minimum 75% required for exams",
            "New elective subject options have been added for next semester",
            "Student council elections will be held next Wednesday",
            "The department has organized an industrial visit next month",
            "Backlog exam registration window opens from tomorrow",
            "Group project team formation deadline is this Thursday",
            "The Wi-Fi password has been changed, new password is on notice board",
            "All practical exams will conclude before the theory exam period",
        ]

        for text in questions:
            dataset.append((text, 'Question'))
        for text in doubts:
            dataset.append((text, 'Doubt'))
        for text in resources:
            dataset.append((text, 'Resource'))
        for text in announcements:
            dataset.append((text, 'Announcement'))

        return dataset
