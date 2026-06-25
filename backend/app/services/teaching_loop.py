from enum import Enum


class TeachingState(str, Enum):

    EXPLAIN = "explain"

    CHECK_UNDERSTANDING = "check_understanding"

    GIVE_HINT = "give_hint"

    ASK_PRACTICE = "ask_practice"

    ENCOURAGE = "encourage"

    COMPLETE = "complete"


class TeachingLoop:

    """
    Controls how the teacher behaves.

    This class NEVER calls Gemini.

    It only decides what should happen next.

    """

    def __init__(self):

        self.state = TeachingState.EXPLAIN

    def next_step(
        self,
        student_message: str
    ) -> TeachingState:

        message = student_message.lower()

        if any(
            word in message
            for word in [
                "don't understand",
                "dont understand",
                "confused",
                "why",
                "how"
            ]
        ):

            return TeachingState.EXPLAIN

        if any(
            word in message
            for word in [
                "ok",
                "understood",
                "got it",
                "yes"
            ]
        ):

            return TeachingState.CHECK_UNDERSTANDING

        if any(
            word in message
            for word in [
                "hint"
            ]
        ):

            return TeachingState.GIVE_HINT

        return TeachingState.EXPLAIN