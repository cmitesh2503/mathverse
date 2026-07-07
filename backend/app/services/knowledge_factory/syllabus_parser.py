import re
from typing import List

from app.services.knowledge_factory.models import Curriculum, Chapter


class SyllabusParser:

    UNIT_PATTERN = re.compile(
        r"##\s*(?:MATHEMATICS\s*)?UNIT\s*([0-9]+)\s*:\s*(.+?)(?=\n\n)(.*?)(?=\n##\s*(?:MATHEMATICS\s*)?UNIT\s*[0-9]+:|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    def parse(self, azure_json: dict) -> Curriculum:

        analyze_result = azure_json.get("analyzeResult", {})
        content = analyze_result.get("content", "")

        if not content:
            raise ValueError("Azure Layout JSON does not contain analyzeResult.content")

        exam = self._extract_exam(content)
        subject = self._extract_subject(content)
        grade = self._extract_grade(content)
        version = self._extract_year(content)

        chapters = self._extract_units(content)

        curriculum_id = (
            f"{exam.lower().replace(' ', '-')}-"
            f"{version}-"
            f"{subject.lower()}"
        )

        return Curriculum(
            curriculum_id=curriculum_id,
            exam=exam,
            subject=subject,
            grade=grade,
            version=version,
            chapters=chapters,
        )

    def _extract_exam(self, text: str) -> str:

        if "JEE (Main)" in text or "JEE Main" in text:
            return "JEE Main"

        return "Unknown"

    def _extract_subject(self, text: str) -> str:

        if "MATHEMATICS" in text.upper():
            return "Mathematics"

        if "PHYSICS" in text.upper():
            return "Physics"

        if "CHEMISTRY" in text.upper():
            return "Chemistry"

        return "Unknown"

    def _extract_grade(self, text: str) -> str:

        match = re.search(r"B\.E\./B\.Tech\.", text)

        if match:
            return match.group()

        return ""

    def _extract_year(self, text: str) -> str:

        match = re.search(r"20\d{2}", text)

        if match:
            return match.group()

        return "Unknown"

    def _extract_units(self, text: str) -> List[Chapter]:

        chapters: List[Chapter] = []

        matches = list(self.UNIT_PATTERN.finditer(text))

        for match in matches:

            order = int(match.group(1))

            title = self._clean(match.group(2))

            description = self._clean(match.group(3))

            chapters.append(
                Chapter(
                    id=f"chapter-{order:03d}",
                    order=order,
                    title=title,
                    description=description,
                )
            )

        return chapters

    @staticmethod
    def _clean(text: str) -> str:

        text = text.replace("<!-- PageBreak -->", "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()