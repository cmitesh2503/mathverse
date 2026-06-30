from dataclasses import dataclass


@dataclass
class TeacherObservation:

    confused: bool = False

    needs_example: bool = False

    needs_hint: bool = False

    needs_whiteboard: bool = False

    understood: bool = False

    asks_why: bool = False

    asks_how: bool = False