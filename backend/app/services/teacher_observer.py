from app.models.teacher_observation import (
    TeacherObservation
)


class TeacherObserver:

    def observe(
        self,
        session,
        student_message: str
    ) -> TeacherObservation:

        message = student_message.lower()

        observation = TeacherObservation()

        # ---------------------------------------
        # Current message analysis
        # ---------------------------------------

        if "don't understand" in message:
            observation.confused = True

        if "do not understand" in message:
            observation.confused = True

        if "confused" in message:
            observation.confused = True

        if "example" in message:
            observation.needs_example = True

        if "hint" in message:
            observation.needs_hint = True

        if "diagram" in message:
            observation.needs_whiteboard = True

        if "draw" in message:
            observation.needs_whiteboard = True

        if "whiteboard" in message:
            observation.needs_whiteboard = True

        if "why" in message:
            observation.asks_why = True

        if "how" in message:
            observation.asks_how = True

        if "understand" in message and not observation.confused:
            observation.understood = True

        # =======================================
        # Phase 3 : History-aware observation
        # =======================================

        # Student is repeatedly asking follow-up questions

        if session.followup_questions >= 3:
            observation.confused = True

        # Student already requested examples before

        example_requests = sum(
            1
            for q in session.memory.student_questions
            if "example" in q.lower()
        )

        if example_requests >= 2:
            observation.needs_example = True

        # Student already requested hints before

        hint_requests = sum(
            1
            for q in session.memory.student_questions
            if "hint" in q.lower()
        )

        if hint_requests >= 2:
            observation.needs_hint = True

        # If Hint was already used but student still says confused,
        # escalate to Example.

        methods = [
            method.lower()
            for method in session.memory.teaching_methods_used
        ]

        if (
            observation.confused
            and "hint" in methods
        ):
            observation.needs_example = True

        # If Example was already used and student is still confused,
        # escalate to Whiteboard.

        if (
            observation.confused
            and "example" in methods
        ):
            observation.needs_whiteboard = True

        return observation