import sys
import os
os.environ["PATH"] += os.pathsep + "/Library/TeX/texbin"
import csv
import tempfile
import subprocess
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QCheckBox, QSpacerItem, QSizePolicy,
    QScrollArea, QFrame, QFileDialog, QMessageBox, QLineEdit
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
import shutil


class ExamMakerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exam Maker for Further Maths(9231)")
        self.setFixedSize(900, 600)

        self.layout = QVBoxLayout(self)

        self.question_data = {}  # { topic: [{index, marks}] }
        self.question_rows = []

        self.init_component_selector()
        self.init_question_area()
        self.init_footer()

    def load_question_data(self, paper_name):
        if paper_name not in ["Paper 1", "Paper 2", "Paper 3", "Paper 4"]:
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
        self.component_box.addItems(["(Select a Component)", "Paper 1", "Paper 2", "Paper 3", "Paper 4"])
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

        topic_box.setEnabled(False)
        question_box.setEnabled(False)
        preview_button.setEnabled(False)


    def remove_last_question_row(self):
        if len(self.question_rows) > 1:
            last = self.question_rows.pop()
            last["container"].setParent(None)
            self.update_total_score()

    def on_component_selected(self, paper_name):
        self.random_btn.setEnabled(paper_name in ["Paper 3", "Paper 4"])
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
        if paper not in ["Paper 3", "Paper 4"]:
            QMessageBox.warning(self, "Unavailable", "Random selection is only available for Paper 3 and 4.")
            return

        if paper == "Paper 4":
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

                # Pick one from chi, crv, pgf
                for key in ["chi", "crv", "pgf"]:
                    pick = choose(groups[key])
                    if not pick:
                        break
                    topic, q = pick
                    selected.append((topic, q))
                    used_topics.add(topic)
                    if q["marks"] < 6:
                        below_6 += 1

                # Pick one from twci
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

                # Fifth question: from remaining twci topics
                remaining_twci = [t for t in groups["twci"] if t not in used_topics]
                fifth_candidates = []
                for t in remaining_twci:
                    for q in self.question_data.get(t, []):
                        if current_total + q["marks"] < target:
                            fifth_candidates.append((t, q))
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

                # Sixth question: from any unused topic to complete target
                final_candidates = []
                for t in self.question_data:
                    if t not in used_topics:
                        for q in self.question_data[t]:
                            if current_total + q["marks"] == target:
                                final_candidates.append((t, q))
                if not final_candidates:
                    continue
                topic6, q6 = random.choice(final_candidates)
                selected.append((topic6, q6))

                if len(selected) == 6 and sum(q["marks"] for _, q in selected) == target:
                    break
            else:
                QMessageBox.warning(self, "Selection Failed", "Could not generate a valid combination.")
                return

            self.reset_question_rows(6)
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

        elif paper == "Paper 3":
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
                for topic in core_topics:
                    questions = self.question_data.get(topic, [])
                    if not questions:
                        break
                    q = random.choice(questions)
                    selected.append((topic, q))
                    used.add(topic)
                    total += q["marks"]

                if len(selected) < 6 or total > 44:
                    continue

                candidates = []
                for topic in extra_pool:
                    if topic in used:
                        continue
                    for q in self.question_data.get(topic, []):
                        if total + q["marks"] == target:
                            candidates.append((topic, q))

                if not candidates:
                    continue

                selected.append(random.choice(candidates))
                break
            else:
                QMessageBox.warning(self, "Selection Failed", "Could not generate a valid combination.")
                return

            self.reset_question_rows(7)
            for i, (topic, q) in enumerate(selected):
                row = self.question_rows[i]
                row["topic_box"].setEnabled(True)
                row["question_box"].setEnabled(True)
                row["preview_button"].setEnabled(True)
                row["topic_box"].setCurrentText(topic)
                self.update_question_list(i)
                row["question_box"].setCurrentText(q["index"])
                self.update_mark_display(i)
            self.update_total_score()

    def init_footer(self):
        footer_layout1 = QHBoxLayout()
        self.total_score_label = QLabel("Total Score: 0")
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

        self.latex_status_label = QLabel()
        footer_layout2.addWidget(self.latex_status_label)

        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self.show_latex_help)
        footer_layout2.addWidget(self.help_btn)

        if self.is_latex_installed():
            self.latex_status_label.setText("✅LaTeX installed")
            self.help_btn.setEnabled(False)
        else:
            self.latex_status_label.setText("❌LaTeX Not Detected")
            self.help_btn.setEnabled(True)

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
        self.total_score_label.setText("Total Score: 0")
        self.preview_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        for row in self.question_rows:
            row["topic_box"].setEnabled(False)
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

    def generate_latex(self, questions, show_indices):
        lines = [
            "\\documentclass[a4paper,12pt]{article}",
            "\\usepackage{graphicx}",
            "\\usepackage{pdfpages}",
            "\\usepackage{geometry}",
            "\\usepackage{eso-pic}",
            "\\usepackage{fancyhdr}",
            "\\geometry{margin=1in}",
            "\\pagestyle{empty}",
            "",
            "\\begin{document}"
        ]

        for i, q in enumerate(questions, start=1):
            label = f"Question {i}"
            if show_indices:
                escaped_index = q['index'].replace('_', r'\_')
                label += f": {escaped_index}"

            lines.append(
                "\\includepdf[pages=-, pagecommand={"
                "\\thispagestyle{empty}"
                "\\AddToShipoutPictureFG*{"
                "\\AtPageUpperLeft{\\hspace{1cm} \\raisebox{-2cm}{\\textbf{" + label + "}}}"
                                                                                       "}"
                                                                                       "}]{" + q['index'] + ".pdf}"
            )

        lines.append("\\end{document}")
        return "\n".join(lines)


    def compile_latex(self, tex_code, output_pdf_path):
        with tempfile.TemporaryDirectory() as tempdir:
            tex_file = os.path.join(tempdir, "output.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(tex_code)

            # Copy required PDFs into temp directory
            folder = self.component_box.currentText().replace(" ", "_")
            base_path = os.path.dirname(__file__)
            for row in self.collect_selected_questions():
                pdf_name = f"{row['index']}.pdf"
                src_pdf = os.path.join(base_path, folder, pdf_name)
                dst_pdf = os.path.join(tempdir, pdf_name)
                if not os.path.exists(src_pdf):
                    print(f"Missing file: {src_pdf}")
                    return False
                shutil.copyfile(src_pdf, dst_pdf)

            # Ensure pdflatex is available
            if not shutil.which("pdflatex"):
                print("pdflatex not found in system PATH.")
                return False

            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_file],
                cwd=tempdir, capture_output=True
            )

            pdf_file = os.path.join(tempdir, "output.pdf")
            if result.returncode == 0 and os.path.exists(pdf_file):
                os.replace(pdf_file, output_pdf_path)
                return True
            else:
                print("pdflatex error output:")
                print(result.stdout.decode())
                print(result.stderr.decode())
                return False

    def preview_paper(self):
        questions = self.collect_selected_questions()
        if not questions:
            QMessageBox.warning(self, "No Questions", "Please select at least one question.")
            return

        show_indices = self.show_index_checkbox.isChecked()
        tex_code = self.generate_latex(questions, show_indices)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            output_path = temp_pdf.name

        if self.compile_latex(tex_code, output_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
        else:
            QMessageBox.critical(self, "Error", "Failed to compile LaTeX.")

    def save_paper(self):
        questions = self.collect_selected_questions()
        if not questions:
            QMessageBox.warning(self, "No Questions", "Please select at least one question.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Paper As", "paper.pdf", "PDF Files (*.pdf)")
        if not save_path:
            return

        show_indices = self.show_index_checkbox.isChecked()
        tex_code = self.generate_latex(questions, show_indices)

        if self.compile_latex(tex_code, save_path):
            QMessageBox.information(self, "Success", f"Paper saved to: {save_path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to compile and save LaTeX.")

    def is_latex_installed(self):
        import shutil
        return shutil.which("pdflatex") is not None

    def show_latex_help(self):
        help_text = (
            "LaTeX is required to generate the PDF paper.\n\n"
            "To install LaTeX:\n\n"
            "• On macOS: Install MacTeX from https://tug.org/mactex/\n"
            "• On Windows: Install MiKTeX from https://miktex.org/download\n\n"
            "After installation, make sure `pdflatex` is added to your system PATH."
        )
        QMessageBox.information(self, "Install LaTeX", help_text)

    def show_version_info(self):
        message = (
            "📄 Exam Maker v1.1\n"
            "©  CC BY-NC-SA 4.0\n"
            "\n"
            "🛠️ Last Updated: 2025-05-19\n"
            "\n"
            "Developed by: Leo Lin @ OTIA\n"
            "🐞 For bug reports or suggestions, please contact:\n"
            "📧 dlin@icloud.com\n"
            "\n"
            "This tool is designed for assembling CAIE-style exam papers quickly.\n"
            "Supports Paper 3 and Paper 4 with random selection, preview, and LaTeX export.\n"
            "Paper 1 and Paper 2 currently unavailable"
        )

        box = QMessageBox(self)
        box.setWindowTitle("Version Info")
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Trick to resize
        box.setStyleSheet("QLabel{min-width: 400px; min-height: 200px;}")

        box.exec()

    def show_whats_new(self):
        updates = (
            "🔧 What's New (May 19 2025 Update):\n\n"
            "- Refined Random Selection for Paper 3.\n"
            "- Added 'Copy Question Indices' feature.\n"
            "- Added 'LaTeX Installation Check' feature.\n"
            "- Improved UI layout and button availability control.\n"
            "- Mark Scheme buttons added (Function temporarily unavailable).\n"
            "- Numerous bug fixes and usability improvements."
        )

        box = QMessageBox(self)
        box.setWindowTitle("Version Info")
        box.setText(updates)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Trick to resize
        box.setStyleSheet("QLabel{min-width: 400px; min-height: 200px;}")

        box.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExamMakerUI()
    window.show()
    sys.exit(app.exec())
