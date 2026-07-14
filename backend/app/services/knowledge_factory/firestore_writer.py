from google.cloud import firestore

from app.services.knowledge_factory.models import Curriculum


class FirestoreWriter:

    def __init__(self):

        self.db = firestore.Client()

    def save_curriculum(self, curriculum: Curriculum):

        curriculum_doc = self.db.collection(
            "curriculums"
        ).document(curriculum.curriculum_id)

        curriculum_doc.set(
            {
                "curriculum_id": curriculum.curriculum_id,
                "exam": curriculum.exam,
                "subject": curriculum.subject,
                "grade": curriculum.grade,
                "version": curriculum.version,
                "created_at": curriculum.created_at,
                "chapter_count": len(curriculum.chapters),
            }
        )

        chapters = curriculum_doc.collection("chapters")

        batch = self.db.batch()

        for chapter in curriculum.chapters:

            doc = chapters.document(chapter.id)

            batch.set(
                doc,
                {
                    "chapter_id": chapter.id,
                    "order": chapter.order,
                    "title": chapter.title,
                    "description": chapter.description,
                },
            )

        batch.commit()

        print(
            f"Imported {len(curriculum.chapters)} chapters "
            f"into {curriculum.curriculum_id}"
        )
        
    def get_curriculum(
        self,
        subject: str,
    ):
        """
        Load the latest curriculum
        for linking.
        """

        return self.curriculum_loader.load(
            subject,
        ) 