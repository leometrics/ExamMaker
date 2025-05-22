import sys
import os
import csv
import tempfile
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QCheckBox, QSpacerItem, QSizePolicy,
    QScrollArea, QFrame, QFileDialog, QMessageBox, QLineEdit,
    QDialog, QTextEdit)
from PyQt6.QtGui import (QDesktopServices, QShortcut, QKeySequence)
from PyQt6.QtCore import QUrl
import fitz
import atexit

temporary_preview_files = []

@atexit.register
def cleanup_temp_files():
    for path in temporary_preview_files:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Failed to delete temp file {path}: {e}")

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class ExamMakerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exam Maker")
        self.setFixedSize(900, 600)

        self.layout = QVBoxLayout(self)

        self.question_data = {}  # { topic: [{index, marks}] }
        self.question_rows = []

        self.init_component_selector()
        self.init_question_area()
        self.init_footer()

        QShortcut(QKeySequence(QKeySequence.StandardKey.Close), self, activated=self.close)


    def load_question_data(self, paper_name):
        if paper_name not in ["9709 Paper 3", "9231 Paper 3", "9231 Paper 4"]:
            self.question_data.clear()
            return

        folder = paper_name.replace(" ", "_")  # e.g., "Paper 3" → "Paper_3"
        csv_path = os.path.join(os.path.dirname(__file__), folder, "Categories.csv")
        if not os.path.exists(csv_path):
            print(f"CSV not found for {paper_name}. Expected at: {csv_path}")
            self.question_data.clear()
            return

        self.question_data.clear()
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic = row["Topic"]
                index = row["Question Index"]
                marks = int(row["Marks"])
                self.question_data.setdefault(topic, []).append({"index": index, "marks": marks})

    def init_component_selector(self):
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Select Paper Component:"))

        self.component_box = QComboBox()
        self.component_box.setFixedWidth(180)  # Optional: Keep it compact
        self.component_box.addItems(["(Select a Component)", "9709 Paper 3", "9231 Paper 3", "9231 Paper 4", "(Other Components Currently Unavailable)"])
        self.component_box.currentTextChanged.connect(self.on_component_selected)
        top_layout.addWidget(self.component_box)

        top_layout.addStretch()

        self.version_btn = QPushButton("ℹ️Version Info")
        self.version_btn.clicked.connect(self.show_version_info)
        top_layout.addWidget(self.version_btn)

        self.whatsnew_btn = QPushButton("🆕What's New")
        self.whatsnew_btn.clicked.connect(self.show_whats_new)
        top_layout.addWidget(self.whatsnew_btn)

        self.layout.addLayout(top_layout)

    def init_question_area(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_frame = QFrame()
        main_question_layout = QHBoxLayout(self.scroll_frame)
        self.scroll_layout = QVBoxLayout()
        main_question_layout.addLayout(self.scroll_layout)

        for _ in range(6):
            self.add_question_row()

        btn_layout = QHBoxLayout()
        self.add_question_btn = QPushButton("➕Add a Question")
        self.add_question_btn.clicked.connect(self.add_question_row)
        btn_layout.addWidget(self.add_question_btn)

        self.remove_question_btn = QPushButton("➖Remove Last Question")
        self.remove_question_btn.clicked.connect(self.remove_last_question_row)
        btn_layout.addWidget(self.remove_question_btn)

        self.random_btn = QPushButton("🎲Random Selection")
        self.random_btn.setEnabled(False)
        self.random_btn.clicked.connect(self.perform_random_selection)
        btn_layout.addWidget(self.random_btn)

        btn_layout.addSpacing(160)

        self.sort_button = QPushButton("⬆️Sort by Marks")
        self.sort_button.clicked.connect(self.sort_questions_by_marks)
        btn_layout.addWidget(self.sort_button)
        self.sort_button.setEnabled(False)

        btn_layout.addStretch()
        self.scroll_layout.addLayout(btn_layout)

        self.scroll_area.setWidget(self.scroll_frame)
        self.layout.addWidget(self.scroll_area)

    def add_question_row(self):
        container = QFrame()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        index = len(self.question_rows) + 1
        question_label = QLabel(f"Question {index}")
        question_label.setFixedWidth(80)
        row_layout.addWidget(question_label)

        topic_box = QComboBox()
        topic_box.addItem("(Select Topic)")
        topic_box.setFixedWidth(270)
        row_layout.addWidget(topic_box)

        question_box = QComboBox()
        question_box.addItem("(Select Question)")
        question_box.setFixedWidth(240)
        row_layout.addWidget(question_box)

        mark_label = QLabel("Marks: —")
        mark_label.setFixedWidth(100)
        row_layout.addWidget(mark_label)

        preview_button = QPushButton("🔍Preview")
        preview_button.setFixedWidth(80)
        row_layout.addWidget(preview_button)

        row_layout.addStretch()

        self.scroll_layout.insertWidget(len(self.question_rows), container)

        row = {
            "container": container,
            "topic_box": topic_box,
            "question_box": question_box,
            "mark_label": mark_label,
            "preview_button": preview_button
        }
        self.question_rows.append(row)

        topic_box.currentTextChanged.connect(lambda topic, idx=index - 1: self.update_question_list(idx))
        question_box.currentTextChanged.connect(lambda index_text, idx=index - 1: self.update_mark_display(idx))
        preview_button.clicked.connect(lambda _, idx=index - 1: self.preview_question(idx))

        if self.question_data:
            topics = sorted(self.question_data.keys())
            topic_box.addItems(topics)

        topic_box.setEnabled(True)
        question_box.setEnabled(False)
        preview_button.setEnabled(False)


    def remove_last_question_row(self):
        if len(self.question_rows) > 1:
            last = self.question_rows.pop()
            last["container"].setParent(None)
            self.update_total_score()

    def on_component_selected(self, paper_name):
        self.random_btn.setEnabled(paper_name in ["9709 Paper 3", "9231 Paper 3", "9231 Paper 4"])
        self.load_question_data(paper_name)
        topics = sorted(self.question_data.keys())

        for row in self.question_rows:
            row["topic_box"].setEnabled(True)

        for row in self.question_rows:
            row["topic_box"].clear()
            row["topic_box"].addItem("(Select Topic)")
            row["topic_box"].addItems(topics)
            row["question_box"].clear()
            row["question_box"].addItem("(Select Question)")
            row["mark_label"].setText("Marks: —")


    def update_question_list(self, idx):
        if idx >= len(self.question_rows):
            return
        row = self.question_rows[idx]
        topic = row["topic_box"].currentText()
        if topic in self.question_data:
            row["question_box"].setEnabled(True)
        else:
            row["question_box"].setEnabled(False)

        row["question_box"].clear()
        row["question_box"].addItem("(Select Question)")
        if topic in self.question_data:
            for item in self.question_data[topic]:
                row["question_box"].addItem(item["index"])
        row["mark_label"].setText("Marks: —")
        self.update_total_score()

    def update_mark_display(self, idx):
        if idx >= len(self.question_rows):
            return
        row = self.question_rows[idx]
        topic = row["topic_box"].currentText()
        index = row["question_box"].currentText()
        if topic in self.question_data:
            for item in self.question_data[topic]:
                if item["index"] == index:
                    row["mark_label"].setText(f"Marks: {item['marks']}")
                    break
        if index and index != "(Select Question)":
            row["preview_button"].setEnabled(True)
        else:
            row["preview_button"].setEnabled(False)
        self.update_footer_buttons_state()
        self.update_total_score()

    def update_footer_buttons_state(self):
        any_selected = any(
            row["question_box"].currentText() != "(Select Question)"
            for row in self.question_rows
        )
        self.preview_btn.setEnabled(any_selected)
        self.save_btn.setEnabled(any_selected)
        self.copy_btn.setEnabled(any_selected)
        self.sort_button.setEnabled(any_selected)

    def update_total_score(self):
        total = 0
        for row in self.question_rows:
            label = row["mark_label"].text()
            if label.startswith("Marks: "):
                try:
                    total += int(label.replace("Marks: ", ""))
                except ValueError:
                    continue
        self.total_score_label.setText(f"[Total Score: {total}]")

    def preview_question(self, idx):
        if idx >= len(self.question_rows):
            return
        row = self.question_rows[idx]
        index = row["question_box"].currentText()
        if index and index != "(Select Question)":
            folder = self.component_box.currentText().replace(" ", "_")
            path = os.path.join(os.path.dirname(__file__), folder, index + ".pdf")
            if os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def perform_random_selection(self):
        paper = self.component_box.currentText()
        if paper not in ["9709 Paper 3", "9231 Paper 3", "9231 Paper 4"]:
            QMessageBox.warning(self, "Unavailable", "Random selection is only available for Paper 3 and 4.")
            return

        if paper == "9231 Paper 4":
            selected = self.random_select_9231_p4()
            expected_count = 6
        elif paper == "9231 Paper 3":
            selected = self.random_select_9231_p3()
            expected_count = 7
        elif paper == "9709 Paper 3":
            selected = self.random_select_9709_p3()
            expected_count = len(selected) if selected else 10
        else:
            selected = None

        if not selected:
            QMessageBox.warning(self, "Selection Failed", "Could not generate a valid combination.")
            return

        self.reset_question_rows(expected_count)
        for i, row in enumerate(self.question_rows):
            if i < len(selected):
                topic, q = selected[i]
                row["topic_box"].setEnabled(True)
                row["question_box"].setEnabled(True)
                row["preview_button"].setEnabled(True)
                row["topic_box"].setCurrentText(topic)
                self.update_question_list(i)
                row["question_box"].setCurrentText(q["index"])
                self.update_mark_display(i)
            else:
                row["topic_box"].setCurrentIndex(0)
                row["question_box"].setCurrentIndex(0)
                row["mark_label"].setText("Marks: —")
        self.update_total_score()

    def random_select_9231_p4(self):
        target = 50
        groups = {
            "chi": ["Chi-square Test (contingency table)", "Chi-square Test (goodness of fit)"],
            "crv": ["Continuous Random Variable"],
            "pgf": ["Probability Generating Function"],
            "twci": [
                "t-Test (single sample)", "t-Test (pooled sample)", "t-Test (paired sample)",
                "Confidence Interval", "Wilcoxon Test (signed-rank)", "Wilcoxon Test (rank-sum)"
            ]
        }

        for _ in range(1000):
            selected = []
            used_topics = set()
            below_6 = 0

            def choose(topics):
                pool = [(t, q) for t in topics for q in self.question_data.get(t, [])]
                return random.choice(pool) if pool else None

            for key in ["chi", "crv", "pgf"]:
                pick = choose(groups[key])
                if not pick:
                    break
                topic, q = pick
                selected.append((topic, q))
                used_topics.add(topic)
                if q["marks"] < 6:
                    below_6 += 1

            pick4 = choose(groups["twci"])
            if not pick4:
                continue
            topic4, q4 = pick4
            selected.append((topic4, q4))
            used_topics.add(topic4)
            if q4["marks"] < 6:
                below_6 += 1

            current_total = sum(q["marks"] for _, q in selected)
            if current_total > target - 10 or below_6 > 1:
                continue

            remaining_twci = [t for t in groups["twci"] if t not in used_topics]
            fifth_candidates = [(t, q) for t in remaining_twci for q in self.question_data.get(t, []) if
                                current_total + q["marks"] < target]
            if not fifth_candidates:
                continue
            topic5, q5 = random.choice(fifth_candidates)
            selected.append((topic5, q5))
            used_topics.add(topic5)
            current_total += q5["marks"]
            if q5["marks"] < 6:
                below_6 += 1
            if below_6 > 1:
                continue

            final_candidates = [(t, q) for t in self.question_data if t not in used_topics for q in
                                self.question_data[t] if current_total + q["marks"] == target]
            if not final_candidates:
                continue
            topic6, q6 = random.choice(final_candidates)
            selected.append((topic6, q6))

            if len(selected) == 6 and sum(q["marks"] for _, q in selected) == target:
                return selected  # ✅ return here
        return None  # ❌ if all attempts fail

    def random_select_9231_p3(self):
        target = 50
        core_topics = [
            "Projectile Motion", "Center of Mass", "Circular Motion",
            "Hooke's Law", "General Straight Motion", "Momentum"
        ]
        extra_pool = ["Equilibrium of Rigid Body", "Circular Motion"]

        for _ in range(1000):
            selected = []
            used = set()
            total = 0
            below_6 = 0

            for topic in core_topics:
                questions = self.question_data.get(topic, [])
                if not questions:
                    break
                q = random.choice(questions)
                selected.append((topic, q))
                used.add(topic)
                total += q["marks"]
                if q["marks"] < 6:
                    below_6 += 1

            if len(selected) < 6 or total > 44:
                continue

            candidates = []
            for topic in extra_pool:
                for q in self.question_data.get(topic, []):
                    if total + q["marks"] == target:
                        new_below_6 = below_6 + (1 if q["marks"] < 6 else 0)
                        if new_below_6 <= 1:
                            candidates.append((topic, q))

            if not candidates:
                continue

            selected.append(random.choice(candidates))
            return selected
        return None

    def random_select_9709_p3(self):
        target = 75
        must_have_once = [
            "Modulus Inequality", "Binomial Expansion", "Numerical Method of Solving Equation",
            "Trigonometric Identities", "Vectors", "Differential Equations", "Integration by Parts"
        ]
        must_have_at_least = ["Complex Numbers"]
        one_of_sets = [
            ["Factor and Remainder Theorems", "Integration by Substitution", "Integration by Partial Fraction"],
            ["Exponential Equation and Inequality", "Linearization Using Logarithm", "Logarithmic Equation"],
            ["Parametric Differentiation", "Implicit Differentiation"]
        ]
        filler_pool = ["Auxiliary Angle Method", "Complex Numbers", "Product Rule and Quotient Rule"]

        for _ in range(1000):
            selected = []
            used_topics = set()
            total = 0

            def pick_unique(topic_list):
                topic = random.choice(topic_list)
                questions = [q for q in self.question_data.get(topic, []) if topic not in used_topics]
                return (topic, random.choice(questions)) if questions else None

            # Add required topics
            for topic in must_have_once:
                q_list = self.question_data.get(topic, [])
                if not q_list:
                    break
                q = random.choice(q_list)
                selected.append((topic, q))
                used_topics.add(topic)
                total += q["marks"]

            # Add "at least once" topic
            q_list = self.question_data.get("Complex Numbers", [])
            if q_list and "Complex Numbers" not in used_topics:
                q = random.choice(q_list)
                selected.append(("Complex Numbers", q))
                used_topics.add("Complex Numbers")
                total += q["marks"]

            # Add one from each option group
            for group in one_of_sets:
                pick = pick_unique(group)
                if pick:
                    topic, q = pick
                    selected.append((topic, q))
                    used_topics.add(topic)
                    total += q["marks"]

            # Fill up remaining slots
            fillers = [t for t in filler_pool if t not in used_topics]
            for topic in fillers:
                for q in self.question_data.get(topic, []):
                    if topic in used_topics:
                        continue
                    if len(selected) >= 11:
                        break
                    if total + q["marks"] <= target:
                        selected.append((topic, q))
                        used_topics.add(topic)
                        total += q["marks"]
                    if total == target and 10 <= len(selected) <= 11:
                        return selected

            if total == target and 10 <= len(selected) <= 11:
                return selected

        return None

    def init_footer(self):
        footer_layout1 = QHBoxLayout()
        self.total_score_label = QLabel("[Total Score: 0]")
        footer_layout1.addWidget(self.total_score_label)

        self.show_index_checkbox = QCheckBox("Show Question Indices")
        footer_layout1.addWidget(self.show_index_checkbox)

        self.copy_btn = QPushButton("📋Copy Question Indices")
        self.copy_btn.setEnabled(False)  # Initially disabled
        self.copy_btn.clicked.connect(self.copy_question_indices)
        footer_layout1.addWidget(self.copy_btn)

        footer_layout1.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        footer_layout1.addWidget(QLabel("Question Paper:"))

        self.preview_btn = QPushButton("🔍Preview")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self.preview_paper)
        footer_layout1.addWidget(self.preview_btn)

        self.save_btn = QPushButton("💾Save")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_paper)
        footer_layout1.addWidget(self.save_btn)

        footer_layout2 = QHBoxLayout()
        self.reset_btn = QPushButton("🔄Reset")
        self.reset_btn.clicked.connect(self.reset_all)
        footer_layout2.addWidget(self.reset_btn)

        footer_layout2.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        footer_layout2.addWidget(QLabel("Mark Scheme:"))

        self.preview_ms_btn = QPushButton("🔍Preview")
        self.preview_ms_btn.setEnabled(False)
        footer_layout2.addWidget(self.preview_ms_btn)

        self.save_ms_btn = QPushButton("💾Save")
        self.save_ms_btn.setEnabled(False)
        footer_layout2.addWidget(self.save_ms_btn)

        self.layout.addLayout(footer_layout1)
        self.layout.addLayout(footer_layout2)

    def copy_question_indices(self):
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()

        indices = [
            row["question_box"].currentText()
            for row in self.question_rows
            if row["question_box"].currentText() not in ["", "(Select Question)"]
        ]
        if not indices:
            QMessageBox.information(self, "No Indices", "No question indices selected to copy.")
            return

        clipboard.setText("\n".join(indices))
        QMessageBox.information(self, "Copied", "Question indices copied to clipboard.")

    def reset_all(self):
        self.component_box.setCurrentIndex(0)
        for row in self.question_rows:
            row["container"].setParent(None)
        self.question_rows.clear()
        for _ in range(6):
            self.add_question_row()
        self.show_index_checkbox.setChecked(False)
        self.total_score_label.setText("[Total Score: 0]")
        self.preview_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        for row in self.question_rows:
            row["topic_box"].setEnabled(True)
            row["question_box"].setEnabled(False)
            row["preview_button"].setEnabled(False)

    def sort_questions_by_marks(self):
        selected = []
        for row in self.question_rows:
            topic = row["topic_box"].currentText()
            index = row["question_box"].currentText()
            if topic in self.question_data and index != "(Select Question)":
                for item in self.question_data[topic]:
                    if item["index"] == index:
                        selected.append((topic, index, item["marks"]))
                        break

        selected.sort(key=lambda x: x[2])

        for i, row in enumerate(self.question_rows):
            if i < len(selected):
                topic, index, marks = selected[i]
                row["topic_box"].setCurrentText(topic)
                self.update_question_list(i)
                row["question_box"].setCurrentText(index)
                row["mark_label"].setText(f"Marks: {marks}")
            else:
                row["topic_box"].setCurrentIndex(0)
                row["question_box"].setCurrentIndex(0)
                row["mark_label"].setText("Marks: —")

        self.update_total_score()

    def collect_selected_questions(self):
        questions = []
        for row in self.question_rows:
            topic = row["topic_box"].currentText()
            index = row["question_box"].currentText()
            if topic in self.question_data and index != "(Select Question)":
                for item in self.question_data[topic]:
                    if item["index"] == index:
                        questions.append({"index": index, "marks": item["marks"]})
                        break
        return questions

    def reset_question_rows(self, count=6):
        for row in self.question_rows:
            row["container"].setParent(None)
        self.question_rows.clear()
        for _ in range(count):
            self.add_question_row()

    def preview_paper(self):
        questions = self.collect_selected_questions()
        if not questions:
            QMessageBox.warning(self, "No Questions", "Please select at least one question.")
            return

        folder = self.component_box.currentText().replace(" ", "_")
        base_path = os.path.dirname(__file__)
        pdf_paths = [os.path.join(base_path, folder, q["index"] + ".pdf") for q in questions]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            output_path = temp_pdf.name
            # Add to cleanup list
            temporary_preview_files.append(output_path)

        try:
            self.generate_merged_pdf(pdf_paths, output_path, questions)
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{e}")

    def save_paper(self):
        questions = self.collect_selected_questions()
        if not questions:
            QMessageBox.warning(self, "No Questions", "Please select at least one question.")
            return

        folder = self.component_box.currentText().replace(" ", "_")
        base_path = os.path.dirname(__file__)
        pdf_paths = [os.path.join(base_path, folder, q["index"] + ".pdf") for q in questions]

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Paper As", "paper.pdf", "PDF Files (*.pdf)")
        if not save_path:
            return

        try:
            self.generate_merged_pdf(pdf_paths, save_path, questions)
            QMessageBox.information(self, "Success", f"Paper saved to: {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save PDF:\n{e}")

    def generate_merged_pdf(self, pdf_paths, output_path, questions):
        doc = fitz.open()
        show_indices = self.show_index_checkbox.isChecked()

        for i, (pdf_path, q) in enumerate(zip(pdf_paths, questions), start=1):
            label = f"Question {i}"
            if show_indices:
                label += f": {q['index']}"

            src = fitz.open(pdf_path)

            for page_num in range(len(src)):
                new_page = doc.new_page(width=595, height=842)

                new_page.show_pdf_page(new_page.rect, src, pno=page_num)

                new_page.insert_text(
                    (50, 50),
                    label,
                    fontsize=12,
                    fontname="Times-Roman",  # or "Courier"
                    color=(0, 0, 0)
                )

            src.close()

        doc.save(output_path)
        doc.close()

    def show_version_info(self):
        message = (
            "📄 Exam Maker v1.2\n"
            "©  CC BY-NC-SA 4.0\n"
            "\n"
            "🛠️ Last Updated: 2025-05-21\n"
            "\n"
            "Developed by: Leo Lin @ OTIA\n"
            "🐞 For bug reports or suggestions, please contact:\n"
            "📧 dlin07@icloud.com\n"
            "\n"
            "This tool is designed for assembling CAIE-style exam papers quickly.\n"
            "Supports random selection, preview, and export.\n"
            "Some components are currently unavailable."
        )

        box = QMessageBox(self)
        box.setWindowTitle("Version Info")
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Trick to resize
        box.setStyleSheet("QLabel{min-width: 500px; min-height: 300px;}")

        box.exec()

    def show_whats_new(self):
        patch_dir = get_resource_path("patch_log")
        entries = sorted([
            f for f in os.listdir(patch_dir) if f.endswith(".txt")
        ], reverse=True)

        if not entries:
            QMessageBox.information(self, "What's New", "No update logs found.")
            return

        latest_file = entries[0]
        latest_path = os.path.join(patch_dir, latest_file)
        with open(latest_path, "r") as f:
            latest_content = f.read().strip()

        # Create a custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("What's New")
        layout = QVBoxLayout()

        # Show the latest update summary
        layout.addWidget(QLabel(f"<b>Latest Update: {latest_file[:-4]}</b>"))
        layout.addWidget(QLabel(latest_content))

        # Dropdown to view history
        combo = QComboBox()
        combo.addItems([f[:-4] for f in entries])
        layout.addWidget(QLabel("Browse Update History:"))
        layout.addWidget(combo)

        view_btn = QPushButton("View")
        layout.addWidget(view_btn)

        text_view = QTextEdit()
        text_view.setReadOnly(True)
        layout.addWidget(text_view)

        def load_selected_log():
            date = combo.currentText()
            path = os.path.join(patch_dir, f"{date}.txt")
            if os.path.exists(path):
                with open(path, "r") as f:
                    text_view.setText(f.read())

        view_btn.clicked.connect(load_selected_log)
        dialog.setLayout(layout)
        dialog.resize(500, 400)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExamMakerUI()
    window.show()
    sys.exit(app.exec())
