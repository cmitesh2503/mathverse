from app.services.teacher_reasoning import TeacherReasoning


class TeacherReasoner:
    """
    TeacherReasoner represents the THINK stage of the
    teaching lifecycle.

        Observe
            ↓
        Think      <-- This class
            ↓
        Choose Strategy
            ↓
        Teach

    Phase 2
    -------
    Uses deterministic Python rules.

    Phase 4
    -------
    May internally use Gemini.

    The public interface MUST remain unchanged.
    """

    def reason(
        self,
        context,
        session,
        memory,
        observation,
    ) -> TeacherReasoning:

        reasoning = TeacherReasoning()

        # ----------------------------
        # Learning Stage
        # ----------------------------

        if observation.confused:

            reasoning.learning_stage = "STRUGGLING"

            reasoning.confidence = 0.90

        elif observation.understood:

            reasoning.learning_stage = "UNDERSTANDING"

            reasoning.confidence = 0.90

        else:

            reasoning.learning_stage = "LEARNING"

            reasoning.confidence = 0.60

        # ----------------------------
        # Student Goal
        # ----------------------------

        reasoning.student_goal = (
            "Understand the uploaded JEE question"
        )

        # ----------------------------
        # Teaching Objective
        # ----------------------------

        if observation.asks_why:

            reasoning.next_objective = (
                "Explain the underlying concept"
            )

            reasoning.recommended_depth = "DETAILED"

        elif observation.needs_example:

            reasoning.next_objective = (
                "Teach using a simple worked example"
            )

            reasoning.recommended_depth = "MEDIUM"

        elif observation.needs_hint:

            reasoning.next_objective = (
                "Guide the student with a hint"
            )

            reasoning.recommended_depth = "LIGHT"

        elif observation.needs_whiteboard:

            reasoning.next_objective = (
                "Explain using whiteboard steps"
            )

            reasoning.recommended_depth = "DETAILED"

        elif observation.understood:

            reasoning.next_objective = (
                "Check conceptual understanding"
            )

            reasoning.recommended_depth = "LIGHT"

        else:

            reasoning.next_objective = (
                "Continue explanation"
            )

        # ----------------------------
        # Misconception Detection
        # ----------------------------

        if observation.confused:

            reasoning.probable_misconception = (
                "Concept not yet fully understood"
            )

        elif observation.asks_why:

            reasoning.probable_misconception = (
                "Needs conceptual understanding"
            )

        # ----------------------------
        # Teacher Notes
        # ----------------------------

        reasoning.notes = (
            "Generated using deterministic reasoning rules."
        )

        return reasoning