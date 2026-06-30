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

        return observation