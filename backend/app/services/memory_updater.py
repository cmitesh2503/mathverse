from app.services.memory_extractor import (
    MemoryExtractor
)


class MemoryUpdater:

    def __init__(self):

        self.extractor = MemoryExtractor()

    def update(
        self,
        session,
        student_message: str,
        teacher_response: str
    ):

        # Always remember conversation

        session.memory.remember_question(
            student_message
        )

        session.memory.remember_answer(
            teacher_response
        )

        # Ask AI to summarize the teaching memory

        memory = self.extractor.extract(
            student_message,
            teacher_response
        )
        
        print("=" * 60)
        print("AI MEMORY")
        print(memory)
        print("=" * 60)

        # ----------------------------
        # Current Topic
        # ----------------------------

        topic = memory.get(
            "current_topic",
            ""
        )

        if topic:

            session.memory.current_topic = topic

            session.memory.add_topic(
                topic
            )

        # ----------------------------
        # Explained Topics
        # ----------------------------

        for topic in memory.get(
            "explained_topics",
            []
        ):

            session.memory.add_topic(
                topic
            )

        # ----------------------------
        # Misconceptions
        # ----------------------------

        for misconception in memory.get(
            "misconceptions",
            []
        ):

            session.memory.add_misconception(
                misconception
            )

        
        
        for method in memory.get(
            "teaching_methods_used",
            []
        ):

            session.memory.add_teaching_method(
                method
            )


        session.memory.set_learning_status(

            memory.get(
                "learning_status",
                ""
            )

        )
        session.update()